import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_cinematics import module
from cinematics_v2_fixtures import Backend,ready_model,poll
from expedition33.cinematics.controller import ReplayObservation,BackendState
from expedition33.cinematics.title_replay import ExactTitleReplay
from expedition33.cinematics.title_profiles import PROLOGUE

class TitleStatusTimingTests(unittest.TestCase):
    def test_browser_reads_cached_status_and_only_changed_states_refresh(self):
        row=dict(id=module.DEFINITION,title='Prologue',reason='ready',replay_kind='title',supported=True,unlocked=True)
        mod=ready_model(module,row);view=module.BrowserView(N(_check=Mock()),mod)
        view.selected=module.DEFINITION;view.status='Starting';mod.native.menu.view=view
        backend=Backend();backend.poll.return_value=ReplayObservation(BackendState.ACTIVE,'Title: ended')
        mod.controller.queue(row['id'],lambda:backend,mod._last_epoch);mod.controller.poll(mod._last_epoch)
        mod.playback_status='Starting';poll(mod)
        self.assertEqual(view.render().status,'Title: ended');mod.native.parent.refresh.assert_called_once()
        backend.poll.reset_mock();view.render();view.render();backend.poll.assert_not_called()
        poll(mod);mod.native.parent.refresh.assert_called_once()

    def test_other_views_are_not_refreshed_by_title_status(self):
        mod=ready_model(module,dict(id='title',title='Title'));backend=Backend()
        backend.poll.return_value=ReplayObservation(BackendState.ACTIVE,'Title: ended')
        mod.controller.queue('title',lambda:backend,mod._last_epoch);mod.controller.poll(mod._last_epoch)
        mod.native.menu.view=object();poll(mod);mod.native.parent.refresh.assert_not_called()

    def test_timing_records_failed_phase_without_retry(self):
        replay=ExactTitleReplay.__new__(ExactTitleReplay);replay.evidence={}
        operation=Mock(side_effect=RuntimeError('failed'))
        with patch('expedition33.cinematics.title_replay.time.perf_counter',side_effect=[10.,12.5]):
            with self.assertRaisesRegex(RuntimeError,'failed'):replay._prepare_step('music',operation)
        self.assertEqual(replay.evidence['preparation_timings']['music'],dict(seconds=2.5,completed=False))
        operation.assert_called_once()

    def test_unlock_failure_precedes_owner_creation(self):
        sequence_factory=Mock();adapters=Mock()
        replay=ExactTitleReplay(N(_session=N(_transport=N(cinematic_title_profiles=['prologue_lumiere'],**dict.fromkeys(PROLOGUE.required_protocols,1)))),lambda:N(state='open',uncertain=False),lambda:{},
            adapter_factory=adapters,sequence_factory=sequence_factory)
        with self.assertRaises(RuntimeError):replay.start()
        adapters.assert_not_called();sequence_factory.assert_not_called()
        self.assertFalse(replay.evidence['preparation_timings']['unlock']['completed'])

if __name__=='__main__':unittest.main()

