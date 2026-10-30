"""Composition polling must not miss start or leave sound running on pause."""
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock

from test_cinematics import module as mod
from expedition33.cinematics.media_audio_adapter import MediaAudioAdapter


class CompositionPollingTests(unittest.TestCase):
    def adapter(self, *, started=True):
        from expedition33.cinematics.adapters import MediaAdapter
        adapter = MediaAdapter(None, {}, None, None, None)
        adapter.backend = Mock(state='opened')
        adapter.backend.audio_dependency = Mock()
        adapter.running = started
        adapter.opening_deadline = float('inf')
        return adapter

    def test_start_uses_fresh_state_and_dispatches_audio_in_same_iteration(self):
        adapter = self.adapter(started=False)
        video = adapter.backend
        video.playback_status.side_effect = [
            dict(IsReady=True, IsPlaying=False, IsPaused=False),
            dict(IsPlaying=True, IsPaused=False),
        ]
        video.resume.return_value = True
        adapter.poll()
        self.assertTrue(adapter.running)
        self.assertEqual(video.playback_status.call_count, 2)
        video.audio_dependency.poll.assert_called_once_with(video, True)
        video.close.assert_not_called()

    def test_unexpected_native_pause_stops_composition_even_when_close_defers(self):
        from expedition33.cinematics.controller import ReplayController, StartResult
        for closed in (True, False):
            with self.subTest(closed=closed):
                adapter = self.adapter()
                adapter.start = Mock(return_value=StartResult.STARTED)
                video = adapter.backend
                video.close.return_value = closed
                video.playback_status.return_value = dict(IsPlaying=False, IsPaused=True)
                controller = ReplayController()
                controller.queue('movie', lambda: adapter, 'epoch')
                controller.poll('epoch')
                controller.poll('epoch')
                video.close.assert_called_once()
                video.audio_dependency.poll.assert_not_called()
                self.assertEqual(controller.status().busy, not closed)

    def test_rejected_resume_cannot_dispatch_audio(self):
        adapter = self.adapter(started=False)
        adapter.backend.playback_status.return_value = dict(IsReady=True, IsPlaying=False, IsPaused=False)
        adapter.backend.resume.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'not acknowledged'):
            adapter.poll()
        adapter.backend.audio_dependency.poll.assert_not_called()
        self.assertFalse(adapter.running)

    def test_clock_failure_is_recorded_without_dispatch(self):
        audio = object.__new__(MediaAudioAdapter)
        audio.state = 'running'
        audio.error = None
        audio.dispatcher = Mock()
        video = Mock()
        video.media_position.side_effect = ValueError('invalid native media clock')
        with self.assertRaisesRegex(ValueError, 'invalid native media clock'):
            audio.poll(video, True)
        self.assertEqual(audio.state, 'failed')
        self.assertIn('invalid native media clock', audio.error)
        audio.dispatcher.advance.assert_not_called()


if __name__ == '__main__':
    unittest.main()
