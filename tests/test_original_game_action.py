import unittest
import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics import original_game_action as m

class OriginalActionTests(unittest.TestCase):
    def fixture(self):
        self.enterContext(patch.object(m,'ReadBatch'))
        profile=m.profiles()[m.DEFINITION]
        scene=dict(id=profile['id'],saved_id=profile['saved_id'],sequence=profile['sequence'],definition_sha256=profile['definition_sha256'],unlocked=True)
        session=N(pid=7,_session=N(_transport=N(original_game_action_protocol=1)),console=Mock())
        replay=m.OriginalActionReplay(session,scene,profile)
        history=dict(history=N(items={profile['saved_id']:True}),selected_slot=0,context_identities={'world':(1,2,3,4)})
        return replay,session,history
    def context(self,controller):
        return dict(controller=(1,controller,3,4),world=(1,2,3,4),world_path=m.WORLD)
    def test_map_rows_are_bounded_and_matching_is_exact(self):
        rows=m.profiles();self.assertEqual(len(rows),83)
        r,_,_=self.fixture();self.assertTrue(m.profile_matches(r.profile,r.scene))
        changed=dict(r.scene,definition_sha256='0'*64);self.assertFalse(m.profile_matches(r.profile,changed))
    def test_original_route_history_is_informational_by_user_override(self):
        for unlocked in (False,None):
            replay,session,history=self.fixture();history['history'].items[m.SAVE_ID]=unlocked
            with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',return_value=self.context(10)):
                replay.start()
            session.console.execute.assert_called_once()
    def test_unavailable_history_and_null_save_id_can_travel(self):
        replay,session,history=self.fixture();replay.profile=dict(replay.profile,saved_id=None);replay.scene=dict(replay.scene,saved_id=None)
        with patch.object(m,'read_current_history',side_effect=RuntimeError('history absent')),patch.object(m,'controller_context',return_value=self.context(10)):
            replay.start()
        self.assertIsNone(replay.slot);session.console.execute.assert_called_once()
    def test_travel_recovery_fresh_dispatch_order(self):
        replay,session,history=self.fixture();first=Mock();second=Mock()
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20),self.context(30),self.context(30)]),patch.object(m,'prepare',return_value=second) as prepare,patch.object(m,'recover_spawn') as recover:
            replay.start();session.console.execute.assert_called_once_with('open '+replay.profile['exact_map'])
            replay.poll();prepare.assert_not_called();recover.assert_called_once()
            replay.next_poll=0;replay.poll();second.play.assert_called_once();self.assertEqual(replay.state,'starting')
    def test_timeout_before_dispatch_is_failed_without_retry(self):
        replay,session,history=self.fixture();replay.state='traveling';replay.deadline=-1
        with patch.object(m,'prepare') as prepare:
            self.assertEqual(replay.poll()['state'],'failed');prepare.assert_not_called()
    def test_spawn_recovery_precedes_optional_history_and_uses_fast_poll(self):
        replay,session,history=self.fixture()
        with patch.object(m,'read_current_history',return_value=history) as read,patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20)]),patch.object(m,'recover_spawn') as recover,patch.object(m.time,'monotonic',return_value=100.):
            replay.start();read.reset_mock()
            replay.poll()
            recover.assert_called_once();read.assert_not_called()
            self.assertAlmostEqual(replay.next_poll,100.05)

    def test_background_deferral_is_bounded_and_releases_after_recovery(self):
        from expedition33.management_service import NativeMenuService
        service=NativeMenuService(Mock(),Mock())
        owner=N(state='traveling',deadline=110.)
        service.travel_recovery=owner
        with patch('expedition33.management_service.time.monotonic',return_value=100.):
            self.assertTrue(service.travel_recovery_pending)
            with patch('expedition33.management_service.NativeManagementMenu') as menu:
                service.prepare();menu.assert_not_called()
            owner.state='starting';self.assertFalse(service.travel_recovery_pending)
            owner.state='unknown';self.assertFalse(service.travel_recovery_pending)
            owner.state='traveling';owner.deadline=99.;self.assertFalse(service.travel_recovery_pending)

    def test_readiness_worker_closes_before_teleport(self):
        replay,session,history=self.fixture()
        events=[]
        batch=m.ReadBatch.return_value
        batch.__enter__.side_effect=lambda:events.append('read-open')
        batch.__exit__.side_effect=lambda *args:events.append('read-close')
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20)]),patch.object(m,'recover_spawn',side_effect=lambda _:events.append('teleport')):
            replay.start();replay.poll()
        self.assertEqual(events,['read-open','read-close','teleport'])
        m.ReadBatch.assert_called_once_with(session.pid,share=True)
    def test_unknown_dispatch_is_never_repeated(self):
        replay,session,history=self.fixture();replay.recovered=True;owner=Mock();owner.play.side_effect=RuntimeError('unknown')
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20),self.context(20)]),patch.object(m,'prepare',return_value=owner):
            replay.start();replay.poll();replay.next_poll=0;replay.poll()
        owner.play.assert_called_once();self.assertEqual(replay.state,'unknown')
    def test_same_map_old_controller_cannot_prepare_or_recover(self):
        replay,session,history=self.fixture()
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',return_value=self.context(10)),patch.object(m,'prepare') as prepare,patch.object(m,'recover_spawn') as recover:
            replay.start();replay.poll();self.assertEqual(replay.state,'traveling')
            prepare.assert_not_called();recover.assert_not_called()
    def test_recovery_requires_a_second_new_controller(self):
        replay,session,history=self.fixture();owner=Mock()
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20),self.context(20)]),patch.object(m,'prepare',return_value=owner) as prepare,patch.object(m,'recover_spawn'):
            replay.start();replay.poll();replay.next_poll=0;replay.poll()
            self.assertEqual(replay.state,'recovering');prepare.assert_not_called();owner.play.assert_not_called()
    def test_codec_failure_is_terminal_not_loading_retry(self):
        replay,session,history=self.fixture();replay.recovered=True
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20)]),patch.object(m,'prepare',side_effect=ValueError('bad reflected codec')) as prepare:
            replay.start();replay.poll();replay.next_poll=0;replay.poll()
            self.assertEqual(replay.state,'failed');prepare.assert_called_once()
    def test_exact_read_identity_race_discards_catalog_and_recovers(self):
        expected=self.context(20)
        with patch.object(m,'_controller_context_once',side_effect=[m.RuntimeQueryError('Object identity changed or belongs to another process'),expected]) as read:
            with self.assertRaisesRegex(m.NotReady,'controller_context'):m.controller_context(Mock())
            self.assertEqual(m.controller_context(Mock()),expected);self.assertEqual(read.call_count,2)
    def test_other_query_errors_do_not_become_readiness(self):
        with patch.object(m,'_controller_context_once',side_effect=m.RuntimeQueryError('Invalid descriptor response')):
            with self.assertRaises(m.RuntimeQueryError):m.controller_context(Mock())
    def test_asset_or_planner_identity_error_remains_terminal(self):
        replay,session,history=self.fixture();replay.recovered=True
        with patch.object(m,'read_current_history',return_value=history),patch.object(m,'controller_context',side_effect=[self.context(10),self.context(20)]),patch.object(m,'prepare',side_effect=m.RuntimeQueryError('Object identity changed or belongs to another process')):
            replay.start();result=replay.poll()
        self.assertEqual(result['state'],'failed');self.assertIn('prepare_original_action:',result['error'])
    def test_readonly_preflight_identity_race_precedes_any_scope_or_asset(self):
        replay,session,history=self.fixture();session._check=Mock()
        with patch.object(m,'_read_action_preflight',side_effect=m.RuntimeQueryError('Object identity changed or belongs to another process')),patch.object(m,'SessionScope') as scope,patch.object(m,'load_asset') as load:
            with self.assertRaisesRegex(m.NotReady,'action_read_preflight'):m.prepare(session,replay.scene,replay.profile)
            scope.assert_not_called();load.assert_not_called()
    def test_asset_load_identity_error_is_not_reclassified_as_readiness(self):
        replay,session,history=self.fixture();session._check=Mock();scope=Mock()
        with patch.object(m,'_read_action_preflight',return_value=(Mock(),Mock(),Mock(),Mock(),{})),patch.object(m,'SessionScope',return_value=scope),patch.object(m,'load_asset',side_effect=m.RuntimeQueryError('Object identity changed or belongs to another process')) as load:
            with self.assertRaises(m.RuntimeQueryError):m.prepare(session,replay.scene,replay.profile)
            load.assert_called_once();scope.close.assert_called_once()
    def test_retained_asset_serial_uses_new_catalog_not_preload_merge(self):
        replay,session,history=self.fixture();session._check=Mock();session.pid=7
        def obj(index,serial):return N(pid=7,index=index,serial=serial,address=1000+index,class_name='BP_GameAction_CinematicWithLightingScenario_C')
        old=Mock();old.with_observations.side_effect=AssertionError('Pre-retention catalog must not be merged')
        asset=obj(1,100);executor=obj(2,22);component=obj(3,33);function=obj(4,44)
        fresh=N(by_index={o.index:o for o in (asset,executor,component,function)},path_name=lambda _:replay.profile['action_path'])
        dependencies=object();fresh.with_observations=Mock(return_value=fresh)
        planner=Mock();session.invocation_planner=Mock(return_value=planner);scope=Mock()
        with patch.object(m,'_read_action_preflight',return_value=(old,executor,component,function,{})),patch.object(m,'SessionScope',return_value=scope),patch.object(m,'load_asset',return_value=N(return_value=asset)),patch.object(m,'capture_selected',return_value=fresh) as capture,patch.object(m,'capture_matching',return_value=dependencies) as matching:
            owner=m.prepare(session,replay.scene,replay.profile)
        capture.assert_called_once_with(session.pid,tuple((o.index,o.serial,o.address) for o in (asset,executor,component,function)))
        old.with_observations.assert_not_called();session.invocation_planner.assert_called_once_with(catalog=fresh,selected_results=True)
        matching.assert_called_once_with(session.pid,names=('GameAction','GameActionInstance'));fresh.with_observations.assert_called_once_with(dependencies)
        self.assertIs(owner.scope,scope)

class OriginalActionMenuDisposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('original_action_menu_test',Path(__file__).resolve().parents[1]/'mods/Cinematics/mod.py')
        cls.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.mod)
    def test_travel_disposes_old_view_without_stopping_game_action(self):
        for state in ('traveling','recovering','starting','playing'):
            model=N(original_replay=N(status=lambda:dict(active=True,state=state)),stop=Mock(return_value=False))
            view=self.mod.BrowserView(Mock(),model);view.close()
            self.assertTrue(view.closed);model.stop.assert_not_called()
    def test_owned_title_media_pending_cleanup_still_blocks_close(self):
        model=N(original_replay=None,stop=Mock(return_value=False))
        view=self.mod.BrowserView(Mock(),model)
        with self.assertRaisesRegex(self.mod.ManagementError,'cleanup is still finishing'):view.close()
        self.assertFalse(view.closed);model.stop.assert_called_once()
    def test_original_route_disposes_tree_before_travel_even_when_locked(self):
        model=self.mod.Mod();profile=m.profiles()[m.DEFINITION]
        scene=dict(profile,definition_sha256=profile['definition_sha256'],unlocked=False,supported=True,replay_kind='original_action')
        model.discovery={'all':[scene],'confirmed':[]};model.stop=Mock(return_value=True);model.discover=Mock()
        events=[];panel=N(state='open')
        def dispose():events.append('dispose');panel.state='closed'
        model.native=N(menu=N(panel=panel),parent=N(dispose_menu=dispose));model.session=Mock()
        replay=Mock();replay.start.side_effect=lambda:events.append('travel')
        with patch.object(self.mod,'OriginalActionReplay',return_value=replay):model.control(m.DEFINITION,1)
        self.assertEqual(events,['dispose','travel'])
if __name__=='__main__':unittest.main()
