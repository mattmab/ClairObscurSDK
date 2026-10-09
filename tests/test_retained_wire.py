import struct
import unittest
from expedition33 import _invocation_wire as call, _retained_wire as wire
from expedition33.invocation import PARM, RETURN
import test_invocation


class RetainedWireTests(unittest.TestCase):
    def setUp(self):
        p = test_invocation.InvocationTests(); p.setUp()
        self.planner = p
        cls = p.catalog.by_index[2]
        self.plan = p.plan([p.field('ReturnValue', 'ObjectProperty', 0, 8, PARM | RETURN,
            property_class_index=2, property_class_serial=cls.serial,
            property_class_name=cls.name, property_class_address=hex(cls.address))], {}, 8, 0)
        self.request = wire.encode_plan(self.plan)

    def response(self):
        packet = bytearray(self.request)
        obj = self.planner.target
        struct.pack_into('<III', packet, 28, 1, 1, 0)
        call.OBJECT.pack_into(packet, call.OBJECTS_AT, 0, obj.index, obj.serial, obj.address)
        wire.HEADER.pack_into(packet, call.SIZE, 1, 1)
        wire.LEASE.pack_into(packet, wire.LEASES_AT, 0, 12)
        return packet

    def test_success_requires_exact_output_ownership(self):
        packet = self.response()
        reply, leases = wire.decode_reply(self.request, packet.hex())
        self.assertEqual(reply.outcome, 'dispatch_returned')
        self.assertEqual(leases, ((0, 12),))
        wire.HEADER.pack_into(packet, call.SIZE, 1, 0)
        packet[wire.LEASES_AT:] = bytes(128 * wire.LEASE.size)
        with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())

    def test_null_output_has_no_lease(self):
        packet = bytearray(self.request)
        struct.pack_into('<II', packet, 32, 1, 0)
        reply, leases = wire.decode_reply(self.request, packet.hex())
        self.assertEqual((reply.objects, leases), ((), ()))

    def test_duplicate_zero_wrong_offset_and_tail_tokens_rejected(self):
        for offset, token in ((8, 12), (0, 0)):
            packet = self.response()
            wire.LEASE.pack_into(packet, wire.LEASES_AT, offset, token)
            with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())
        packet = self.response()
        wire.LEASE.pack_into(packet, wire.LEASES_AT + wire.LEASE.size, 0, 12)
        with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())
        wire.HEADER.pack_into(packet, call.SIZE, 1, 2)
        with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())

    def test_unknown_preserves_partial_tokens_for_cleanup_not_use(self):
        packet = self.response()
        struct.pack_into('<II', packet, 32, 2, 405)
        reply, leases = wire.decode_reply(self.request, packet.hex())
        self.assertEqual((reply.outcome, reply.objects, leases), ('unknown', (), ((0, 12),)))
        struct.pack_into('<II', packet, 32, 0, 401)
        with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())

    def test_envelope_version_size_and_count(self):
        self.assertEqual(len(self.request), 26192)
        for version, count in ((2, 1), (1, 129)):
            packet = self.response()
            wire.HEADER.pack_into(packet, call.SIZE, version, count)
            with self.assertRaises(ValueError): wire.decode_reply(self.request, packet.hex())
        for packet in ('', self.request.hex() + '00', 'z' * (wire.SIZE * 2)):
            with self.assertRaises(ValueError): wire.decode_reply(self.request, packet)


if __name__ == '__main__': unittest.main()
