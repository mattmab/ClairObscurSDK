import importlib,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_cinematics import module as facade
from expedition33.ui_shell_proof import UiProofPending
from expedition33 import process_ui # Keep real proof/router imports outside temporary test module maps.

from pathlib import Path
spec=importlib.util.spec_from_file_location('cinematic_loading_tests',Path(__file__).resolve().parents[1]/'mods/Cinematics/loading.py')
loading=importlib.util.module_from_spec(spec);spec.loader.exec_module(loading)

class CinematicLoadingTests(unittest.TestCase):
    def fixture(self):
        mod=N(prepare_loading_pause=Mock(return_value=Mock(state='attached',retire_world=Mock(return_value='ack'))));session=N(pid=7,_transport=N(_executable='reader'));gi=(7,10,20,30)
        context=N(gi=gi,kind='title',signature=('title',))
        with patch.object(loading,'SessionScope',return_value=Mock(_closed=False)):
            owner=loading.LoadingReplay(mod,session)
        deps=Mock(gi=gi)
        with patch.object(loading,'CinematicDependencies',return_value=deps):owner.prepare(context)
        return owner,mod,deps,context

    def test_title_prepares_metadata_once_without_allocating_world_panel(self):
        owner,mod,deps,title=self.fixture()
        with patch.object(loading,'CinematicPanelPool') as pool:owner.observe_title(title)
        deps.prepare.assert_called_once();pool.assert_not_called()
        self.assertIs(mod._loading_replay,owner)

    def test_world_handoff_reuses_metadata_but_never_old_controller_panel(self):
        owner,mod,deps,title=self.fixture()
        first=N(gi=title.gi,kind='world',controller=(7,1,2,3),signature=('first',))
        second=N(gi=title.gi,kind='world',controller=(7,1,2,3),signature=('second',))
        old=Mock();old.retire_world.side_effect=('pending','ack')
        new=Mock()
        with patch.object(loading,'CinematicPanelPool',side_effect=(old,new)) as pool,patch('expedition33.cinematics.history.PreparedHistorySelectors'),patch('expedition33._reader.ReadBatch'):
            owner.bind(first,preparing=True);owner.bind(first)
            with self.assertRaises(UiProofPending):owner.bind(second,preparing=True)
            self.assertIs(owner.pool,old);self.assertEqual(pool.call_count,1)
            owner.bind(second,preparing=True)
            self.assertIs(owner.pool,new);self.assertEqual(pool.call_count,2)
        deps.prepare.assert_called_once();deps.close.assert_not_called()
        old.prepare.assert_called_once();new.prepare.assert_called_once()

    def test_different_gi_is_rejected_before_new_panel_construction(self):
        owner,mod,deps,title=self.fixture()
        with patch.object(loading,'CinematicPanelPool') as pool:
            with self.assertRaisesRegex(RuntimeError,'GameInstance'):
                owner.bind(N(gi=(7,9,9,9),kind='world',controller=(7,1,2,3),signature=('other',)))
        pool.assert_not_called()

    def test_adoption_requires_exact_fresh_context_and_cannot_repeat(self):
        owner,mod,deps,title=self.fixture()
        pool=Mock(closed=False,context={'world':'current','controller':'current'})
        owner.pool=pool;owner.pause=Mock(state='attached')
        session=N(_session=owner.session)
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=lambda:{'world':'current','controller':'other'}):
            with self.assertRaisesRegex(RuntimeError,'activation'):owner.take(session)
        self.assertFalse(owner.adopted)
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=lambda:pool.context):
            self.assertIs(owner.take(session),pool)
            self.assertIsNone(owner.take(session))

    def test_unattached_pause_does_not_adopt_or_rebuild_the_pool(self):
        owner,mod,deps,title=self.fixture();owner.pool=Mock(closed=False)
        owner.pause=Mock(state='new');context=N(controller=(7,1,2,3))
        with self.assertRaises(UiProofPending):owner._prepare_pause(context)
        with self.assertRaises(UiProofPending):owner.take(N(_session=owner.session))
        self.assertFalse(owner.adopted);owner.pool.prepare.assert_not_called()

    def test_activation_borrows_the_reader_warmed_during_loading(self):
        from unittest.mock import MagicMock
        mod=facade.Mod();reader=MagicMock();mod._loading_replay=N(reader=reader)
        mod._enable=Mock();session=N(pid=7,_session=N(_transport=N(_executable='reader')))
        with patch('expedition33._reader.active_reader',return_value=None),patch.object(facade,'shared_operation') as cold:
            mod.enable(session)
        reader.bind.assert_called_once();cold.assert_not_called()
        mod._enable.assert_called_once_with(session);reader.close.assert_not_called()

    def test_pause_discovery_race_defers_only_before_construction(self):
        from expedition33 import RuntimeQueryError
        owner,mod,deps,title=self.fixture();owner.pause=Mock(state='prepared')
        owner.pause.install.side_effect=RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')
        with self.assertRaises(UiProofPending):owner._prepare_pause(N(controller=(7,1,2,3)))
        def partial():
            owner.pause.state='building';raise RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')
        owner.pause.install.side_effect=partial
        with self.assertRaises(RuntimeQueryError):owner._prepare_pause(N(controller=(7,1,2,3)))

    def test_controller_not_ready_before_panel_allocation_retires_and_retries(self):
        from expedition33.cinematics.original_game_action import NotReady
        owner,mod,deps,title=self.fixture()
        context=N(gi=title.gi,kind='world',controller=(7,1,2,3),signature=('world',))
        first=Mock(panel=None,context=None,retire_world=Mock(return_value='ack'))
        first.prepare.side_effect=NotReady('Player controller is not available yet')
        second=Mock()
        with patch.object(loading,'CinematicPanelPool',side_effect=(first,second)),patch('expedition33.cinematics.history.PreparedHistorySelectors'),patch('expedition33._reader.ReadBatch'):
            with self.assertRaises(UiProofPending):owner.bind(context,preparing=True)
            self.assertIsNone(owner.pool);self.assertIsNone(owner.signature)
            first.retire_world.assert_called_once();mod.prepare_loading_pause.assert_not_called()
            owner.bind(context)
            second.prepare.assert_called_once();self.assertIs(owner.pool,second)

    def test_not_ready_after_panel_allocation_is_not_replayed(self):
        from expedition33.cinematics.original_game_action import NotReady
        owner,mod,deps,title=self.fixture()
        pool=Mock(panel=object(),context={});pool.prepare.side_effect=NotReady('late failure')
        with patch.object(loading,'CinematicPanelPool',return_value=pool):
            with self.assertRaises(NotReady):owner.bind(N(gi=title.gi,kind='world',signature=('world',)))
        pool.retire_world.assert_not_called();self.assertIs(owner.pool,pool)
