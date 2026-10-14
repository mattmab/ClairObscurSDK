import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33 import procedural_mesh as mesh

class CombatTargetTests(unittest.TestCase):
    def fixture(self,current=10,ended=0,possessed=None):
        pc=N(index=1,object_flags=0);manager=N(index=2,serial=3,outer_index=1,object_flags=0)
        party=[N(index=10,serial=20),N(index=11,serial=21)]
        c=N(select=lambda name:[pc] if name=='PlayerController' else [manager])
        def values(catalog,obj,fields):
            d={'bIsLocalPlayerController':True,'Pawn':possessed} if obj is pc else {'CurrentCharacter':next((p for p in party if p.index==current),N(index=current,serial=999)), 'PlayerCharacters':N(items=party),'BattleEndState':ended}
            return N(values={(0,k):v for k,v in d.items()}),c
        return c,values
    def select(self,**kwargs):
        c,values=self.fixture(**kwargs)
        with patch.object(mesh,'capture_matching',return_value=c),patch('expedition33.values.read_values_with_references',side_effect=values):return mesh.combat_target(123)[0]
    def setUp(self):mesh._combat_selection.clear()
    def test_party_turn_selects_player(self):self.assertEqual(self.select(current=11).index,11)
    def test_enemy_turn_keeps_last_party_target(self):
        self.select(current=11)
        self.assertEqual(self.select(current=99).index,11)
    def test_ended_battle_is_rejected(self):
        with self.assertRaises(ValueError):self.select(ended=1)
    def test_possessed_exploration_does_not_select_battle(self):
        with self.assertRaises(ValueError):self.select(possessed=N(index=4))
if __name__=='__main__':unittest.main()
