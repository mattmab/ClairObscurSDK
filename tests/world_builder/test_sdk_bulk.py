import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from expedition33 import lease_policy,procedural_mesh
class SDKBulkTests(unittest.TestCase):
 def test_expanded_lease_limit_is_bounded(self):
  lease_policy.validate_request(lease_policy.request(1,8192,7000,512))
  with self.assertRaises(ValueError):lease_policy.request(1,8193,7000,512)
 def test_bulk_packet_count_padding_and_nonfinite_rejected(self):
  raw=bytearray(procedural_mesh.SIZE);struct.pack_into('<4IQ',raw,0,3,50,0,0,1);struct.pack_into('<I',raw,2000,1);struct.pack_into('<II12d',raw,4096,0,0,0,0,0,1,0,0,0,0,1,1,1,0)
  procedural_mesh.validate_request(bytes(raw))
  for at,value,fmt in ((2000,65,'<I'),(4200,1,'<B'),(4104,float('nan'),'<d')):
   bad=bytearray(raw);struct.pack_into(fmt,bad,at,value)
   with self.assertRaises(ValueError):procedural_mesh.validate_request(bytes(bad))
if __name__=='__main__':unittest.main()
