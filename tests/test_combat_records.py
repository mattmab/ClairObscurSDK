import importlib.util,sys,types,unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
package=types.ModuleType('combat_records_test');package.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[package.__name__]=package
from combat_records_test.records import CombatRecords,battle_detail

class CombatRecordTests(unittest.TestCase):
 def state(self,ending=False):
  return dict(active=True,ending=ending,outcome='victory',signature='fight-1',roster=(
   dict(id='verso',name='Verso',side='party',aliases=((1,1,100),(11,1,110))),
   dict(id='maelle',name='Maelle',side='party',aliases=((2,1,200),(12,1,120))),
   dict(id='boss',name='Duolliste',side='enemy',aliases=((3,1,300),(13,1,130)))),counters={})
 def event(self,source,target,damage,sequence=1):
  def obj(key):return NS(index=key[0],serial=key[1],address=key[2]) if key else None
  return NS(sequence=sequence,monotonic_ms=1000,arguments=dict(SourceCharacter=obj(source),TargetCharacter=obj(target),ReceivedDamages=damage))
 def test_per_character_attribution_actor_and_stats_aliases_secondary_events(self):
  r=CombatRecords();r.observe(dict(active=False));r.observe(self.state())
  r.event(self.event((11,1,110),(13,1,130),100));r.event(self.event((1,1,100),(3,1,300),25,2))
  r.event(self.event((3,1,300),(12,1,120),40,3))
  r.observe(self.state(True));r.observe(self.state(True))
  self.assertEqual(len(r.recent),1)
  p=r.recent[0]['participants'];self.assertEqual(p['verso']['dealt'],125);self.assertEqual(p['maelle']['received'],40)
  self.assertEqual(p['boss']['received'],125);self.assertFalse(r.recent[0]['partial'])
  self.assertIn('Maelle',battle_detail(r.recent[0]));self.assertIn('To Duolliste: 125',battle_detail(r.recent[0]))
 def test_unknown_source_and_late_previous_battle_are_not_assigned_to_a_character(self):
  r=CombatRecords();r.observe(self.state());r.event(self.event(None,(3,1,300),20))
  r.event(self.event((90,1,900),(91,1,910),1000,2))
  self.assertEqual(r.current['unattributed'],20);self.assertEqual(r.current['damage'],20);self.assertTrue(r.current['incomplete'])
 def test_recap_persists_and_diagnostic_logging_expires(self):
  clock=[10.]
  with TemporaryDirectory() as d:
   r=CombatRecords(Path(d),clock=lambda:clock[0],ticks=lambda:1000);r.start_validation(10);r.observe(self.state())
   r.preview((1,1,100),(3,1,300),dict(hits=1,failed_normal=100,failed_critical=150),kind='aim')
   r.event(self.event((11,1,110),(13,1,130),150));r.observe(self.state(True))
   lines=[json.loads(line)for line in (Path(d)/'damage-validation.jsonl').read_text().splitlines()]
   damage=next(row for row in lines if row['event']=='damage');self.assertEqual(damage['delta_vs_crit'],0)
   self.assertIn('Temporal candidate',damage['comparison_note'])
   loaded=CombatRecords(Path(d));self.assertEqual(loaded.recent[0]['participants']['verso']['dealt'],150)
   count=len(lines);clock[0]=30.;r._log('late',{})
   self.assertEqual(len((Path(d)/'damage-validation.jsonl').read_text().splitlines()),count)
 def test_native_counter_reset_creates_new_fight_and_invalid_damage_is_not_summed(self):
  r=CombatRecords();s=self.state();s['counters']={'TotalReceivedDamagesByEnemies':100};r.observe(s)
  s['counters']={'TotalReceivedDamagesByEnemies':0};r.observe(s)
  self.assertEqual(len(r.recent),1)
  r.event(self.event((1,1,100),(3,1,300),float('nan')))
  self.assertEqual(r.current['damage'],0);self.assertTrue(r.current['incomplete'])
 def test_ending_can_drain_last_events_before_finalization(self):
  r=CombatRecords();r.observe(self.state(True),defer_finish=True)
  r.event(self.event((1,1,100),(3,1,300),99));r.observe(self.state(True))
  self.assertEqual(r.recent[0]['participants']['verso']['dealt'],99)


class StatisticsViewTests(unittest.TestCase):
 def test_long_recap_pages_without_overlaying_action_controls(self):
  from combat_records_test.statistics_view import StatisticsView
  from expedition33.management import Registry,ManagementError
  r=CombatRecords();fixture=CombatRecordTests();r.observe(fixture.state())
  for i in range(20):r.current['participants']['extra'+str(i)]=dict(name='Party '+str(i),side='party',dealt=i,received=0,hits=1,targets={})
  view=StatisticsView(Registry(None),NS(records=r));frame=view.render()
  self.assertTrue(frame.controls[50].enabled)
  self.assertTrue(all(c.token==-1 for c in frame.controls[60:78]))
  old=frame.revision;frame=view.activate(old,50)
  self.assertIn('Details 2/',frame.status)
  with self.assertRaises(ManagementError):view.activate(old,50)
  while frame.controls[50].enabled:frame=view.activate(frame.revision,50)
  self.assertIn('Historical records',frame.description)
  closed=view.activate(frame.revision,51);self.assertTrue(closed.closed)

class PermanentHistoryTests(CombatRecordTests):
 def test_hits_survive_without_validation_and_inputs_are_detached(self):
  with TemporaryDirectory() as d:
   r=CombatRecords(Path(d),ticks=lambda:1000);r.observe(self.state())
   model=dict(hits=4,failed_normal=100,failed_critical=150,inputs={'live_effect_values':{'buff':{'DamageMultiplier':1.25}}})
   r.preview((1,1,100),(3,1,300),model,kind='basic')
   model['inputs']['live_effect_values']['buff']['DamageMultiplier']=9
   r.event(self.event((1,1,100),(3,1,300),59))
   r.observe(self.state(True))
   loaded=CombatRecords(Path(d));hit=loaded.recent[0]['timeline'][0]
   self.assertEqual(hit['damage'],59)
   self.assertEqual(hit['forecast_candidate']['model']['inputs']['live_effect_values']['buff']['DamageMultiplier'],1.25)
   self.assertFalse((Path(d)/'damage-validation.jsonl').exists())
 def test_checkpoint_recovers_interrupted_fight_and_turn_order(self):
  with TemporaryDirectory() as d:
   r=CombatRecords(Path(d),ticks=lambda:1000);s=self.state();s['turn_actor']=(1,1,100);r.observe(s)
   r.event(self.event((1,1,100),(3,1,300),42));r._save()
   loaded=CombatRecords(Path(d));battle=loaded.recent[0]
   self.assertEqual(battle['outcome'],'capture interrupted')
   self.assertEqual(battle['turns'][0]['name'],'Verso')
   self.assertEqual(battle['timeline'][0]['turn'],1)
 def test_breakdown_views_and_old_records_have_explicit_missing_data(self):
  from combat_records_test.records import battle_history_detail,hit_detail
  self.assertIn('older capture',battle_history_detail({},'hits'))
  text=hit_detail(dict(sequence=1,damage=59))
  self.assertIn('Applied modifiers unavailable',text)

class MarkRecordTests(unittest.TestCase):
 state=CombatRecordTests.state
 event=CombatRecordTests.event
 def test_mark_changes_and_pre_hit_mark_are_permanent(self):
  tick=[900];r=CombatRecords(ticks=lambda:tick[0]);state=self.state()
  state['marks']=({'actor':(3,1,300),'instances':({'identity':(70,1,700),'HitCountToRemoveMark':2},)},)
  r.observe(state);r.observe(state)
  self.assertEqual(len(r.current['mark_changes']),1)
  r.preview((1,1,100),(3,1,300),dict(hits=1,failed_normal=150,failed_critical=225,inputs={'mark':dict(observed=True,remaining_hits=2,multiplier=1.5,affected_hits=1)}),kind='aim')
  r.event(self.event((11,1,110),(13,1,130),225))
  hit=r.current['timeline'][0]
  self.assertEqual(hit['forecast_mark']['remaining_hits'],2)
  self.assertEqual(hit['target_mark_observation']['after'][0]['HitCountToRemoveMark'],2)
  state['marks']=({'actor':(3,1,300),'instances':()},);tick[0]=1100;r.observe(state)
  self.assertEqual(len(r.current['mark_changes']),2)
  self.assertEqual(hit['target_mark_observation']['after'][0]['HitCountToRemoveMark'],2)
  self.assertEqual(r.current['mark_changes'][-1]['after'],())
 def test_unchanged_forecast_interval_survives_busy_hit_delivery(self):
  tick=[100];r=CombatRecords(ticks=lambda:tick[0]);r.observe(self.state());model=dict(hits=1,failed_normal=100,failed_critical=150)
  r.preview((1,1,100),(3,1,300),model,kind='aim')
  for i in range(600):
   tick[0]+=10;r.preview((1,1,100),(3,1,300),model,kind='aim')
  self.assertEqual(len(r.previews),1)
  e=self.event((11,1,110),(13,1,130),150);e.monotonic_ms=6000;r.event(e)
  self.assertEqual(r.current['timeline'][0]['delta_vs_crit'],0)
  frozen=r.current['timeline'][0]['forecast_candidate']['until'];tick[0]=9000;r.preview((1,1,100),(3,1,300),model,kind='aim')
  self.assertEqual(r.current['timeline'][0]['forecast_candidate']['until'],frozen)

 def test_engine_reason_prevents_shot_forecast_being_attached_to_skill_or_proc(self):
  import copy
  for reason,expected in ((3,True),(4,False),(1,False),(6,False)):
   r=CombatRecords(ticks=lambda:900);r.observe(self.state())
   r.preview((1,1,100),(3,1,300),dict(hits=1,failed_normal=100,failed_critical=150),kind='aim')
   evidence=dict(coverage='observed',rejected=0,dropped=0,modifiers=[dict(before=100.,kind=2,value=1.5,affects_base=1,reason='test',damage_reason=reason)])
   r.engine_evidence=NS(match=lambda *args:copy.deepcopy(evidence))
   r.event(self.event((11,1,110),(13,1,130),150))
   hit=r.current['timeline'][0]
   self.assertEqual('forecast_candidate' in hit,expected)
   self.assertTrue(hit['engine_modifiers']['calculation']['reconciled'])
