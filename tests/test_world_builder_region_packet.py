import struct, unittest
from expedition33.procedural_mesh import validate_request, SIZE, HEADER

class RegionPacketTests(unittest.TestCase):
    def packet(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,65,0,0,17)
        struct.pack_into('<II',p,2000,1,0)
        struct.pack_into('<6d',p,2016,-100.,-100.,-100.,100.,100.,100.)
        struct.pack_into('<iiQ',p,4096,123,5,0x10000)
        return p
    def test_valid_region(self):validate_request(bytes(self.packet()))
    def test_rejects_invalid_bounds_counts_and_identity(self):
        for fmt,offset,value in [('<I',2000,65),('<I',2004,1000001),('<d',2016,float('nan')),('<d',2016,101.),('<Q',4104,0),('<B',2064,1)]:
            p=self.packet();struct.pack_into(fmt,p,offset,value)
            with self.subTest(offset=offset,value=value),self.assertRaises(ValueError):validate_request(bytes(p))
