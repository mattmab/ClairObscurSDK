import unittest
from unittest.mock import Mock, patch

from expedition33.cinematics.adapters import OriginalActionAdapter
from expedition33.cinematics.controller import BackendState, ReplayController, ControllerState, StartResult


class OriginalActionCompletionTests(unittest.TestCase):
    def test_known_final_context_rejection_is_not_an_unknown_dispatch(self):
        from expedition33.cinematics.original_game_action import NotReady
        prepared=Mock()
        prepared.play.side_effect=NotReady('world replaced during preparation')
        adapter=OriginalActionAdapter(None,{}, {})
        with patch('expedition33.cinematics.original_game_action.prepare',return_value=prepared), \
             patch('expedition33.cinematics.adapters._prepared_action_source'), \
             patch('expedition33._original_action_observation.CinematicActionMonitor'):
            self.assertEqual(adapter.start(), StartResult.REJECTED)
        self.assertFalse(adapter.dispatch_acknowledged)
        self.assertEqual(adapter.last.state, BackendState.FAILED)

    def adapter(self):
        adapter = OriginalActionAdapter(None, {}, {})
        adapter.dispatch_acknowledged = True
        adapter._observe_activity = Mock(return_value=(False, False))
        return adapter

    def test_unobserved_dispatch_releases_tracking_as_failure_not_visual_success(self):
        adapter = self.adapter()
        with patch('expedition33.cinematics.adapters.time.monotonic', return_value=0):
            self.assertEqual(adapter.poll().state, BackendState.ACTIVE)
        with patch('expedition33.cinematics.adapters.time.monotonic', return_value=11):
            self.assertEqual(adapter.poll().state, BackendState.ACTIVE)
            self.assertEqual(adapter.poll().state, BackendState.FAILED)
        self.assertIn('playback unverified', adapter.last.detail)

    def test_observed_action_waits_for_cinematic_retirement(self):
        adapter = self.adapter()
        adapter._observe_activity.side_effect = [(True, True), (False, True), (False, False)]
        self.assertEqual(adapter.poll().state, BackendState.ACTIVE)
        self.assertEqual(adapter.poll().state, BackendState.ACTIVE)
        self.assertEqual(adapter.poll().state, BackendState.COMPLETE)

    def test_read_failure_breaks_stable_idle_window(self):
        adapter = self.adapter()
        with patch('expedition33.cinematics.adapters.time.monotonic', return_value=0):
            adapter.poll()
        adapter._observe_activity.side_effect = OSError('transient read')
        with self.assertRaises(OSError):
            adapter.poll()
        self.assertIsNone(adapter.idle_since)
        adapter._observe_activity.side_effect = None
        with patch('expedition33.cinematics.adapters.time.monotonic', return_value=20):
            self.assertEqual(adapter.status().state, BackendState.ACTIVE)

    def test_unknown_dispatch_cannot_expire_or_read_stale_objects(self):
        adapter = self.adapter()
        adapter.dispatch_acknowledged = False
        self.assertEqual(adapter.status().state, BackendState.UNKNOWN)
        self.assertEqual(adapter.poll().state, BackendState.UNKNOWN)
        adapter._observe_activity.assert_not_called()

    def test_controller_recovers_from_transient_poll_failure_without_restarting_action(self):
        adapter = self.adapter()
        adapter.start = Mock(return_value=StartResult.STARTED)
        adapter.close = Mock(return_value=True)
        adapter.stop = Mock(side_effect=AssertionError('Game owns playback'))
        adapter._observe_activity.side_effect = [(True, True), OSError('read failed'), (False, False)]
        controller = ReplayController()
        controller.queue('scene', lambda: adapter, 'world', engine_owned=True)
        controller.poll('world')
        controller.poll('world')
        self.assertEqual(controller.poll('world').state, ControllerState.UNCERTAIN)
        self.assertEqual(controller.poll('world').state, ControllerState.IDLE)
        adapter.start.assert_called_once()
        adapter.stop.assert_not_called()
        adapter.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
