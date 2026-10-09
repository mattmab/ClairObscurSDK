import struct
from types import SimpleNamespace
import unittest
from expedition33 import _multi_button_wire as wire


class MultiButtonWireTests(unittest.TestCase):
    def response(self, sent, *, state=0, registration=0, events=()):
        packet = bytearray(sent)
        struct.pack_into('<4I', packet, 8, 0, 2, len(events), state)
        struct.pack_into('<Q', packet, 64, registration)
        for i, event in enumerate(events):
            wire.EVENT.pack_into(packet, 72 + i * 40, *event)
        return packet

    def test_menu_drain_accepts_multiple_registrations(self):
        sent = wire.request('drain', 10)
        reply = self.response(sent, events=((7, 11, 10, 21, 1), (7, 12, 10, 22, 2)))
        result = wire.decode(sent, reply.hex(), session=7)
        self.assertEqual([event.registration for event in result.events], [11, 12])
        self.assertEqual(result.registration, 0)

    def test_entire_batch_rejects_foreign_or_reordered_event(self):
        sent = wire.request('drain', 10)
        for bad in ((8, 12, 10, 22, 2), (7, 12, 99, 22, 2), (7, 12, 10, 22, 1)):
            reply = self.response(sent, events=((7, 11, 10, 21, 1), bad))
            with self.assertRaises(ValueError): wire.decode(sent, reply.hex(), session=7)

    def test_bind_identity_and_nonzero_tail_are_correlated(self):
        sent = wire.request('bind', 10, 20, action=30,
                            child=SimpleNamespace(index=4, serial=5, address=0x10000))
        reply = self.response(sent, state=2, registration=11)
        self.assertEqual(wire.decode(sent, reply.hex(), session=7).registration, 11)
        reply[-1] ^= 1
        with self.assertRaises(ValueError): wire.decode(sent, reply.hex(), session=7)
        reply = self.response(sent, state=2, registration=11); reply[2631] = 1
        with self.assertRaises(ValueError): wire.decode(sent, reply.hex(), session=7)

    def test_request_shape_and_outcome_rejection(self):
        with self.assertRaises(ValueError): wire.request('drain', 10, 20)
        with self.assertRaises(ValueError): wire.request('bind', 10, 20, action=30)
        with self.assertRaises(ValueError): wire.request('unbind', 10, True)
        sent = wire.request('unbind', 10, 20)
        reply = self.response(sent, state=2, registration=11)
        with self.assertRaises(ValueError): wire.decode(sent, reply.hex(), session=7)
        reply = self.response(sent); struct.pack_into('<2I', reply, 8, 1016, 1)
        self.assertEqual(wire.decode(sent, reply.hex(), session=7).outcome, 'unknown')
