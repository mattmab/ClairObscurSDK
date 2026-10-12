import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import verify_sequence_camera_capture as probe

class CaptureProbeTests(unittest.TestCase):
    def model(self):
        profile=next(p for p in probe.TITLE_PROFILES.values() if p.profile_id=='back_at_camp')
        transport=N(cinematic_title_profiles=('back_at_camp',))
        for capability in profile.required_protocols:setattr(transport,capability,1)
        mod=N(video=None,title_replay=None,session=N(_session=N(_transport=transport)),
            native=N(menu=N(panel=N(state='open',uncertain=False))),discover=Mock(),
            discovery={'confirmed':[dict(id=profile.definition,saved_id=profile.saved_id,
                sequence=profile.sequence,sha256=profile.definition_sha256,unlocked=True)]})
        sequence=N(state='ready',uncertain=False,owner=N(state='armed'),build=Mock(),close=Mock())
        return mod,sequence

    def test_mod_scope_is_unwrapped_and_no_play_is_called(self):
        mod,sequence=self.model()
        with patch.object(probe,'OwnedLevelSequence',return_value=sequence):result=probe.run(mod)
        self.assertTrue(result['closed']);self.assertFalse(result['playback_attempted'])
        self.assertTrue(sequence.build.call_args.kwargs['capture_camera'])
        sequence.close.assert_called_once();self.assertIsNone(mod._camera_capture_retained)

    def test_unlock_failure_refuses_factory(self):
        mod,_=self.model();mod.discovery['confirmed'][0]['unlocked']=False
        with patch.object(probe,'OwnedLevelSequence') as factory:
            with self.assertRaises(RuntimeError):probe.run(mod)
            factory.assert_not_called()

    def test_unknown_owner_remains_reachable_without_retry(self):
        mod,sequence=self.model();sequence.owner.state='unknown'
        sequence.build.side_effect=RuntimeError('uncertain dispatch')
        with patch.object(probe,'OwnedLevelSequence',return_value=sequence):result=probe.run(mod)
        self.assertFalse(result['closed']);sequence.close.assert_not_called()
        self.assertIs(mod._camera_capture_retained,sequence)
        with self.assertRaisesRegex(RuntimeError,'no retry'):probe.run(mod)

if __name__=='__main__':unittest.main()
