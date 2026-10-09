import struct
import unittest
from types import SimpleNamespace
from expedition33 import _menu_wire as wire
from expedition33._invocation_wire import SIZE as CALL_SIZE


class MenuWireTests(unittest.TestCase):
    def test_preparation_layout(self):
        ids = tuple(SimpleNamespace(index=i, serial=i+1, address=0x1000+i) for i in range(5))
        plan = b'\x01' + bytes(CALL_SIZE-1)
        packet = wire.request('prepare', 42, leases=(12, 13), identities=ids, plans=(plan,)*10)
        self.assertEqual(len(packet), wire.SIZE)
        self.assertEqual(struct.unpack_from('<3Q', packet, 24), (42, 12, 13))
        self.assertEqual(struct.unpack_from('<iiQ', packet, 112), (4, 5, 0x1004))
        self.assertEqual(packet[wire.PLANS_AT:], plan*10)
        with self.assertRaises(ValueError):
            wire.request('prepare', 42, leases=(12, 12), identities=ids, plans=(plan,)*10)
        with self.assertRaises(ValueError):
            wire.request('prepare', 42, leases=(12, 13), identities=ids, plans=(plan,)*9)

    def test_reply_correlation_and_outcomes(self):
        sent = wire.request('close', 42)
        for error, outcome, active in ((0,2,0), (813,2,1), (814,2,1), (816,1,1), (810,0,0)):
            reply = bytearray(sent)
            struct.pack_into('<3I', reply, 8, error, outcome, active)
            result = wire.decode(sent, reply.hex())
            self.assertEqual((result.error, result.active), (error, bool(active)))
        for error, outcome, active in ((0,0,0), (0,1,1), (816,2,1), (0,2,2), (815,2,1)):
            reply = bytearray(sent)
            struct.pack_into('<3I', reply, 8, error, outcome, active)
            with self.assertRaises(ValueError): wire.decode(sent, reply.hex())
        for offset in (0, 4, 20, 24, 32, 48, 128, wire.SIZE-1):
            reply = bytearray(sent)
            struct.pack_into('<3I', reply, 8, 0, 2, 0)
            reply[offset] ^= 1
            with self.assertRaises(ValueError): wire.decode(sent, reply.hex())

    def test_invalid_request(self):
        for owner in (0, -1, True, 2**64):
            with self.assertRaises(ValueError): wire.request('status', owner)
        with self.assertRaises(ValueError): wire.request('status', 1, leases=(2,3))
        with self.assertRaises(ValueError): wire.request('prepare', 1)
        with self.assertRaises(ValueError): wire.request('destroy', 1)
