import unittest
import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33 import _sequence_owner as staged
from expedition33.cinematics.title_profiles import PROLOGUE
from expedition33.cinematics.title_replay import ExactTitleReplay, DEFINITION, SEQUENCE, SAVE_ID


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.order = []
        self.panel = SimpleNamespace(state='open', uncertain=False)
        self.discovery = dict(state='history_verified', definition_catalog_complete=True,
            confirmed=[dict(id=DEFINITION, saved_id=SAVE_ID, sequence=SEQUENCE, definition_sha256=PROLOGUE.definition_sha256, unlocked=True)])
        self.discover = Mock(side_effect=lambda: self.discovery)
        self.adapters = Mock()
        self.adapters.prepare_music.side_effect = lambda: self.order.append('music')
        self.adapters.arm.side_effect = lambda sequence: self.order.append('arm')
        self.adapters.close.side_effect = lambda: self.order.append('adapter_close')
        self.adapters.status.return_value = dict(widgets=dict(state='armed', observed=0, failed=0),
                                                  sound=dict(state='armed', observed=0, failed=0))
        self.sequence = Mock()
        self.sequence.owner.status.return_value = 'armed'
        self.sequence.build.side_effect = lambda *args: self.order.append('build')
        self.sequence.play.side_effect = lambda: self.order.append('play')
        self.sequence.close.side_effect = lambda: self.order.append('sequence_close')
        self.sequence.status.return_value = dict(playing=False, paused=False)
        self.now = 10.
        session = SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(cinematic_title_profiles=['prologue_lumiere'], **dict.fromkeys(PROLOGUE.required_protocols,1))))
        self.replay = ExactTitleReplay(session, lambda: self.panel, self.discover,
            adapter_factory=Mock(return_value=self.adapters), sequence_factory=Mock(return_value=self.sequence),
            clock=lambda: self.now)

    def test_prepare_never_plays_and_explicit_play_refreshes_unlock(self):
        self.replay.start()
        self.assertEqual(self.order, ['music', 'build', 'arm'])
        self.assertEqual(self.replay.status()['state'], 'armed')
        self.replay.play()
        self.assertEqual(self.discover.call_count, 2)
        self.assertEqual(self.order[-1], 'play')
        self.assertFalse(self.replay.status()['live_playback_verified'])

    def test_fail_closed_on_unknown_false_numeric_unlock_and_wrong_definition(self):
        for value in (None, False, 1):
            self.discovery['confirmed'][0]['unlocked'] = value
            with self.assertRaises(RuntimeError):
                self.replay.start()
        with self.assertRaises(ValueError):
            self.replay.start('another_definition')
        self.replay.adapter_factory.assert_not_called()

    def test_changed_save_between_arm_and_play_closes_without_play(self):
        self.replay.start()
        self.discovery['confirmed'][0]['unlocked'] = False
        with self.assertRaises(RuntimeError):
            self.replay.play()
        self.assertEqual(self.order[-2:], ['sequence_close', 'adapter_close'])
        self.sequence.play.assert_not_called()

    def test_preparation_failure_closes_allocated_owners(self):
        self.adapters.arm.side_effect = ValueError('guard')
        with self.assertRaises(ValueError):
            self.replay.start()
        self.assertEqual(self.order[-2:], ['sequence_close', 'adapter_close'])
        self.sequence.play.assert_not_called()

    def test_cleanup_deferred_preserves_both_owners_for_retry(self):
        self.replay.start()
        self.sequence.close.side_effect = RuntimeError('deferred')
        with self.assertRaises(RuntimeError):
            self.replay.stop()
        self.assertEqual(self.replay.state, 'cleanup_pending')
        self.assertIs(self.replay.sequence, self.sequence)
        self.assertIs(self.replay.adapters, self.adapters)
        self.adapters.close.assert_not_called()
        self.sequence.close.side_effect = None
        self.replay.stop()
        self.adapters.close.assert_called_once()

    def test_bounded_poll_and_engine_end_is_not_live_acceptance(self):
        self.replay.start(play=True)
        self.sequence.status.return_value = dict(playing=True, paused=False)
        self.replay.poll()
        self.replay.poll()
        self.sequence.status.assert_called_once()
        self.sequence.status.return_value = dict(playing=False, paused=False)
        self.now += .2
        self.assertEqual(self.replay.poll()['state'], 'ended')
        self.assertFalse(self.replay.status()['live_playback_verified'])

    def test_panel_replacement_stops_without_polling_stale_player(self):
        self.replay.start(play=True)
        self.panel = SimpleNamespace(state='open', uncertain=False)
        self.assertEqual(self.replay.poll()['state'], 'context_closed')
        self.sequence.status.assert_not_called()

    def test_never_observed_and_hard_timeout_clean_up(self):
        self.replay.start(play=True)
        self.now += 4
        self.assertEqual(self.replay.poll()['state'], 'not_observed')
        self.replay.start()
        self.now += 181
        self.assertEqual(self.replay.poll()['state'], 'timed_out')

    def test_native_escape_closure_does_not_invoke_closed_player(self):
        self.replay.start(play=True)
        self.sequence.owner.status.return_value = 'closed'
        self.assertEqual(self.replay.poll()['state'], 'native_closed')
        self.sequence.status.assert_not_called()

    def test_guard_failure_during_poll_stops_before_adapter_close(self):
        self.replay.start(play=True)
        self.adapters.status.side_effect = RuntimeError('native failure')
        with self.assertRaises(RuntimeError):
            self.replay.poll()
        self.assertEqual(self.order[-2:], ['sequence_close', 'adapter_close'])

    def test_original_and_cleanup_errors_persist_before_loader_stringifies(self):
        self.replay.start(play=True)
        original = RuntimeError('Native sequence rejected (407, 0)')
        cleanup = RuntimeError('Unknown sequence ownership outcome')
        self.sequence.owner.status.side_effect = original
        self.sequence.close.side_effect = cleanup
        logger = logging.getLogger('expedition33.cinematics')
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / 'failure.log'
            handler = logging.FileHandler(path, encoding='utf8')
            logger.addHandler(handler)
            try:
                with self.assertRaises(RuntimeError) as raised:
                    self.replay.poll()
                self.assertIs(raised.exception, original)
                handler.flush()
                text = path.read_text(encoding='utf8')
                self.assertIn('Native sequence rejected (407, 0)', text)
                self.assertIn('Unknown sequence ownership outcome', text)
                self.assertIn('Cinematic failed status:', text)
                self.assertIn('cleanup_pending', text)
            finally:
                logger.removeHandler(handler)
                handler.close()
        status = self.replay.status()
        self.assertEqual(status['error'], repr(original))
        self.assertEqual(status['cleanup_error'], repr(cleanup))
        self.assertEqual(status['evidence']['failure']['phase'], 'poll')
        self.assertEqual(status['evidence']['cleanup_failure']['type'], 'RuntimeError')
        self.assertIs(self.replay.adapters, self.adapters)
        self.adapters.close.assert_not_called()

    def test_start_play_propagation_does_not_retry_failed_cleanup(self):
        original = ValueError('Play callback failed')
        self.sequence.play.side_effect = original
        self.sequence.close.side_effect = RuntimeError('cleanup deferred')
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(ValueError) as raised:
                self.replay.start(play=True)
        self.assertIs(raised.exception, original)
        self.sequence.close.assert_called_once()
        self.assertEqual(self.replay.status()['evidence']['failure']['phase'], 'play')

    def test_successful_cleanup_does_not_erase_original_failure(self):
        self.replay.start(play=True)
        original = ValueError('malformed reply')
        self.sequence.status.side_effect = original
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(ValueError) as raised:
                self.replay.poll()
        self.assertIs(raised.exception, original)
        self.assertEqual(self.replay.status()['state'], 'failed')
        self.assertEqual(self.replay.status()['error'], repr(original))
        self.assertIsNone(self.replay.status()['cleanup_error'])

    def test_proven_cleanup_deferral_retries_close_only_without_loader_error(self):
        self.replay.start(play=True)
        self.sequence.close.side_effect = [staged.SequenceCleanupDeferred('draining'), None]
        self.assertEqual(self.replay.stop()['state'], 'cleanup_pending')
        self.adapters.close.assert_not_called()
        self.sequence.status.reset_mock()
        self.sequence.owner.status.reset_mock()
        self.assertEqual(self.replay.poll()['state'], 'stopped')
        self.sequence.status.assert_not_called()
        self.sequence.owner.status.assert_not_called()
        self.adapters.close.assert_called_once()

    def test_deferral_retry_is_throttled_and_has_a_hard_deadline(self):
        self.replay.start(play=True)
        self.sequence.close.side_effect = staged.SequenceCleanupDeferred('draining')
        self.replay.stop()
        self.replay.poll()
        calls = self.sequence.close.call_count
        self.replay.poll()
        self.assertEqual(self.sequence.close.call_count, calls)
        self.now += 6
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaisesRegex(RuntimeError, 'five-second'):
                self.replay.poll()
        self.assertEqual(self.sequence.close.call_count, calls)
        self.assertIs(self.replay.sequence, self.sequence)
        self.adapters.close.assert_not_called()

    def test_unknown_cleanup_never_polls_engine_again(self):
        self.replay.start()
        self.sequence.close.side_effect = RuntimeError('unknown native outcome')
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(RuntimeError):
                self.replay.stop()
        self.sequence.owner.status.reset_mock()
        self.replay.poll()
        self.sequence.owner.status.assert_not_called()
        self.sequence.status.assert_not_called()

    def test_cleanup_timeout_preserves_first_error(self):
        self.replay.start()
        self.replay.error = 'original playback error'
        self.sequence.close.side_effect = staged.SequenceCleanupDeferred('draining')
        self.replay.stop()
        self.now += 6
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(RuntimeError):
                self.replay.poll()
        self.assertEqual(self.replay.error, 'original playback error')
        self.assertIn('five-second', self.replay.cleanup_error)

    def test_cleanup_diagnostics_survive_native_failure_and_owner_release(self):
        self.replay.start()
        self.sequence.owner.cleanup_diagnostics = {'phase': 3, 'owner_state': 2, 'reason': 1493}
        self.sequence.close.side_effect = RuntimeError('Native sequence rejected (1493, 0)')
        with self.assertLogs('expedition33.cinematics', level='ERROR') as captured:
            with self.assertRaises(RuntimeError):
                self.replay.stop()
        self.assertEqual(self.replay.status()['evidence']['native_audio_cleanup']['reason'], 1493)
        self.assertTrue(any('native_audio_cleanup' in line for line in captured.output))
        self.sequence.close.side_effect = None
        self.replay.stop()
        self.assertIsNone(self.replay.sequence)
        self.assertEqual(self.replay.status()['evidence']['native_audio_cleanup']['phase'], 3)


if __name__ == '__main__':
    unittest.main()

