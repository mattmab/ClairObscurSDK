import struct,unittest
from types import SimpleNamespace as NS
from expedition33 import story_enemy_loot as wire

def held(index):return NS(object=NS(index=index,serial=1,address=0x10000+index*16),_token=index+10)
class EnemyLootWire(unittest.TestCase):
    def packet(self,mode=0):return wire.packet(123,*(held(i) for i in range(1,5)),'/Game/SDK/Test/SampleEnemies','SampleEnemies',held(5),'e33c5701000000010000000200000003',mode,enemy='SampleEnemy',reward='SampleReward')
    def test_exact_enemy_row_and_bound_save_required(self):
        sent=self.packet();wire.validate(sent)
        for offset in (488,2040,2048):
            changed=bytearray(sent);changed[offset]=0
            with self.assertRaises(ValueError):wire.validate(bytes(changed))
    def test_row_replacement_preserves_inventory_size(self):
        sent=self.packet();reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<2I',reply,128,434,434)
        self.assertEqual(wire.decode(sent,bytes(reply))['registered_rows'],434)
        struct.pack_into('<I',reply,132,435)
        with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
    def test_reply_cannot_change_save_or_owner(self):
        sent=self.packet();reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<2I',reply,128,434,434);reply[2052]^=1
        with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
