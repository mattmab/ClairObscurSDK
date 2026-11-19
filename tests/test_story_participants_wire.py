import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_participants_wire as wire

class ParticipantWireTests(unittest.TestCase):
    def packet(self,remove=False):
        objects=[N(index=i,serial=1001+i,address=0x10000+16*i) for i in range(5)]
        return wire.encode(1,2,*objects[:3],[(3,4,objects[3]),(5,6,objects[4])],remove=remove)
    def test_registration_and_cleanup_bind_the_same_owner_lease_and_actor_records(self):
        a=self.packet();b=self.packet(True)
        wire.validate(a);wire.validate(b)
        self.assertEqual(a[:80],b[:80]);self.assertEqual(a[84:],b[84:])
        self.assertEqual(struct.unpack_from('<I',b,80)[0],1)
    def test_duplicate_owners_leases_indices_addresses_and_dirty_unused_slots_are_rejected(self):
        for at,data in [(120,struct.pack('<Q',3)),(128,struct.pack('<Q',4)),(136,struct.pack('<i',3)),
                        (144,struct.pack('<Q',0x10030)),(152,struct.pack('<Q',1)),(8280,b'x')]:
            p=bytearray(self.packet());p[at:at+len(data)]=data
            with self.assertRaises(ValueError):wire.validate(bytes(p))
    def test_invalid_context_and_mode_are_rejected(self):
        for at,value in [(0,4),(4,232),(8,1),(16,0),(24,0),(36,0),(80,2),(84,257)]:
            p=bytearray(self.packet());struct.pack_into('<I',p,at,value)
            with self.assertRaises(ValueError):wire.validate(bytes(p))
