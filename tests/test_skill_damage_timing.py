import sys,types,unittest
from pathlib import Path
package=types.ModuleType('skill_damage_test');package.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[package.__name__]=package
from skill_damage_test.keyframes import schedule
class SkillTimingTests(unittest.TestCase):
 def test_optional_sequence_absence_does_not_issue_an_empty_query(self):
  from skill_damage_test.keyframes import SkillTimings
  from expedition33 import RuntimeQueryError
  from unittest.mock import patch
  t=SkillTimings(123)
  from types import SimpleNamespace as NS
  anchor=NS(name='Default__LevelSequence',class_name='LevelSequence')
  with patch('skill_damage_test.keyframes.capture_matching',return_value=NS(objects=(anchor,))) as capture:
   t.prime()
   with self.assertRaisesRegex(ValueError,'not loaded'):t.get('Striker')
   self.assertIn('Default__LevelSequence',capture.call_args.kwargs['names'])
  for message in ('IDENTITY_CHANGED','SCHEMA_INVALID','MATCH_RESULTS_EMPTY but unexpected trailer'):
   with patch('skill_damage_test.keyframes.capture_matching',side_effect=RuntimeQueryError(message)):
    with self.assertRaises(RuntimeQueryError):t.discover()

 def test_exploration_prime_rechecks_missing_optional_assets_after_deadline(self):
  from skill_damage_test.keyframes import SkillTimings,SEQUENCES
  from unittest.mock import patch
  from types import SimpleNamespace as NS
  t=SkillTimings(123);asset=NS(name=SEQUENCES['striker'],class_name='LevelSequence')
  with patch('skill_damage_test.keyframes.time.monotonic',return_value=10.),patch('skill_damage_test.keyframes.capture_matching',return_value=NS(objects=())) as capture:
   t.prime();t.prime();self.assertEqual(capture.call_count,1)
  with patch('skill_damage_test.keyframes.time.monotonic',return_value=11.),patch('skill_damage_test.keyframes.capture_matching',return_value=NS(objects=(asset,))) as capture,patch.object(t,'get') as prepare:
   t.prime();self.assertEqual(capture.call_count,1);prepare.assert_called_once_with('striker')

 def test_single_and_multihit_inputs(self):
  self.assertEqual(schedule([(0,50),(1,2)]),(1,))
  self.assertEqual(schedule([(0,50),(1,51),(2,2),(3,2),(4,2)]),(2,2,2))
 def test_inputs_replace_count_and_unsupported_channel_rejected(self):
  self.assertEqual(schedule([(0,50),(1,2),(2,50),(3,52),(4,2)]),(1,2))
  with self.assertRaises(ValueError):schedule([(0,100)])

 def test_missing_loaded_sequences_share_one_bounded_inventory(self):
  from skill_damage_test.keyframes import SkillTimings
  from unittest.mock import patch
  from types import SimpleNamespace as NS
  t=SkillTimings(123)
  with patch('skill_damage_test.keyframes.capture_matching',return_value=NS(objects=())) as capture:
   for name in ('QuickStrike','Striker','Sabotage'):
    with self.assertRaises(ValueError):t.get(name)
   self.assertEqual(capture.call_count,1)
   self.assertIn('SEQ_SkillVerso_Striker',capture.call_args.kwargs['names'])

class BattleEntryPreparationTests(unittest.TestCase):
 def test_hud_is_prepared_before_battle_initialization_without_forecast_numbers(self):
  from types import SimpleNamespace as NS
  from unittest.mock import patch
  from skill_damage_test.observe import CombatObserver,CARD,MANAGER
  manager=NS(index=1,serial=1,address=65536,object_flags=0,class_name=MANAGER)
  card=NS(index=2,object_flags=0,class_name=CARD)
  old_card=NS(index=20,object_flags=0,class_name=CARD)
  hud=NS(index=7,serial=1,address=70000);wheel=NS(index=8)
  description=NS(index=3);tree=NS(index=4);root=NS(index=5,class_name='SizeBox');box=NS(index=6)
  values={1:dict(IsBattleInitialized=False,HasBattleStartedEndFlow=False,BattleScreenWidget=hud),2:dict(SkillDescription=description,DescriptionBox=box),3:dict(WidgetTree=tree),4:dict(RootWidget=root),7:dict(WBP_HUD_WheelsContainer=wheel)}
  paths={1:'/Game/Map:PersistentLevel.Manager',2:'/Engine/Transient.HUD.WBP_HUD_SkillWheel_Skills.Card',8:'/Engine/Transient.HUD',20:'/Engine/Transient.OldHUD.WBP_HUD_SkillWheel_Skills.Card'}
  catalog=NS(select=lambda name:[o for o in (manager,card,old_card) if o.class_name==name],path_name=lambda o:paths[o.index])
  def read(c,objects,fields):return ({o.index:NS(errors={},values={('',name):values[o.index].get(name) for name in fields}) for o in objects},c)
  observer=CombatObserver.__new__(CombatObserver);observer.pid=1
  with patch('skill_damage_test.observe.capture_matching',return_value=catalog),patch('skill_damage_test.observe.read_values_many_with_references',side_effect=read):sample=observer._observe()
  self.assertFalse(sample['battle']['active'])
  self.assertEqual(len(sample['cards']),1)
  _,row,text,visibility=sample['cards'][0]
  self.assertTrue(row['Prewarm']);self.assertEqual(row['ForecastContainer'],root)
  self.assertEqual(text,'');self.assertEqual(visibility['RenderOpacity'],0.)
  values[1]['HasBattleStartedEndFlow']=True
  with patch('skill_damage_test.observe.capture_matching',return_value=catalog),patch('skill_damage_test.observe.read_values_many_with_references',side_effect=read):ending=observer._observe()
  self.assertEqual(len(ending['cards']),1)
  self.assertEqual(ending['cards'][0][2],'')

class BattleCardReassignmentTests(unittest.TestCase):
 def test_unassigned_and_previous_battle_cards_wait_then_rejoin(self):
  from types import SimpleNamespace as NS
  from skill_damage_test.observe import assigned_cards
  card=NS(index=1);actor=NS(index=10);state=NS(index=2);definition=NS(index=3)
  rows={1:dict(SkillState=state,SkillDescription=NS(index=4),DescriptionBox=NS(index=5))}
  states={2:dict(CharacterStats=None,SkillDefinition=definition)}
  self.assertEqual(assigned_cards([card],rows,states,actor),[])
  states[2]['CharacterStats']=NS(outer_index=9)
  self.assertEqual(assigned_cards([card],rows,states,actor),[])
  states[2]['CharacterStats']=NS(outer_index=10)
  self.assertEqual(assigned_cards([card],rows,states,actor),[card])
  states[2]['SkillDefinition']=None
  self.assertEqual(assigned_cards([card],rows,states,actor),[])
 def test_history_releases_previous_battle_receiver_and_resets_failure(self):
  from types import SimpleNamespace as NS
  from skill_damage_test.history import DamageHistory
  closed=[];h=DamageHistory();h.receiver=(1,2,3);h.trace=NS(close=lambda:closed.append(True));h.error='Event capture ended';h.events.append((1,99))
  catalog=NS(objects=(),classes={})
  h.start(None,catalog,(4,5,6))
  self.assertEqual(closed,[True]);self.assertEqual(h.receiver,(4,5,6));self.assertEqual(h.error,'');self.assertEqual(list(h.events),[])

class PreparationReuseTests(unittest.TestCase):
 def test_transient_ui_preparation_failure_keeps_mod_enabled_and_rebuilds_fresh_reader(self):
  from skill_damage_test.mod import Mod
  from expedition33 import RuntimeQueryError
  from unittest.mock import patch
  from contextlib import nullcontext
  from types import SimpleNamespace as NS
  m=Mod();m.session=NS(pid=123);m.ui_preparation_pending=True
  readers=[]
  class Reader:
   def __init__(self,*args,**kwargs):self._closed=False;readers.append(self)
   def warm(self):pass
   def bind(self):return nullcontext()
   def close(self):self._closed=True
  with patch('expedition33._reader.ReadBatch',Reader),patch('skill_damage_test.ui.prepare_definitions',side_effect=[RuntimeQueryError('READ_FAILED'),'definitions']),patch('skill_damage_test.ui.prepare_planning',return_value='planning'):
   self.assertFalse(m._prepare_rendering());self.assertTrue(m.ui_preparation_pending);self.assertFalse(m.stopped)
   self.assertTrue(readers[0]._closed);self.assertIsNone(m.definitions)
   m.next_ui_preparation=0
   self.assertTrue(m._prepare_rendering());self.assertFalse(m.ui_preparation_pending)
   self.assertEqual((m.definitions,m.planning),('definitions','planning'));self.assertEqual(len(readers),2)

 def test_detached_timing_data_survives_reader_replacement_without_inventory(self):
  from skill_damage_test.keyframes import SkillTimings,SEQUENCES
  from unittest.mock import patch
  shared={};first=SkillTimings(123,shared)
  for name in SEQUENCES.values():first.cache[name]=(1,);first.impact_times[name]=(.2,)
  second=SkillTimings(123,shared)
  self.assertIsNone(second.inventory)
  with patch('skill_damage_test.keyframes.capture_matching',side_effect=AssertionError('No rescan of prepared immutable timings')):
   second.prime();self.assertEqual(second.get('QuickStrike'),(1,))
 def test_observer_reuses_only_detached_rules_not_old_world_objects(self):
  from skill_damage_test.observe import CombatObserver
  from unittest.mock import patch
  from types import SimpleNamespace as NS
  shared=dict(tables={'table':{}},callbacks={'callback':{'class'}},buff_classes={'class'})
  with patch('expedition33._reader.ReadBatch',return_value=NS(warm=lambda:None,close=lambda:None)),patch('skill_damage_test.observe.Path.is_file',return_value=True):
   first=CombatObserver(123,shared);first.inventory='old world';second=CombatObserver(123,shared)
  self.assertIs(first.tables,second.tables);self.assertFalse(hasattr(second,'inventory'))
  self.assertIs(first.callback_owners,second.callback_owners)
