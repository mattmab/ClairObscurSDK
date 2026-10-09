import struct
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from expedition33 import RuntimeQueryError, _enum_wire, _invocation_wire
from expedition33.enums import EnumDescriptor, EnumMember, EnumValue
from expedition33.invocation import prepare_call, decode_result, UnsupportedInvocation, InvocationError, PARM, RETURN
import test_invocation
import test_text_transport
from test_ownership import Transport
from expedition33.sdk import Session
from expedition33._scope import SessionScope


class EnumInvocationTests(unittest.TestCase):
    def setUp(self):
        self.f = test_invocation.InvocationTests()
        self.f.setUp()
        self.enum = self.f.catalog.by_index[2]
        self.members = (EnumMember('E::First', 0), EnumMember('E::Second', 2), EnumMember('E::E_MAX', 3))
        self.descriptor = EnumDescriptor(self.enum, self.members)

    def plan(self, value, enabled=True, output=False, **changes):
        row = self.f.field('Mode', 'EnumProperty', 0, 1, PARM | (RETURN if output else 0),
            enum_index=self.enum.index, enum_serial=self.enum.serial, enum_name=self.enum.name,
            inner_type='ByteProperty', inner_element_size=1)
        row.update(changes)
        descriptor = SimpleNamespace(owners=({'index': 7, 'size': 1},), properties=[row],
            function=dict(params_size=1, return_offset=0 if output else 65535, flags=0x400, entry_rva='0x1234'))
        with patch('expedition33.invocation.describe', return_value={7: descriptor}), patch(
                'expedition33.invocation.describe_enums', return_value={self.enum.index: self.descriptor}):
            return prepare_call(self.f.catalog, self.f.target, self.f.function,
                                {} if output else {'Mode': value}, enum_values=enabled)

    def test_typed_plan_wire_and_old_codec_rejection(self):
        plan = self.plan(self.descriptor.value('E::Second'))
        self.assertEqual((plan.wire_version, plan.data), (4, b'\x02'))
        encoded = _enum_wire.encode_plan(plan)
        self.assertEqual(struct.unpack_from('<I', encoded)[0], 4)
        self.assertEqual(_invocation_wire.FIELD.unpack_from(encoded, _invocation_wire.FIELDS_AT)[0], 14)
        with self.assertRaises(UnsupportedInvocation): _invocation_wire.encode_plan(plan)
        with self.assertRaises(UnsupportedInvocation): self.plan(self.descriptor.value('E::First'), enabled=False)

    def test_reject_untyped_forged_stale_sentinel_and_wrong_storage(self):
        good = self.descriptor.value('E::Second')
        for bad in (2, True, replace(good, value=1), replace(good, name='Other'),
                    EnumValue(self.enum, 'E::E_MAX', 3), replace(good, value=256),
                    replace(good, enum=replace(self.enum, serial=99))):
            with self.subTest(value=bad), self.assertRaises((ValueError, RuntimeQueryError)):
                self.plan(bad)
        for change in ({'dimension': 2}, {'inner_type': 'IntProperty'}, {'enum_serial': 99}):
            with self.subTest(change=change), self.assertRaises(ValueError): self.plan(good, **change)
        with self.assertRaises(ValueError): self.descriptor.value('E::E_MAX')

    def test_copied_output_and_reply_identity(self):
        plan = self.plan(None, output=True)
        request = _enum_wire.encode_plan(plan)
        packet = bytearray(request)
        struct.pack_into('<I', packet, 32, 1)
        packet[_invocation_wire.DATA_AT] = 2
        reply, leases = _enum_wire.decode_reply(request, packet.hex())
        self.assertFalse(leases)
        result = decode_result(plan, reply, self.f.catalog)
        self.assertEqual(result.return_value, self.descriptor.value('E::Second'))
        with self.assertRaises(InvocationError):
            decode_result(plan, replace(reply, data=b'\x01'), self.f.catalog)
        packet[_invocation_wire.FIELDS_AT + 124] ^= 1
        with self.assertRaises(ValueError): _enum_wire.decode_reply(request, packet.hex())

    def test_session_scope_route_and_handshake(self):
        transport = Transport()
        transport.start['pid'] = self.f.target.pid
        for capability in (*test_text_transport.TextTransportTests.capabilities, 'enum_value_protocol'):
            setattr(transport, capability, 1)
        original = transport.command
        def command(name, packet=None):
            if name != 'retained-invoke': return original(name, packet)
            transport.calls.append(name)
            response = bytearray(packet)
            struct.pack_into('<I', response, 32, 1)
            response[_invocation_wire.DATA_AT] = 2
            return {'retained_packet': response.hex()}
        transport.command = command
        plan = self.plan(None, output=True)
        with patch('expedition33.sdk.SessionTransport', return_value=transport) as factory, patch(
                'expedition33.catalog.capture', return_value=self.f.catalog), patch(
                'expedition33.invocation.prepare_call', return_value=plan):
            with Session(enum_values=True) as session:
                self.assertIn('research-probe-v13', str(factory.call_args.kwargs['_executable']))
                scope = SessionScope(session)
                self.assertTrue(scope.supports_enum_values and scope.supports_text_values)
                with scope.invoke_retained(self.f.target, self.f.function) as result:
                    self.assertEqual(result.return_value, self.descriptor.value('E::Second'))
                scope.close()
                self.assertFalse(session._leases)
            transport.enum_value_protocol = 0
            with self.assertRaisesRegex(RuntimeQueryError, 'Enum value backend handshake'):
                Session(enum_values=True)

    def test_transport_rejects_incomplete_enum_handshake_before_send(self):
        packet = _enum_wire.encode_plan(self.plan(self.descriptor.value('E::Second')))
        helper = test_text_transport.TextTransportTests()
        for missing in (*helper.capabilities, 'enum_value_protocol'):
            transport = helper.transport()
            transport.enum_value_protocol = 1
            setattr(transport, missing, 0)
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'does not support'):
                transport.command('retained-invoke', packet)
            self.assertEqual(transport._process.stdin.getvalue(), '')


if __name__ == '__main__': unittest.main()
