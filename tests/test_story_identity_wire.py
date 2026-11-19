import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_identity_wire as wire


class StoryIdentityWireTests(unittest.TestCase):
    def packet(self):
        objects=[N(index=i,serial=i+1,address=0x10000+i*16) for i in range(6)]
        return wire.encode(1,2,objects,'e33c5701123456789abcdef001234567',insert=True)

    def test_guid_words_match_engine_guid_layout_and_fixed_packet_size(self):
        p=self.packet();wire.validate_request(p)
        self.assertEqual(len(p),20984)
        self.assertEqual(struct.unpack_from('<4I',p,128),(0xe33c5701,0x12345678,0x9abcdef0,0x01234567))
        self.assertEqual(struct.unpack_from('<II',p,144),(1,0))

    def test_no_arbitrary_guid_namespace_or_modes_and_padding(self):
        for at,value in ((0,1),(4,230),(8,1),(12,1),(24,0xffffffff),(32,1),(128,0),(144,2),(148,1),(152,1)):
            p=bytearray(self.packet());struct.pack_into('<I',p,at,value)
            with self.assertRaises(ValueError):wire.validate_request(bytes(p))
