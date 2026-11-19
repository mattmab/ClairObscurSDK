import sys,types,json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
package=types.ModuleType('damage_engine_evidence_test');package.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[package.__name__]=package
from damage_engine_evidence_test.engine_evidence import ModifierEvidence,describe,calculation

class EngineEvidenceTests(unittest.TestCase):
 def row(self,**changes):
  return dict(dict(pid=42,epoch=100,sequence=1,tick=1000,damage=[10,1,100000],source=[11,1,110000],target=[12,1,120000],before=100.,value=.25,kind=3,affects_base=1,damage_reason=3,reason='Augmented Aim',rejected=0,dropped=0),**changes)
 def test_joins_exact_hit_source_target_and_time_without_cross_character_leakage(self):
  with TemporaryDirectory() as temp:
   folder=Path(temp);reader=ModifierEvidence(folder,42);reader.path.write_text(json.dumps(self.row())+'\n',encoding='utf-8')
   found=reader.match((10,1,100000),(11,1,110000),(12,1,120000),1100)
   self.assertEqual(found['modifiers'][0]['reason'],'Augmented Aim');self.assertIn('additive percentage 0.25',describe(found))
   for damage,source,target,tick in (((10,2,100000),(11,1,110000),(12,1,120000),1100),((10,1,100000),(99,1,990000),(12,1,120000),1100),((10,1,100000),(11,1,110000),(99,1,990000),1100),((10,1,100000),(11,1,110000),(12,1,120000),900)):
    self.assertIsNone(reader.match(damage,source,target,tick))
   found['modifiers'][0]['value']=99
   self.assertEqual(reader.match((10,1,100000),(11,1,110000),(12,1,120000),1100)['modifiers'][0]['value'],.25)
 def test_partial_append_foreign_process_invalid_rows_and_replays(self):
  with TemporaryDirectory() as temp:
   reader=ModifierEvidence(Path(temp),42);text=json.dumps(self.row());reader.path.write_text(text[:20],encoding='utf-8');reader.poll();self.assertFalse(reader.groups)
   with reader.path.open('a',encoding='utf-8') as f:f.write(text[20:]+'\n'+text+'\n'+json.dumps(self.row(pid=99,sequence=2))+'\n'+json.dumps(self.row(sequence=3,value=float('nan')))+'\n')
   reader.poll();self.assertEqual(sum(map(len,reader.groups.values())),1);self.assertEqual(reader.error,'Invalid diagnostic evidence')
 def test_unavailable_profile_status_never_becomes_applied_evidence(self):
  with TemporaryDirectory() as temp:
   reader=ModifierEvidence(Path(temp),42);reader.path.write_text(json.dumps(dict(event='capture_started',pid=42,epoch=100,enabled=False))+'\n',encoding='utf-8')
   reader.poll();self.assertFalse(reader.status['enabled']);self.assertFalse(reader.groups)
 def test_replays_separate_observed_stages_and_adds_percentages_once(self):
  evidence=dict(modifiers=[self.row(before=100.,kind=2,value=1.5),self.row(before=150.,kind=2,value=2.),self.row(before=150.,kind=3,value=.3),self.row(before=150.,kind=3,value=.25),self.row(before=465.,kind=2,value=.15)],rejected=0,dropped=0)
  result=calculation(evidence,69.75)
  self.assertTrue(result['reconciled']);self.assertEqual(len(result['stages']),3);self.assertAlmostEqual(result['raw_result'],69.75)
 def test_never_invents_a_multiplier_to_close_unobserved_stage_or_output_gaps(self):
  evidence=dict(modifiers=[self.row(before=100.,kind=2,value=2.),self.row(before=170.,kind=2,value=.5)],rejected=0,dropped=0)
  result=calculation(evidence,85.)
  self.assertFalse(result['reconciled']);self.assertEqual(result['gaps'][0]['observed_input'],170.)
  evidence['modifiers']=[self.row(before=100.,kind=2,value=1.)]
  self.assertFalse(calculation(evidence,110.)['reconciled'])
  evidence['modifiers'][0]['kind']=7;self.assertIsNone(calculation(evidence,100.)['raw_result'])
