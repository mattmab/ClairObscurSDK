import unittest
from unittest.mock import Mock,patch
from expedition33.cinematics.timeline_media import TimelineMedia

class TimelineMediaTests(unittest.TestCase):
    def model(self):
        with patch('expedition33.cinematics.timeline_media.OwnedVideoWidget') as factory:
            model=TimelineMedia(object(),Mock(invisible=4,collapsed=1),'./Movies/CS_Film.mp4',(30,1),-30)
        video=model.video
        video.playback_status.return_value=dict(IsReady=True,IsPlaying=False)
        video.media_time.return_value=dict(duration_seconds=10.)
        video.seek.return_value=video.pause.return_value=video.resume.return_value=True
        model.prepare();return model,video
    def test_opening_defers_all_clock_mutations_and_times_out_explicitly(self):
        m,v=self.model();v.playback_status.return_value=dict(IsReady=False)
        self.assertFalse(m.sync(0,False));v.seek.assert_not_called();v.resume.assert_not_called()
        with patch('expedition33.cinematics.timeline_media.time.monotonic',return_value=m.deadline+1):
            with self.assertRaisesRegex(ValueError,'ready'):m.sync(0,False)
    def test_seek_uses_native_rate_and_start_and_coalesces_unchanged_frames(self):
        m,v=self.model();self.assertTrue(m.sync(0,False));v.seek.assert_called_once_with(1.)
        m.sync(0,False);self.assertEqual(v.seek.call_count,1)
        m.sync(30,False);v.seek.assert_called_with(2.)
        m.sync(-99,False);v.seek.assert_called_with(0.)
    def test_play_pause_drift_and_exclusive_video_endpoint(self):
        m,v=self.model();m.sync(0,True);v.resume.assert_called_once()
        v.media_position.return_value=dict(time_seconds=1.2)
        m.sync(6,True);self.assertEqual(v.seek.call_count,1)
        v.media_position.return_value=dict(time_seconds=0.)
        m.sync(30,True);v.seek.assert_called_with(2.)
        m.sync(300,True);v.pause.assert_called_once();self.assertFalse(m.playing)
        self.assertLess(v.seek.call_args.args[0],10.)
    def test_negative_preroll_does_not_start_the_movie_early(self):
        m,v=self.model();m.sync(-40,True)
        v.seek.assert_called_once_with(0.);v.resume.assert_not_called()
        m.sync(-30,True);v.resume.assert_called_once()

    def test_movie_surface_is_hidden_outside_its_duration_and_while_opening(self):
        m,v=self.model()
        self.assertEqual(v._call.call_args.kwargs['InVisibility'],1)
        v.playback_status.return_value=dict(IsReady=False)
        self.assertFalse(m.sync(0,False));self.assertFalse(m.shown)
        v.playback_status.return_value=dict(IsReady=True,IsPlaying=False)
        m.sync(-40,False);self.assertFalse(m.shown)
        m.sync(-30,False);self.assertTrue(m.shown)
        self.assertEqual(v._call.call_args.kwargs['InVisibility'],4)
        m.sync(270,False);self.assertFalse(m.shown)
        self.assertEqual(v._call.call_args.kwargs['InVisibility'],1)
        # Scrubbing backwards restores the movie surface.
        m.sync(0,False);self.assertTrue(m.shown)
        self.assertEqual(v._call.call_args.kwargs['InVisibility'],4)

    def test_authored_spawn_end_hides_and_pauses_before_movie_duration(self):
        m,v=self.model();m.end=0
        m.sync(-15,True);self.assertTrue(m.shown);self.assertTrue(m.playing)
        m.sync(0,True);self.assertFalse(m.shown);self.assertFalse(m.playing)
        self.assertEqual(v._call.call_args.kwargs['InVisibility'],1)
        v.pause.assert_called_once()
        m.sync(-15,False);self.assertTrue(m.shown)

    def test_negative_start_and_exclusive_end_across_forward_and_reverse_scrubs(self):
        # Frame boundaries from the captured Depends Which Family source;
        # this checks clock arithmetic, not that the original renders fullscreen.
        m,v=self.model();m.start=-49.;m.end=773.
        v.media_time.return_value=dict(duration_seconds=60.)
        m.sync(-49.01,False);self.assertFalse(m.shown)
        m.sync(-49.,False);self.assertTrue(m.shown);v.seek.assert_called_with(0.)
        m.sync(772.99,False);self.assertTrue(m.shown)
        self.assertAlmostEqual(v.seek.call_args.args[0],(772.99+49.)/30.)
        m.sync(773.,False);self.assertFalse(m.shown)
        m.sync(772.99,False);self.assertTrue(m.shown)
        m.sync(-49.01,False);self.assertFalse(m.shown)

    def test_movie_audio_pauses_at_exclusive_end_and_resumes_when_reentered(self):
        m,v=self.model();m.start=-49.;m.end=773.
        v.media_time.return_value=dict(duration_seconds=60.)
        v.media_position.return_value=dict(time_seconds=0.)
        m.sync(-49.,True);self.assertTrue(m.playing);v.resume.assert_called_once()
        m.sync(773.,True);self.assertFalse(m.playing);v.pause.assert_called_once()
        m.sync(-49.,True);self.assertTrue(m.playing);self.assertEqual(v.resume.call_count,2)

    def test_rejected_seek_is_not_recorded_as_success(self):
        m,v=self.model();v.seek.return_value=False
        with self.assertRaisesRegex(ValueError,'seeking'):m.sync(0,False)
        self.assertIsNone(m.last);v.resume.assert_not_called()
    def test_known_owner_closes_and_retirement_can_defer(self):
        m,v=self.model();v.state='closed';self.assertTrue(m.close());v.close.assert_called_once()
        v.retire_world.return_value=False;self.assertFalse(m.retire_world())
        v.retire_world.return_value=True;self.assertTrue(m.retire_world())
