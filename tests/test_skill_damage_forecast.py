import importlib.util
from pathlib import Path
import sys,unittest
spec=importlib.util.spec_from_file_location('skill_damage_forecast',Path(__file__).resolve().parents[1]/'mods/SkillDamage/forecast.py')
f=importlib.util.module_from_spec(spec);sys.modules[spec.name]=f;spec.loader.exec_module(f)

class ForecastTests(unittest.TestCase):
 def test_four_outcomes_and_rounding_per_impact(self):
  result=f.project([f.Hit(100,1,0)]*2,[f.Hit(100,1.1,0)]*2)
  self.assertEqual(result,f.Outcomes(200,300,220,330))
  self.assertEqual(f.card_text(result),'Fail total: N 200 | C 300\nPass total: N 220 | C 330')
 def test_defense_precedes_critical_and_final_modifiers(self):
  hit=f.Hit(100,1,50,final_multiplier=2,additive_percent=.3)
  self.assertEqual(hit.damage(False),130)
  self.assertEqual(hit.damage(True),195)
 def test_damage_cap_and_shield_apply_per_hit(self):
  self.assertEqual(f.project([f.Hit(100,1,0,damage_limit=80)]*2,[f.Hit(100,1,0,shielded=True)]),f.Outcomes(160,160,0,0))
 def test_unknown_rules_and_invalid_inputs_never_produce_numbers(self):
  with self.assertRaisesRegex(ValueError,'Unresolved'):f.project([f.Hit(100,1,0)],[f.Hit(100,1,0)],unresolved=('weapon effect',))
  for value in (True,float('nan'),float('inf'),-1):
   with self.assertRaises(ValueError):f.Hit(value,1,0).damage(False)
 def test_zero_attack_and_compact_display(self):
  self.assertEqual(f.Hit(0,1,100).damage(True),0)
  self.assertEqual(f.compact(12500),'12.5k')
  self.assertEqual(f.compact(1200000),'1.2m')
