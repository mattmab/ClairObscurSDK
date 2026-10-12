"""Composition polling must not miss start or leave sound running on pause."""
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock

from test_cinematics import module as mod
from expedition33.cinematics.media_audio_adapter import MediaAudioAdapter


class CompositionPollingTests(unittest.TestCase):
    def model(self, *, started=True):
        model = mod.Mod()
        model.native = N(menu=N(panel=N(state='open')))
        model.video = Mock(state='opened')
        model.video.audio_dependency = Mock()
        model._play_started = started
        model._paused = False
        model._next_media_poll = 0
        model.stop = Mock(return_value=True)
        return model

    def test_start_uses_fresh_state_and_dispatches_audio_in_same_iteration(self):
        model = self.model(started=False)
        video = model.video
        video.playback_status.side_effect = [
            dict(IsReady=True, IsPlaying=False, IsPaused=False),
            dict(IsPlaying=True, IsPaused=False),
        ]
        video.resume.return_value = True
        model._poll_media()
        self.assertTrue(model._play_started)
        self.assertEqual(video.playback_status.call_count, 2)
        video.audio_dependency.poll.assert_called_once_with(video, True)
        model.stop.assert_not_called()

    def test_unexpected_native_pause_stops_composition_even_when_close_defers(self):
        for closed in (True, False):
            with self.subTest(closed=closed):
                model = self.model()
                model.stop.return_value = closed
                model.video.playback_status.return_value = dict(IsPlaying=False, IsPaused=True)
                model._poll_media()
                model.stop.assert_called_once()
                model.video.audio_dependency.poll.assert_not_called()
                if closed:
                    self.assertEqual(model.playback_status, 'Playback stopped after native media pause')
                else:
                    self.assertNotEqual(model.playback_status, 'Playback stopped after native media pause')

    def test_rejected_resume_cannot_dispatch_audio(self):
        model = self.model(started=False)
        model.video.playback_status.return_value = dict(IsReady=True, IsPlaying=False, IsPaused=False)
        model.video.resume.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'rejected'):
            model._poll_media()
        model.video.audio_dependency.poll.assert_not_called()
        self.assertFalse(model._play_started)

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
