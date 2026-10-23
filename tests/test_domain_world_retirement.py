import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
from concurrent.futures import Future
from unittest import TestCase
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
def module(folder):
    name='retirement_'+folder
    spec=importlib.util.spec_from_file_location(name,ROOT/'mods'/folder/'mod.py',submodule_search_locations=[str(ROOT/'mods'/folder)])
    import sys
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value
SCENE=module('SceneEditor');ENEMY=module('EnemySpawner');FLIGHT=module('ContinentFlight');PICTO=module('PictoEditor');CINEMATIC=module('Cinematics')
CONTEXT=N(previous_token=((1,2,3,4),(1,5,6,7),(1,8,9,10),0),next_token=None,reason='title')

class DomainRetirementTests(TestCase):
    def test_flight_waits_read_worker_without_landing_or_restoring_old_tuning(self):
        model=FLIGHT.Mod();future=Future();future.set_running_or_notify_cancel()
        model.discovery_future=future;model.discovery_worker=Mock();model.planner=Mock();model._close_reader=Mock()
        model.land=Mock(side_effect=AssertionError('old pawn write'));model._restore_flight_tuning=Mock(side_effect=AssertionError('old tuning write'))
        model.flying=True;model.flight_tuning=['old'];model.revoke_world(CONTEXT)
        self.assertEqual(model.begin_world_retirement(CONTEXT),'pending');model.planner.close.assert_not_called()
        future.set_result('old read snapshot')
        self.assertEqual(model.poll_world_retirement(CONTEXT),'ack');self.assertFalse(model.flying);self.assertEqual(model.flight_tuning,[])
        model.land.assert_not_called();model._restore_flight_tuning.assert_not_called();model._close_reader.assert_called_once_with()
    def test_scene_retains_native_owner_without_stop_or_old_world_ui_writes(self):
        model=SCENE.Mod();model.want_play=model.want_timeline=True;model.pending_edit=('delete','event')
        model.runtime.scope=object();model.runtime.session=N(_session=N(_transport=N(retired_world_cleanup_protocol=0)));model.runtime.stop=Mock(side_effect=AssertionError('old input/music compensation'))
        model.revoke_world(CONTEXT);self.assertFalse(model.want_play);self.assertIsNone(model.pending_edit)
        self.assertEqual(model.begin_world_retirement(CONTEXT),'unknown');self.assertIsNotNone(model.runtime.scope)
        model.runtime.stop.assert_not_called()
        model.runtime.scope=None;self.assertEqual(model.poll_world_retirement(CONTEXT),'ack')
    def test_enemy_pending_owner_is_retained_and_completed_close_not_replayed(self):
        model=ENEMY.Mod();npc=Mock();npc.close.return_value=True
        spawner=Mock();spawner.original_fight=N(_world_replaced=False);spawner.close.side_effect=[False,True]
        model.npc_encounter=npc;model.spawner=spawner;model._direct_pending={'recipe':'old'};model.revoke_world(CONTEXT)
        self.assertIsNone(model._direct_pending);self.assertEqual(model.begin_world_retirement(CONTEXT),'pending')
        self.assertIs(model.spawner,spawner);self.assertTrue(spawner.original_fight._world_replaced)
        self.assertEqual(model.poll_world_retirement(CONTEXT),'ack');npc.close.assert_called_once_with();self.assertEqual(spawner.close.call_count,2)
    def test_cinematics_active_playback_and_pause_restore_are_held(self):
        model=CINEMATIC.Mod();model.title_replay=N(sequence=object(),adapters=None,presentation=None)
        model.stop=Mock(side_effect=AssertionError('old camera/music/presentation restore'));model.revoke_world(CONTEXT)
        self.assertEqual(model.begin_world_retirement(CONTEXT),'unknown');model.stop.assert_not_called()
        model.title_replay=None;model.pause=N(state='attached',close=Mock(),retire_world=Mock(return_value='unknown'))
        self.assertEqual(model.poll_world_retirement(CONTEXT),'unknown');model.pause.close.assert_not_called();model.pause.retire_world.assert_called_once_with()
    def picto_editor(self):
        editor=PICTO.StockEditor.__new__(PICTO.StockEditor)
        editor.restore_queue=['old'];editor.catalog_request='old';editor.lumina_ui_pending=True
        editor.unlock_confirm=editor.clear_confirm='old';editor.bulk_job=None;editor.unlock_bulk=None;editor.unlock_transaction=None
        editor.catalog_future=editor.refresh_future=None;editor.worker_reader=None;editor.main_reader=Mock();editor.refresh_worker=Mock()
        close_future=Future();close_future.set_result(None);editor.refresh_worker.submit.return_value=close_future
        editor.card_layout=N(planner=Mock(),saved={'old':'layout'},pending='old');editor.planner=Mock();editor.observers=[]
        editor.attachment=Mock();editor.attachment.close.return_value=True
        editor.restore_originals=Mock(side_effect=AssertionError('old baseline write'));editor.card_layout.close=Mock(side_effect=AssertionError('old borrowed UI write'))
        return editor
    def test_picto_retirement_cancels_native_queue_without_reconcile_or_compensation(self):
        editor=self.picto_editor();job=N(native=True,dispatched=True,error=None,queue=['old'],cancelled=False,future=None,_command=Mock(return_value=3),stop=Mock(),poll=Mock())
        editor.unlock_bulk=job;editor.revoke_world(CONTEXT)
        self.assertEqual(editor.retire_world(CONTEXT),'pending');self.assertEqual(job.queue,[]);job._command.assert_called_once_with(3)
        self.assertEqual(editor.retire_world(CONTEXT),'ack');job._command.assert_called_once_with(3)
        job.stop.assert_not_called();job.poll.assert_not_called();editor.restore_originals.assert_not_called();editor.card_layout.close.assert_not_called()
        self.assertIsNone(editor.attachment)
        self.assertEqual(editor.card_layout.saved,{})
    def test_picto_unknown_native_job_never_retries_cancel_or_discards_journal(self):
        editor=self.picto_editor();job=N(native=True,dispatched=True,error='unknown acknowledgement',queue=[],future=None,_command=Mock())
        editor.unlock_bulk=job;editor.revoke_world(CONTEXT)
        self.assertEqual(editor.retire_world(CONTEXT),'unknown');job._command.assert_not_called();self.assertIs(editor.unlock_bulk,job)
        editor.refresh_worker.submit.assert_not_called()

    def test_enemy_active_tuning_retains_old_manager_without_restore(self):
        model=ENEMY.Mod();model.spawner=N(_tuning=N(attempted=True,closed=False),helper_encounter=None,close=Mock())
        model.revoke_world(CONTEXT)
        self.assertEqual(model.begin_world_retirement(CONTEXT),'unknown');model.spawner.close.assert_not_called()
