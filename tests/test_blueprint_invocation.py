"""Explicit Blueprint admission and retained transport, without game execution."""
from dataclasses import replace
from types import SimpleNamespace
import struct
import unittest
from unittest.mock import patch

from expedition33.invocation import prepare_call, UnsupportedInvocation, PARM, RETURN
from expedition33 import _blueprint_wire as wire, _invocation_wire as call
from expedition33.prepared_invocation import InvocationPlanner
import test_invocation


class BlueprintInvocationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_invocation.InvocationTests()
        self.fixture.setUp()
        self.catalog = self.fixture.catalog
        self.target, self.function = self.fixture.target, self.fixture.function

    def descriptor(self, fields=(), size=0, returned=65535, flags=0x0c020000, entry='0x13937a0'):
        return SimpleNamespace(owners=({'index': 7, 'size': size},), properties=fields,
            function=dict(params_size=size, return_offset=returned, flags=flags, entry_rva=entry))

    def planner(self, descriptor, supported=True):
        class TestSession(SimpleNamespace):
            pass
        session = TestSession(_check=lambda: None, supports_retained_invocation=True,
            supports_blueprint_invocation=supported, pid=self.catalog.pid)
        planner = InvocationPlanner(session, catalog=self.catalog)
        # Planner deliberately borrows its session; retain the test owner.
        planner.test_session = session
        self.addCleanup(planner.close)
        self.patch = patch('expedition33.invocation.describe', return_value={7: descriptor})
        self.patch.start(); self.addCleanup(self.patch.stop)
        return planner

    def test_reset_zero_argument_opt_in_and_rebind_keep_v8(self):
        planner = self.planner(self.descriptor())
        prepared = planner.prepare_blueprint(self.target, self.function)
        self.assertEqual(prepared._plan.wire_version, 8)
        self.assertEqual(prepared.bind()._plan.wire_version, 8)
        packet = wire.encode_plan(prepared._plan)
        self.assertEqual(call.HEADER.unpack_from(packet)[:4], (8, 0, 0, 65535))
        self.assertEqual(len(packet), 26192)

    def test_can_start_battle_bool_result_round_trip(self):
        field = self.fixture.field('ReturnValue', 'BoolProperty', 0, 1, PARM | RETURN,
                                   bool_encoding='0xff010001')
        planner = self.planner(self.descriptor([field], 1, 0, flags=0x14020000))
        prepared = planner.prepare_blueprint(self.target, self.function)
        packet = wire.encode_plan(prepared._plan)
        response = bytearray(packet)
        struct.pack_into('<II', response, 32, 1, 0)
        response[call.DATA_AT] = 1
        result, leases = wire.decode_reply(packet, response.hex())
        self.assertEqual(result.data, b'\x01')
        self.assertFalse(leases)

    def test_capability_missing_rejects_before_metadata(self):
        planner = self.planner(self.descriptor(), supported=False)
        with self.assertRaisesRegex(UnsupportedInvocation, 'capability'):
            planner.prepare_blueprint(self.target, self.function)

    def test_all_forbidden_flag_bits_and_native_thunk_rejected(self):
        for bit in range(32):
            if wire.FORBIDDEN_FLAGS & (1 << bit):
                with self.assertRaises(UnsupportedInvocation):
                    wire.validate_function(1 << bit, 0x13937a0, 'ResetState')
        for name, entry in [('ExecuteUbergraph_QA', 0x13937a0), ('ResetState', 0x1234)]:
            with self.assertRaises(UnsupportedInvocation):
                wire.validate_function(0x0c020000, entry, name)

    def test_complex_output_rejected_before_any_dispatch(self):
        field = self.fixture.field('ReturnValue', 'ArrayProperty', 0, 16, PARM | RETURN)
        planner = self.planner(self.descriptor([field], 16, 0))
        with self.assertRaises(UnsupportedInvocation):
            planner.prepare_blueprint(self.target, self.function)

    def test_object_identity_arguments_use_existing_schema_codec(self):
        cls = self.catalog.by_index[2]
        field = self.fixture.field('Object', 'ObjectProperty', 0, 8,
            property_class_index=2, property_class_serial=cls.serial,
            property_class_name=cls.name, property_class_address=hex(cls.address))
        planner = self.planner(self.descriptor([field], 8))
        prepared = planner.prepare_blueprint(self.target, self.function, Object=self.target)
        self.assertEqual(prepared._plan.objects[0].object, self.target)
        wire.encode_plan(prepared._plan)
        with self.assertRaises(ValueError):
            planner.prepare_blueprint(self.target, self.function, Object=self.target.address)

    def test_scalar_inputs_remain_typed_and_old_wire_unchanged(self):
        field = self.fixture.field('Value', 'IntProperty', 0, 4)
        descriptor = self.descriptor([field], 4)
        planner = self.planner(descriptor)
        prepared = planner.prepare_blueprint(self.target, self.function, Value=4)
        self.assertEqual(prepared._plan.data, struct.pack('<i', 4))
        with self.assertRaises(ValueError):
            planner.prepare_blueprint(self.target, self.function, Value=True)
        with patch('expedition33.invocation.describe', return_value={7: descriptor}):
            ordinary = prepare_call(self.catalog, self.target, self.function, {'Value': 4})
        self.assertEqual(ordinary.wire_version, 1)
        with self.assertRaises(UnsupportedInvocation):
            wire.encode_plan(ordinary)

    def test_refresh_revokes_blueprint_prepared_call(self):
        planner = self.planner(self.descriptor())
        prepared = planner.prepare_blueprint(self.target, self.function)
        planner.refresh_from(self.catalog)
        with self.assertRaisesRegex(RuntimeError, 'revoked'):
            prepared.bind()

    def test_name_inputs_copy_registered_strings_and_never_accept_ids(self):
        fields = [self.fixture.field('QuestName', 'NameProperty', 0, 8),
                  self.fixture.field('ObjectiveName', 'NameProperty', 8, 8),
                  self.fixture.field('Status', 'ByteProperty', 16, 1),
                  self.fixture.field('HasUpdated', 'BoolProperty', 17, 1, PARM | 0x100,
                                     bool_encoding='0xff010001')]
        planner = self.planner(self.descriptor(fields, 18))
        prepared = planner.prepare_blueprint(self.target, self.function,
            QuestName='Quests_LumiereAct1', ObjectiveName='DefeatMime', Status=0)
        packet = wire.encode_plan(prepared._plan)
        name = call.FIELD.unpack_from(packet, call.FIELDS_AT)
        self.assertEqual(name[0], 21)
        self.assertTrue(name[6].startswith(b'QuestName\0Quests_LumiereAct1\0'))
        self.assertEqual(packet[call.DATA_AT:call.DATA_AT+16], bytes(16))
        response = bytearray(packet); struct.pack_into('<II', response, 32, 1, 0)
        response[call.DATA_AT+17] = 1
        reply, _ = wire.decode_reply(packet, response.hex())
        from expedition33.invocation import decode_result
        result = decode_result(prepared._plan, reply, self.catalog)
        self.assertTrue(result.outputs['HasUpdated'])
        for bad in (12345, '', 'bad\0name', 'nonascii_é'):
            with self.assertRaises((ValueError, UnsupportedInvocation)):
                planner.prepare_blueprint(self.target, self.function,
                    QuestName=bad, ObjectiveName='DefeatMime', Status=0)

    def test_real_quest_name_reference_flags_are_inputs(self):
        fields = [self.fixture.field('QuestName', 'NameProperty', 0, 8, 0x8001048000394),
                  self.fixture.field('ObjectiveName', 'NameProperty', 8, 8, 0x8001048000394)]
        prepared = self.planner(self.descriptor(fields, 16)).prepare_blueprint(
            self.target, self.function, QuestName='Quests_LumiereAct1', ObjectiveName='DefeatMime')
        packet = wire.encode_plan(prepared._plan)
        self.assertEqual(call.FIELD.unpack_from(packet, call.FIELDS_AT)[4], 0x8001048000394)
        self.assertEqual(packet[call.DATA_AT:call.DATA_AT+16], bytes(16))
        output = self.fixture.field('Name', 'NameProperty', 0, 8, PARM | 0x100)
        with self.assertRaises(UnsupportedInvocation):
            self.planner(self.descriptor([output], 8)).prepare_blueprint(self.target, self.function)

    def test_name_return_and_oversize_payload_rejected(self):
        field = self.fixture.field('ReturnValue', 'NameProperty', 0, 8, PARM | RETURN)
        planner = self.planner(self.descriptor([field], 8, 0))
        with self.assertRaises(UnsupportedInvocation):
            planner.prepare_blueprint(self.target, self.function)
        with self.assertRaises(UnsupportedInvocation):
            wire.encode_name('QuestName', 'a' * 90)


if __name__ == '__main__':
    unittest.main()
