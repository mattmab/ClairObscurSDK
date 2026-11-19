import struct,unittest
from types import SimpleNamespace as N
from expedition33 import story_enemy_loot as wire
def held(i):return N(object=N(index=i,serial=2,address=65536+i*16),_token=i+10)
class EnemyLootTests(unittest.TestCase):
 def packet(self,enemy='TestEnemy',reward='TestItem'):
  return wire.packet(99,*(held(i) for i in range(1,5)),'/Game/SDK/Sample/Enemies','Enemies',held(5),
      'e33c5701000000010000000200000003',enemy=enemy,reward=reward)
 def test_two_consumer_pairs_and_exact_ack(self):
  for enemy,reward in (('TestEnemy','TestItem'),('AnotherEnemy','AnotherItem')):
   sent=self.packet(enemy,reward);wire.validate(sent)
   reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<2I',reply,128,20,20)
   self.assertEqual(wire.decode(sent,bytes(reply)),dict(original_rows=20,registered_rows=20))
   reply[2064]^=1
   with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
 def test_invalid_id_padding_and_missing_identity_rejected(self):
  for enemy,reward in (('bad/name','Item'),('Enemy',''),('Enemy','X'*96)):
   with self.assertRaises(ValueError):self.packet(enemy,reward)
  for at in (2048,2159,2160):
   changed=bytearray(self.packet());changed[at]^=1
   with self.assertRaises(ValueError):wire.validate(bytes(changed))
