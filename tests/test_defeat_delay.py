import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33 import _defeat_delay as delay


class DefeatDelayTests(unittest.TestCase):
    def packet(self, mode=1):
        return delay.encode(SimpleNamespace(index=3, serial=4, address=0x10000), 7, 8, mode)

    def test_fixed_packet_round_trip(self):
        for mode in (1, 2):
            packet = self.packet(mode)
            self.assertEqual(len(packet), 20984)
            self.assertEqual(struct.unpack_from('<4IQiiQQI', packet),
                             (3, 227, 0, 0, 8, 3, 4, 0x10000, 7, mode))
            delay.validate_request(packet)

    def test_other_operations_and_arbitrary_payloads_rejected(self):
        for at, value in ((0, 2), (4, 226), (8, 1), (12, 1), (24, 0xffffffff),
                          (28, 0), (48, 3), (52, 1)):
            packet = bytearray(self.packet())
            struct.pack_into('<I', packet, at, value)
            with self.assertRaises(ValueError):
                delay.validate_request(bytes(packet))

    def test_owner_and_retention_are_mandatory(self):
        for at in (16, 32, 40):
            packet = bytearray(self.packet())
            struct.pack_into('<Q', packet, at, 0)
            with self.assertRaises(ValueError):
                delay.validate_request(bytes(packet))


    def test_restore_remains_available_after_scope_revocation(self):
        obj = object.__new__(delay.DefeatDelayOverride)
        obj._function = SimpleNamespace(index=3, serial=4, address=0x10000)
        obj._token, obj._owner, obj._active = 7, 8, True
        obj._held = SimpleNamespace(active=True, release=Mock())
        def command(name, packet):
            reply = bytearray(packet)
            return {'mesh_packet': reply.hex()}
        transport = SimpleNamespace(command=command, _lease_owner=99)
        session = SimpleNamespace(_check=Mock(), _transport=transport)
        obj._scope = SimpleNamespace(_closed=True, _session=session, _lease_owner_id=42)
        self.assertTrue(obj.close())
        self.assertFalse(obj._active)
        self.assertEqual(transport._lease_owner, 99)
        obj._held.release.assert_not_called()  # Closed scope owns the lease-release batch.


if __name__ == '__main__':
    unittest.main()
