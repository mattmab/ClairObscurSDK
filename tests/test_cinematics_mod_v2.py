import hashlib,unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from test_cinematics import module as m
from cinematics_v2_fixtures import Backend,ready_model,poll
from expedition33.cinematics.controller import ControllerState,StopResult
from expedition33.cinematics import original_game_action
from expedition33.management import ManagementError

class FacadeV2Tests(unittest.TestCase):
 def test_accepted_start_precedes_menu_maintenance_and_bypasses_observation_cadence(self):
  model=ready_model(m,self.row());backend=Backend();events=[]
  model.pause=Mock();model.pause.poll.side_effect=lambda:events.append('pause')
  model.native.poll.side_effect=lambda:events.append('menu')
  backend.start.side_effect=lambda:events.append('start') or m.StartResult.STARTED
  with patch.object(m,'TitleAdapter',return_value=backend):
   model.control(m.DEFINITION,1);model._next_playback_poll=float('inf');model.poll()
  self.assertEqual(events,['start']);model._current_epoch.assert_called()
  self.assertEqual(model.controller.status().state,ControllerState.ACTIVE)
  model.poll()
  self.assertEqual(events,['start','pause','menu']);backend.poll.assert_not_called()

 def test_stop_intent_bypasses_cadence_without_replaying_start(self):
  model=ready_model(m,self.row());backend=Backend()
  with patch.object(m,'TitleAdapter',return_value=backend):
   model.control(m.DEFINITION,1);model.poll()
  model._next_playback_poll=float('inf');model.native.poll.reset_mock()
  model.request_stop();model.poll()
  backend.start.assert_called_once();backend.stop.assert_called_once()
  model.native.poll.assert_not_called();self.assertFalse(model.controller.status().busy)

 def test_portable_dispatch_borrows_one_operation_worker_without_caching_observations(self):
  from expedition33._reader import ReadBatch,active_reader,shared_operation
  from expedition33.cinematics.portable import PROFILES
  from expedition33.cinematics.controller import StartResult
  profile=next(iter(PROFILES.values()))
  row=dict(id=profile.definition,title='Reviewed scene',unlocked=True,portable_supported=True,
           replay_kind='portable',definition_sha256=profile.sha256,sequence=profile.sequence)
  model=ready_model(m,row);backend=Backend();starts=[];owners=[]
  def warm(reader):starts.append(reader.pid);return reader
  def dispatch():
   owner=active_reader();self.assertIsNotNone(owner);owners.append(owner)
   with shared_operation(7,_executable='candidate') as borrower:
    self.assertIs(borrower._borrowed,owner)
   return StartResult.STARTED
  backend.start.side_effect=dispatch
  with patch.object(ReadBatch,'warm',warm),patch.object(m,'PortableSceneAdapter',return_value=backend):
   model.control(row['id'],14);poll(model)
   self.assertEqual(starts,[7]);self.assertTrue(owners[0]._closed)
   self.assertIsNone(active_reader());self.assertEqual(model.controller.status().state,ControllerState.ACTIVE)
   poll(model);self.assertEqual(starts,[7])
 def test_prepared_reader_is_rebound_without_restart_or_leaking_into_other_polls(self):
  from expedition33._reader import ReadBatch,active_reader,shared_operation
  from expedition33.cinematics.portable import PROFILES
  profile=next(iter(PROFILES.values()))
  row=dict(id=profile.definition,title='Prepared',unlocked=True,portable_supported=True,replay_kind='portable',definition_sha256=profile.sha256,sequence=profile.sequence)
  model=ready_model(m,row);backend=Backend()
  reader=ReadBatch(7,share=True,_executable='candidate');reader._process=object()
  reader.warm=Mock(side_effect=AssertionError('worker restarted'));reader.close=Mock()
  model._dispatch_reader=reader
  def start():
   self.assertIs(active_reader(),reader)
   with shared_operation(7,_executable='candidate') as borrower:self.assertIs(borrower._borrowed,reader)
   return m.StartResult.STARTED
  backend.start.side_effect=start
  with patch.object(m,'PortableSceneAdapter',return_value=backend):
   for _ in range(2):
    model.control(row['id'],14);poll(model);self.assertIsNone(active_reader())
    model.request_stop();poll(model)
  self.assertEqual(backend.start.call_count,2);reader.warm.assert_not_called()
  model.disable();reader.close.assert_called_once();self.assertIsNone(model._dispatch_reader)

 def test_failed_prepared_reader_cancels_before_backend_allocation_without_retry(self):
  from expedition33._reader import ReadBatch
  from expedition33.cinematics.portable import PROFILES
  profile=next(iter(PROFILES.values()))
  row=dict(id=profile.definition,title='Prepared',unlocked=True,portable_supported=True,replay_kind='portable',definition_sha256=profile.sha256,sequence=profile.sequence)
  model=ready_model(m,row);reader=ReadBatch(7,share=True);reader._closed=True
  model._dispatch_reader=reader
  with patch.object(m,'PortableSceneAdapter') as backend,patch.object(ReadBatch,'warm') as warm:
   model.control(row['id'],14);poll(model);poll(model)
  backend.assert_not_called();warm.assert_not_called()
  self.assertFalse(model.controller.status().busy)
  self.assertIn('closed',model.playback_status)

 def test_installed_clip_uses_owned_media_without_fabricating_unlock(self):
  from expedition33.cinematics.movie_clips import installed_movie_clips
  row,=installed_movie_clips(b'Sandfall/Content/Movies/CS_Test.mp4\tdate\n',available=True,gameplay=True)
  model=ready_model(m,row);backend=Backend()
  with patch.object(m,'MediaAdapter',return_value=backend) as media,patch.object(m,'OriginalActionAdapter') as original:
   model.control(row['id'],1);poll(model)
  media.assert_called_once();original.assert_not_called()
  self.assertFalse(model.controller.status().engine_owned)
  self.assertIsNone(model.library[0]['unlocked'])
  for token in (11,13):
   with self.assertRaises(ManagementError):m.Mod._check_route(row,token)
 def test_movie_original_alternative_uses_original_adapter_and_engine_ownership(self):
  profile=next(p for key,p in original_game_action.profiles().items() if key in m.MEDIA_PROFILES)
  row=dict(id=profile['id'],title='Movie',replay_kind='movie',supported=False,unlocked=None,
           original_supported=True,definition_sha256=profile['definition_sha256'],sequence=profile['sequence'])
  model=ready_model(m,row);backend=Backend()
  with patch.object(m,'OriginalActionAdapter',return_value=backend) as original,patch.object(m,'MediaAdapter') as movie:
   model.control(row['id'],13);poll(model)
  original.assert_called_once();movie.assert_not_called()
  self.assertTrue(model.controller.status().engine_owned)
  self.assertEqual(model._route,'original_action')
  for token in (1,13):
   with self.subTest(token=token),self.assertRaises(ManagementError):
    m.Mod._check_route(dict(row,original_supported=False),token)
 def test_stop_ack_updates_the_restored_browser_without_another_active_poll(self):
  model=ready_model(m,self.row());backend=Backend()
  view=m.WorkspaceBrowserView(N(_check=Mock()),model)
  model.native.menu.view=view
  with patch.object(m,'TitleAdapter',return_value=backend):
   model.control(m.DEFINITION,1);poll(model)
  model.native.parent.refresh.reset_mock()
  model.request_stop();poll(model)
  self.assertFalse(model.controller.status().busy)
  self.assertEqual(model.playback_status,'Playback stopped')
  self.assertEqual(view.status,'Playback stopped')
  model.native.parent.refresh.assert_called_once()
 def test_queued_history_refresh_repaints_the_open_browser_after_observation(self):
  model=ready_model(m,self.row(unlocked=False,supported=False))
  view=m.WorkspaceBrowserView(N(_check=Mock()),model)
  model.native.menu.view=view
  before=view.render()
  def refresh():
   model._pending_refresh=False
   row=self.row()
   model.library=(row,)
   model.discovery={'all':[row],'confirmed':[row],'error':None}
   return model.discovery
  model._refresh_now.side_effect=refresh
  painted=[]
  model.native.parent.refresh.side_effect=lambda:painted.append(view.render())
  view.activate(before.revision,0)
  self.assertEqual(view.status,'Refreshing current-save history')
  model.native.parent.refresh.assert_not_called()
  model.poll()
  self.assertEqual(len(painted),1)
  self.assertEqual(painted[0].status,'Current-save discovery refreshed')
  self.assertTrue(any('Prologue' in c.label for c in painted[0].controls))
  model.poll()
  self.assertEqual(len(painted),1)
 def test_open_from_mods_waits_for_previous_view_detach(self):
  from expedition33.management_service import NativeMenuRoute
  model=m.Mod();model.session=N();model.pause=None
  old=N(panel=N(state='open'),_view_factory=object())
  parent=N(menu=old,poll=Mock(),open=Mock())
  parent.close_menu=Mock()
  model.native=NativeMenuRoute(parent,lambda registry:None)
  model.open();parent.close_menu.assert_not_called();parent.open.assert_not_called()
  model.poll();parent.close_menu.assert_called_once();parent.open.assert_not_called()
  parent.close_menu.side_effect=lambda:setattr(old.panel,'state','built')
  model.poll();parent.open.assert_called_once_with(view_factory=model.native.factory)
  self.assertFalse(model._pending_open)
 def row(self,**changes):
  row=dict(id=m.DEFINITION,title='Prologue',saved_id=m.SAVE_ID,sequence=m.SEQUENCE,
      definition_sha256=m.PROLOGUE.definition_sha256,unlocked=True,supported=True,replay_kind='title',controls=(1,4))
  row.update(changes);return row
 def test_click_is_a_python_intent_without_native_or_backend_io(self):
  model=ready_model(m,self.row())
  with patch.object(m,'shared_operation',side_effect=AssertionError('native read in click')),patch.object(m,'TitleAdapter') as backend:
   model.control(m.DEFINITION,1)
  backend.assert_not_called();model._refresh_now.assert_not_called()
  model.native.parent.close_menu.assert_not_called();self.assertEqual(model.controller.status().state,ControllerState.QUEUED)
 def test_slot_epoch_definition_and_unlock_are_fresh_before_allocation(self):
  for change in ('slot','epoch','definition','unlock'):
   with self.subTest(change=change):
    model=ready_model(m,self.row())
    def refresh():
     if change=='slot':model._slot=2
     elif change=='epoch':model._last_epoch=('another','epoch')
     elif change=='definition':model.library=(self.row(definition_sha256='0'*64),)
     else:model.library=(self.row(unlocked=False),)
     return model.discovery
    model._refresh_now.side_effect=refresh
    with patch.object(m,'TitleAdapter') as factory:
     model.control(m.DEFINITION,1);poll(model);factory.assert_not_called()
    self.assertFalse(model.controller.status().busy)
 def test_original_story_requires_explicit_setting_and_exact_current_map(self):
  profile=original_game_action.profiles()[original_game_action.DEFINITION]
  item=dict(id=profile['id'],title='Story',saved_id=profile['saved_id'],sequence=profile['sequence'],sha256=profile['definition_sha256'])
  catalog=dict(version=1,manifest_sha256=hashlib.sha256(b'fixture').hexdigest(),scenes=[item])
  for allow,world,available in ((False,profile['world_path'],False),(True,'/Game/Other.Other',False),(True,profile['world_path'],True)):
   with self.subTest(allow=allow,world=world):
    rows=m.catalog_scenes({},False,catalog,b'fixture',original_action_available=True,
       allow_original_actions=allow,current_world_path=world,gameplay_world_available=True)
    self.assertIs(rows[0]['original_supported'],available)
  model=m.Mod();self.assertFalse(model.allow_original_actions)
  with self.assertRaises(ManagementError):model._set_original_actions(1)
 def test_title_and_movie_never_fabricate_pause_restart_or_speed(self):
  for kind in ('title','movie'):
   model=ready_model(m,self.row(replay_kind=kind,controls=(1,2,3,4,5)))
   view=m.BrowserView(N(_check=Mock()),model);view.selected=m.DEFINITION;frame=view.render()
   self.assertEqual({c.token for c in frame.controls if c.token in (1,2,3,4,5)},{1,4})
   for token in (2,3,5):
    with self.assertRaises(ManagementError):view.activate(frame.revision,token)
 def test_disable_pending_does_not_replace_or_release_adapter(self):
  from expedition33._sequence_owner import SequenceCleanupDeferred
  model=ready_model(m,self.row());backend=Backend();backend.stop.return_value=StopResult.DEFERRED
  with patch.object(m,'TitleAdapter',return_value=backend):model.control(m.DEFINITION,1);poll(model)
  generation=model.controller.status().generation
  with self.assertRaises(SequenceCleanupDeferred):model.disable()
  self.assertEqual(model.controller.status().generation,generation);self.assertTrue(model.controller.status().busy)
  model.native.close.assert_not_called();backend.close.assert_not_called()
 def test_refresh_and_open_are_deferred_intents(self):
  model=ready_model(m,self.row());model.discover();model.open()
  model._refresh_now.assert_not_called();self.assertTrue(model._pending_refresh);self.assertTrue(model._pending_open)
