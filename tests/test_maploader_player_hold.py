"""Map collision restoration must bracket placement with a player hold."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]/'mods/WorldBuilderMapLoader'
spec=importlib.util.spec_from_file_location('maploader_hold_tests',ROOT/'mod.py',submodule_search_locations=[str(ROOT)])
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
loading=__import__('maploader_hold_tests.loading_context',fromlist=['LoadingContext'])
from maploader_hold_tests.context_observer import MapContext
from maploader_hold_tests.player_hold import PlayerHold

CTX=dict(world='/Game/Test.Test',visit=[1,2,3],pawn=[4,5,6],ready=True)

class HoldTests(unittest.TestCase):
    def test_title_preference_uses_process_registry_without_world_mod_scope(self):
        mod=module.Mod();mod._native_gate=Mock(closed=False)
        registry=N(_settings=Mock());registry._settings.get.return_value={'enabled':False}
        owner=loading.LoadingContext(mod,N(pid=7,_process_ui=N(registry=registry)))
        owner.observe_title(N(kind='title'))
        mod._native_gate.close.assert_called_once()

    def test_loading_hold_requires_assigned_same_world_and_ready_pawn(self):
        mod=module.Mod();mod._startup_assignments={CTX['world']:'a'*32};mod.hold_player=Mock()
        session=N(pid=7);owner=loading.LoadingContext(mod,session);owner.monitor=Mock()
        owner.monitor.snapshot.return_value=N(admission=MapContext(CTX['world'],(1,2,3),(4,5,6),True))
        owner.bind(N(kind='title',world=(7,1,2,3)));mod.hold_player.assert_not_called()
        owner.bind(N(kind='world',world=(7,9,2,3)));mod.hold_player.assert_not_called()
        owner.bind(N(kind='world',world=(7,1,2,3)),preparing=True)
        mod.hold_player.assert_called_once_with(session,CTX)

    def test_restoration_failure_still_releases_player(self):
        mod=module.Mod();mod.current=dict(CTX);mod.session=object();mod.status=lambda:None
        mod.check_legacy=lambda:None;mod.store=Mock();mod.store.read.return_value={'world':CTX['world']}
        mod.runtime=Mock();mod.runtime.profile={}
        events=[];mod.hold_player=lambda *args:events.append('hold')
        mod.runtime.load.side_effect=RuntimeError('failed collision placement')
        mod.release_player=lambda:events.append('release')
        mod.apply('a'*32)
        self.assertEqual(events,['hold','release']);self.assertIn('failed collision placement',mod.message)
        self.assertFalse(getattr(mod,'_startup_map_loaded',False))

    def test_success_releases_only_after_collision_placement_ack(self):
        mod=module.Mod();mod.current=dict(CTX);mod.session=object();mod.status=lambda:None
        mod.check_legacy=lambda:None;mod.store=Mock();mod.store.read.return_value={'world':CTX['world']}
        mod.runtime=Mock();mod.runtime.profile={};events=[]
        mod.hold_player=lambda *args:events.append('hold')
        mod.runtime.close.side_effect=lambda:events.append('cleanup')
        def load(*args):
            events.append('collision placed');return {'objects':1}
        mod.runtime.load.side_effect=load;mod.release_player=lambda:events.append('release')
        mod.apply('a'*32)
        self.assertEqual(events,['hold','cleanup','collision placed','release'])
        self.assertTrue(mod._startup_map_loaded)

    def test_failed_enable_releases_loading_time_hold(self):
        mod=module.Mod();mod._player_hold=Mock()
        mod._enable=Mock(side_effect=RuntimeError('registration failed'))
        hold=mod._player_hold
        with self.assertRaisesRegex(RuntimeError,'registration failed'):mod.enable(object())
        hold.close.assert_called_once();self.assertIsNone(mod._player_hold)

    def test_validation_failure_releases_native_hold_before_python_adoption(self):
        mod=module.Mod();mod.current=dict(CTX);mod.status=lambda:None
        mod.check_legacy=lambda:None;mod.store=Mock();mod.store.read.side_effect=ValueError('Invalid map')
        mod._native_gate=Mock(closed=False)
        mod._native_gate.status.return_value={'state':2,'world':CTX['visit'],'pawn':CTX['pawn']}
        mod.apply('a'*32)
        mod._native_gate.release.assert_called_once_with({'visit':CTX['visit'],'pawn':CTX['pawn']})

    def test_retirement_does_not_release_destination_worlds_native_hold(self):
        mod=module.Mod();mod._world_retiring=True;mod._native_gate=Mock(closed=False)
        mod.release_player();mod._native_gate.status.assert_not_called();mod._native_gate.release.assert_not_called()

    def test_first_ready_sample_restores_assigned_floor_without_two_second_wait(self):
        mod=module.Mod();mod.session=N(pid=7);mod.runtime=Mock(started=False)
        mod.assignments=N(values={CTX['world']:'a'*32});mod._context_monitor=Mock()
        mod._context_monitor.snapshot.return_value=N(admission=MapContext(CTX['world'],(1,2,3),(4,5,6),True))
        mod.hold_player=Mock();mod.apply=Mock()
        mod.poll()
        mod.hold_player.assert_called_once_with(mod.session,CTX);mod.apply.assert_called_once_with('a'*32)

    def test_departed_world_discards_hold_without_movement_callback(self):
        hold=PlayerHold(object(),CTX);hold.held=True;hold.planner=Mock();hold.restore=Mock()
        with patch('maploader_hold_tests.player_hold.context',return_value=dict(CTX,visit=[7,8,9])):hold.close()
        hold.restore.invoke.assert_not_called();self.assertTrue(hold.closed)

    def test_missing_observation_retains_hold_for_release_retry(self):
        hold=PlayerHold(object(),CTX);hold.held=True;hold.planner=Mock();hold.restore=Mock()
        with patch('maploader_hold_tests.player_hold.context',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'fresh pawn observation'):hold.close()
        self.assertTrue(hold.held);self.assertFalse(hold.closed);hold.restore.invoke.assert_not_called()
