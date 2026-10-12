import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33 import _sequence_owner as staged
from expedition33.cinematics.title_profiles import PROLOGUE
from expedition33.cinematics.title_replay import ExactTitleReplay, DEFINITION, SEQUENCE, SAVE_ID


class ReplayPresentationTests(unittest.TestCase):
    def setUp(self):
        self.order = []
        self.panel = SimpleNamespace(state='open', uncertain=False)
        self.sequence = Mock()
        self.sequence.owner.status.return_value = 'armed'
        self.sequence.owner.cleanup_diagnostics = None
        self.sequence.build.side_effect = lambda *a: self.order.append('build')
        self.sequence.play.side_effect = lambda: self.order.append('play')
        self.sequence.close.side_effect = lambda: self.order.append('sequence_close')
        self.sequence.status.return_value = dict(playing=True, paused=False)
        self.adapters = Mock()
        self.adapters.prepare_music.side_effect = lambda: self.order.append('music')
        self.adapters.arm.side_effect = lambda *a: self.order.append('arm')
        self.adapters.close.side_effect = lambda: self.order.append('adapter_close')
        self.adapters.status.return_value = {'armed': True}
        self.visual = SimpleNamespace(state='new')
        def step(name, state):
            self.order.append(name)
            self.visual.state = state
        self.visual.prepare = Mock(side_effect=lambda: step('visual_prepare', 'prepared'))
        self.visual.suspend = Mock(side_effect=lambda: step('suspend', 'suspended'))
        self.visual.restore = Mock(side_effect=lambda: step('restore', 'restored'))
        self.session = SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(cinematic_title_profiles=['prologue_lumiere'], **dict.fromkeys(PROLOGUE.required_protocols,1))))
        self.now = 10.
        discovery = dict(state='history_verified', definition_catalog_complete=True,
            confirmed=[dict(id=DEFINITION, saved_id=SAVE_ID, sequence=SEQUENCE, definition_sha256=PROLOGUE.definition_sha256, unlocked=True)])
        self.replay = ExactTitleReplay(self.session, lambda: self.panel, lambda: discovery,
            adapter_factory=lambda *a: self.adapters, sequence_factory=lambda *a: self.sequence,
            presentation_factory=lambda: self.visual, clock=lambda: self.now)

    def test_prepare_only_then_suspend_before_play_restore_after_all_cleanup(self):
        self.replay.start()
        self.assertEqual(self.order, ['visual_prepare', 'music', 'build', 'arm'])
        self.assertEqual(self.replay.status()['presentation'], 'prepared')
        self.replay.play()
        self.assertEqual(self.order[-2:], ['suspend', 'play'])
        self.replay.stop()
        self.assertEqual(self.order[-3:], ['sequence_close', 'adapter_close', 'restore'])
        self.assertFalse(self.replay.status()['active'])
        self.assertTrue(self.replay.status()['evidence']['presentation_restored'])

    def test_no_restore_until_deferred_sequence_and_adapters_complete(self):
        self.replay.start(play=True)
        self.sequence.close.side_effect = [staged.SequenceCleanupDeferred('draining'), None]
        self.replay.stop()
        self.assertTrue(self.replay.status()['active'])
        self.visual.restore.assert_not_called()
        self.adapters.close.assert_not_called()
        self.assertEqual(self.replay.poll()['state'], 'stopped')
        self.assertEqual(self.order[-2:], ['adapter_close', 'restore'])

    def test_restore_failure_remains_active_without_player_and_poll_never_retries_unknown(self):
        self.replay.start(play=True)
        def fail_restore():
            self.visual.state = 'unknown'
            raise RuntimeError('opacity acknowledgement lost')
        self.visual.restore.side_effect = fail_restore
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaisesRegex(RuntimeError, 'opacity acknowledgement'):
                self.replay.stop()
        self.assertIsNone(self.replay.sequence)
        self.assertIsNone(self.replay.adapters)
        self.assertTrue(self.replay.status()['active'])
        self.assertEqual(self.replay.status()['presentation'], 'unknown')
        self.assertEqual(self.replay.poll()['state'], 'cleanup_pending')
        self.visual.restore.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, 'Stop the current'):
            self.replay.start()

    def test_unknown_suspend_preserves_original_error_and_prevents_play(self):
        original = RuntimeError('suspend acknowledgement lost')
        def suspend():
            self.visual.state = 'unknown'
            raise original
        self.visual.suspend.side_effect = suspend
        self.visual.restore.side_effect = RuntimeError('unknown mutation: no retry')
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(RuntimeError) as raised:
                self.replay.start(play=True)
        self.assertIs(raised.exception, original)
        self.sequence.play.assert_not_called()
        self.assertEqual(self.replay.status()['error'], repr(original))
        self.assertIn('no retry', self.replay.status()['cleanup_error'])
        self.assertTrue(self.replay.status()['active'])

    def test_failed_visual_preparation_never_arms_native_resources(self):
        self.visual.prepare.side_effect = ValueError('opacity unavailable')
        with self.assertLogs('expedition33.cinematics', level='ERROR'):
            with self.assertRaises(ValueError):
                self.replay.start()
        self.adapters.prepare_music.assert_not_called()
        self.sequence.build.assert_not_called()
        self.visual.restore.assert_called_once()
        self.assertFalse(self.replay.status()['active'])

    def test_prepare_only_stop_releases_visual_plans_without_hiding(self):
        self.replay.start()
        self.replay.stop()
        self.visual.suspend.assert_not_called()
        self.visual.restore.assert_called_once()

