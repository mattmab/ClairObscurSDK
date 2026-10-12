import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import verify_media_rebuild as probe


class MediaRebuildTests(unittest.TestCase):
    def model(self, unlocked=True):
        p = probe.MEDIA_PROFILES[probe.ALICIA]
        scene = dict(id=p.definition, saved_id=p.saved_id, sequence=p.sequence,
                     sha256=p.definition_sha256, unlocked=unlocked)
        return N(video=None, title_replay=None, session=object(),
                 native=N(menu=N(panel=N(state='open', uncertain=False))),
                 discover=Mock(), discovery={'confirmed':[scene]})

    def video(self, fail=False, uncertain=False):
        video = N(state='new', uncertain=False, widget=None, source=None, player=None,
                  native_owner=None, scope=N(_leases=[]))
        def build(*args):
            video.state = 'building'
            if fail:
                video.uncertain = uncertain
                raise ValueError('Media cleanup targets differ (object_flags)')
            video.state = 'configured'
        video.build = Mock(side_effect=build)
        video.close = Mock(side_effect=lambda: setattr(video,'state','closed'))
        return video

    def test_bounds_and_unlock_refuse_allocation(self):
        with patch.object(probe,'OwnedVideoWidget') as factory:
            for count in (0,7,True,1.5):
                with self.assertRaises(ValueError):probe.run(self.model(),count)
            with self.assertRaisesRegex(RuntimeError,'freshly unlocked'):
                probe.run(self.model(False))
            factory.assert_not_called()

    def test_repeated_known_resources_close_without_play_or_attach(self):
        model = self.model(); videos = [self.video() for _ in range(6)]
        with patch.object(probe,'OwnedVideoWidget',side_effect=videos):result=probe.run(model)
        self.assertTrue(result['complete']); self.assertEqual(len(result['iterations']),6)
        self.assertFalse(result['playback_attempted']); self.assertFalse(result['attached'])
        self.assertEqual(model.discover.call_count,6)
        self.assertIsNone(model._media_rebuild_retained)
        for video in videos:video.close.assert_called_once()

    def test_known_build_failure_closes_once_and_stops(self):
        video=self.video(fail=True); model=self.model()
        with patch.object(probe,'OwnedVideoWidget',return_value=video) as factory:
            result=probe.run(model)
        factory.assert_called_once();video.close.assert_called_once()
        self.assertFalse(result['complete']);self.assertTrue(result['iterations'][0]['closed'])
        self.assertIn('object_flags',result['iterations'][0]['build_error'])

    def test_unknown_build_failure_retains_without_cleanup_retry(self):
        video=self.video(fail=True,uncertain=True);model=self.model()
        with patch.object(probe,'OwnedVideoWidget',return_value=video):result=probe.run(model)
        video.close.assert_not_called();self.assertIs(model._media_rebuild_retained,video)
        self.assertFalse(result['iterations'][0]['closed'])
        with self.assertRaisesRegex(RuntimeError,'no retry'):probe.run(model)

    def test_active_replay_and_missing_menu_refused(self):
        for attr,value in (('video',object()),('native',None)):
            model=self.model();setattr(model,attr,value)
            with patch.object(probe,'OwnedVideoWidget') as factory:
                with self.assertRaises(RuntimeError):probe.run(model)
                factory.assert_not_called()


if __name__=='__main__':unittest.main()
