import struct,unittest
from types import SimpleNamespace as N
from expedition33.initial_encounter_roster import packet,validate,decode
class InitialRosterWire(unittest.TestCase):
 def sent(self,names=('Goblu','Simon'),mode=0):
  held=[N(object=N(index=i,serial=1,address=0x10000+i*16),_token=i+1) for i in range(7)]
  return packet(99,held,names,mode)
 def test_complete_ordered_roster_and_duplicates(self):
  sent=self.sent(('Simon','Goblu','Simon'));validate(sent)
  self.assertEqual(struct.unpack_from('<I',sent,196)[0],3)
  self.assertEqual([sent[200+i*96:296+i*96].split(b'\0',1)[0] for i in range(3)],[b'Simon',b'Goblu',b'Simon'])
 def test_bounds_and_definition_validation(self):
  for names in ((),('Simon',)*11,('x'*96,),('Simon\0other',),('!bad',)):
   with self.assertRaises((ValueError,struct.error)):self.sent(names)
 def test_ack_correlates_owner_dependencies_order_and_mode(self):
  for mode in range(3):
   sent=self.sent(mode=mode);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
   if mode==1:struct.pack_into('<I',reply,1160,1)
   self.assertEqual(decode(sent,bytes(reply)),int(mode==1))
   for at in (16,24,136,192,196,200,296,1164):
    bad=bytearray(reply);bad[at]^=1
    with self.assertRaises(RuntimeError):decode(sent,bytes(bad))
