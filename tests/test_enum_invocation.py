import struct
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from expedition33 import RuntimeQueryError, _enum_wire, _invocation_wire
from expedition33.enums import EnumDescriptor, EnumMember, EnumValue
from expedition33.invocation import prepare_call, decode_result, UnsupportedInvocation, InvocationError, PARM, RETURN
import test_invocation


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


if __name__ == '__main__': unittest.main()
