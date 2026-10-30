import copy,hashlib,json,unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33.cinematics.portable import PROFILES,PortableSceneAdapter,available,REQUIRED_PROTOCOLS
from expedition33.cinematics.library import catalog_scenes
from expedition33.cinematics.controller import StartResult,StopResult
from expedition33.cinematics.browser_view import BrowserView

class PortableAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.catalog=json.loads((Path(__file__).resolve().parents[1]/'mods/Cinematics/catalog.json').read_text())
  self.catalog['manifest_sha256']=hashlib.sha256(b'fixture').hexdigest()
  self.profile=next(p for p in PROFILES.values() if p.saved_id=='LuneArrives')
 def scene(self,unlock=True,**kw):
  return next(r for r in catalog_scenes({self.profile.saved_id:unlock},False,self.catalog,b'fixture',
   portable_scene_available=kw.get('runtime',True),gameplay_world_available=kw.get('world',True),
   current_world_path=kw.get('path','/Game/Levels/WorldMap/Camps/Level_Camp_Main.Level_Camp_Main')) if r['id']==self.profile.definition)
 def test_route_does_not_require_original_map_or_story_effects(self):
  row=self.scene();self.assertTrue(row['portable_supported']);self.assertFalse(row['original_supported'])
  self.assertEqual(row['replay_kind'],'portable');self.assertEqual(row['controls'],(14,4))
 def test_exact_unlock_and_runtime_and_loaded_world_required(self):
  for unlock in (False,None,1,'true'):self.assertFalse(self.scene(unlock)['portable_supported'])
  for kw in ({'runtime':False},{'world':False},{'path':None}):self.assertFalse(self.scene(**kw)['portable_supported'])
 def test_changed_definition_or_sequence_never_inherits_portable_route(self):
  for key,value in (('sha256','0'*64),('sequence','/Game/Other.Other'),('saved_id','Other')):
   with self.subTest(key=key):
    old=copy.deepcopy(self.catalog)
    next(r for r in self.catalog['scenes'] if r['id']==self.profile.definition)[key]=value
    self.assertFalse(self.scene()['portable_supported']);self.catalog=old
 def test_full_filter_keeps_portable_play_and_stop(self):
  row=self.scene();model=NS(library=(row,),playback_status='',reason='',control=Mock())
  model.filter='full';view=BrowserView(Mock(),model);view.selected=row['id'];frame=view.render()
  self.assertIn(14,[c.token for c in frame.controls]);self.assertIn(4,[c.token for c in frame.controls])
 def test_boolean_protocols_do_not_advertise_portable_playback(self):
  values=dict.fromkeys(REQUIRED_PROTOCOLS,1);self.assertTrue(available(NS(**values)))
  for name in REQUIRED_PROTOCOLS:
   self.assertFalse(available(NS(**dict(values,**{name:True}))))
 def test_adapter_rejects_locked_or_changed_scene_before_any_native_allocation(self):
  scope=NS(_session=NS(_transport=NS()))
  for row in (self.scene(False),dict(self.scene(),definition_sha256='0'*64)):
   with patch('expedition33.simon_portable._snapshot') as snapshot:
    self.assertEqual(PortableSceneAdapter(scope,row).start(),StartResult.REJECTED)
    snapshot.assert_not_called()

class PortableCleanupTests(unittest.TestCase):
 def adapter(self):return PortableSceneAdapter(None,{})
 def test_prepared_panel_detaches_after_consumers_and_is_not_destroyed(self):
  a=self.adapter();events=[];panel=Mock()
  a.sequence=NS(close=lambda:events.append('sequence'));a.services=NS(close=lambda:events.append('services'))
  a.panel=panel;a._pool_acquired=True
  a.panel_pool=Mock();a.panel_pool.release.side_effect=lambda p:events.append('panel.detach') or True
  self.assertEqual(a.stop(),StopResult.STOPPED)
  self.assertEqual(events,['sequence','services','panel.detach'])
  panel.close.assert_not_called();self.assertFalse(a._pool_acquired);self.assertIsNone(a.panel)
 def test_deferred_pool_detach_keeps_adapter_ownership(self):
  a=self.adapter();a.panel=Mock();panel=a.panel;a._pool_acquired=True;a.panel_pool=Mock()
  a.panel_pool.release.return_value=False
  self.assertEqual(a.stop(),StopResult.DEFERRED)
  self.assertIs(a.panel,panel);self.assertTrue(a._pool_acquired)
 def test_retired_consumer_returns_panel_through_retirement_path(self):
  a=self.adapter();a.panel=Mock();panel=a.panel;a._pool_acquired=True;a.panel_pool=Mock()
  a.panel_pool.release.return_value=True
  self.assertTrue(a.close(NS(epoch_valid=False)))
  a.panel_pool.release.assert_called_once_with(panel,retired=True)
  panel.close.assert_not_called();panel.retire_world.assert_not_called()
 def test_normal_cleanup_stops_sequence_before_private_services_and_panel(self):
  a=self.adapter();events=[]
  a.sequence=NS(close=lambda:events.append('sequence'))
  a.services=NS(close=lambda:events.append('services'))
  a.panel=NS(close=lambda:events.append('panel'))
  self.assertEqual(a.stop(),StopResult.STOPPED);self.assertEqual(events,['sequence','services','panel'])
 def test_deferred_sequence_cleanup_keeps_private_services_alive(self):
  from expedition33._sequence_owner import SequenceCleanupDeferred
  a=self.adapter();a.sequence=Mock();a.sequence.close.side_effect=SequenceCleanupDeferred('GC')
  a.services=Mock();a.panel=Mock()
  self.assertEqual(a.stop(),StopResult.DEFERRED);a.services.close.assert_not_called();a.panel.close.assert_not_called()
 def test_world_replacement_never_stops_or_restores_old_world(self):
  a=self.adapter();sequence=Mock();sequence.retire_world.return_value=True
  services=Mock();services.retire_world.return_value=True
  panel=Mock();panel.retire_world.return_value='ack'
  a.sequence,a.services,a.panel=sequence,services,panel
  self.assertTrue(a.close(NS(epoch_valid=False)))
  sequence.close.assert_not_called();services.close.assert_not_called();panel.close.assert_not_called()
  sequence.retire_world.assert_called_once_with(closed_dependents=(services.widgets,))
 def test_world_retirement_deferral_does_not_discard_services(self):
  a=self.adapter();a.sequence=Mock();a.sequence.retire_world.return_value=False;a.services=Mock()
  self.assertFalse(a.close(NS(epoch_valid=False)));self.assertIsNotNone(a.sequence);a.services.retire_world.assert_not_called()

class PortableDispatchTests(unittest.TestCase):
 def test_playback_status_uses_sampled_progress_without_another_engine_query(self):
  from expedition33.cinematics.adapters import PreviewAdapter
  adapter=PreviewAdapter(None,{})
  adapter.sequence=Mock()
  adapter.sequence.completion.return_value=dict(state='playing',endpoint_observed=False,
       position_seconds=74.8,end_seconds=178.1666667)
  report=adapter.poll()
  self.assertEqual(report.detail,'Preview: playing | 74.8 / 178.2 s')
  adapter.sequence.completion.assert_called_once_with()
  self.assertEqual([c[0] for c in adapter.sequence.mock_calls],['completion'])

 def run_dispatch(self,changed=False):
  profile=next(iter(PROFILES.values()))
  scene=dict(id=profile.definition,saved_id=profile.saved_id,sequence=profile.sequence,
             sha256=profile.sha256,unlocked=True)
  events=[];transport=NS(**dict.fromkeys(REQUIRED_PROTOCOLS,1),_executable='reader')
  scope=NS(pid=42,_session=NS(_transport=transport));context={'world':'current'}
  @contextmanager
  def reader(*args,**kw):
   events.append('reader.open')
   try:yield
   finally:events.append('reader.close')
  panel=NS(build=lambda:events.append('build'),open=lambda:events.append('lock'))
  services=NS(prepare_music=lambda:events.append('music.prepare'),arm=lambda s:events.append('music.pause'))
  def build_sequence(*args,**kwargs):
   self.assertIs(kwargs['completion'],True);events.extend(('sequence','endpoint'))
  sequence=NS(build=build_sequence,play=lambda:events.append('play'))
  with patch('expedition33.simon_portable._snapshot',return_value=(context,None,(0.,0.,0.))),\
       patch('expedition33.cinematics.portable.shared_operation',side_effect=reader),\
       patch('expedition33.cinematic_context_panel.CinematicContextPanel',return_value=panel),\
       patch('expedition33.cinematics.title_adapters.OwnedSequenceContext',return_value=services),\
       patch('expedition33.sequences.OwnedLevelSequence',return_value=sequence) as construct,\
       patch('expedition33.cinematics.original_game_action.controller_context',return_value={} if changed else context):
   result=PortableSceneAdapter(scope,scene).start()
   construct.assert_called_once_with(scope)
  return result,events
 def test_input_is_acquired_after_panel_construction_and_music_handoff_follows_endpoint(self):
  result,events=self.run_dispatch()
  self.assertEqual(result,StartResult.STARTED)
  self.assertEqual(events,['reader.open','build','lock','music.prepare','sequence','endpoint','music.pause','play','reader.close'])
 def test_replaced_context_never_pauses_original_music_or_starts_playback(self):
  result,events=self.run_dispatch(changed=True)
  self.assertEqual(result,StartResult.REJECTED)
  self.assertNotIn('music.pause',events);self.assertNotIn('play',events)
  self.assertEqual(events[-1],'reader.close')
