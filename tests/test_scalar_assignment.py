import unittest,struct
from types import SimpleNamespace
from expedition33.scalar_assignment import bits,packet
class ScalarAssignmentTests(unittest.TestCase):
 def test_numeric_bounds_and_boolean_separation(self):
  self.assertEqual(bits(2,-1),0xffffffff)
  for kind,value in [(1,1),(2,True),(2,2**31),(2,-2**31-1),(3,float('nan')),(4,float('inf')),(3,1e100),(4,10**1000)]:
   with self.subTest(kind=kind,value=value),self.assertRaises(ValueError):bits(kind,value)
 def test_packet_identity_expected_and_boolean_encoding(self):
  obj=SimpleNamespace(index=2,serial=3,address=4096);owner=SimpleNamespace(index=4,serial=5,address=8192)
  m=dict(type='BoolProperty',dimension=1,element_size=1,vtable_rva='0x6e119b0',flags=0,name='Flag',offset=64,bool_encoding='0x04040001')
  p=packet(obj,owner,m,False,True,7)
  self.assertEqual(len(p),232);self.assertEqual(struct.unpack_from('<iiQ',p,32),(2,3,4096))
  self.assertEqual(struct.unpack_from('<QQI',p,80),(0,1,0x04040001))
  for flags in (0x20,0x80,0x20000):
   with self.assertRaises(ValueError):packet(obj,owner,dict(m,flags=flags),False,True,7)
 def test_float_roundtrip(self):
  self.assertEqual(struct.unpack('<f',bits(3,1.25).to_bytes(4,'little'))[0],1.25)
  self.assertEqual(struct.unpack('<d',bits(4,-1.25).to_bytes(8,'little'))[0],-1.25)
