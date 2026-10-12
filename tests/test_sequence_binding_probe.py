import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import verify_sequence_binding_query as probe


class BindingProbeTests(unittest.TestCase):
    def setUp(self):
        for target in ('verify_sequence_binding_query.binding_context','pathlib.Path.write_text'):
            patcher=patch(target,return_value={})
            patcher.start();self.addCleanup(patcher.stop)

    def model(self):
        definition,path,digest=probe.PROFILES[0]
        mod=N(video=None,title_replay=None,session=N(_session=N(pid=1,
            _transport=N(sequence_binding_query_protocol=1))),
            native=N(menu=N(panel=N(state='open',uncertain=False))),discover=Mock(),
            discovery={'confirmed':[dict(id=definition,sequence=path,definition_sha256=digest,unlocked=True)]})
        sequence=N(state='ready',uncertain=False,owner=N(state='armed',query_authored_bindings=Mock(return_value={'outcome':1})),
                   build=Mock(),close=Mock())
        catalog=N(objects=(N(index=1,name='MovieSceneSequencePlayer',class_name='Class'),
            N(index=2,name='GetBoundObjects',class_name='Function',outer_index=1)))
        return mod,sequence,catalog

    def test_unlock_rejection_precedes_factory(self):
        mod,_,_=self.model();mod.discovery['confirmed'][0]['unlocked']=False
        with patch.object(probe,'OwnedLevelSequence') as factory:
            with self.assertRaises(RuntimeError):probe.run(mod)
            factory.assert_not_called()

    def test_query_close_and_no_play(self):
        mod,sequence,catalog=self.model()
        with patch.object(probe,'capture_matching',return_value=catalog),patch.object(probe.OwnedLevelSequence,'__new__',return_value=sequence):
            report=probe.run(mod)
        self.assertFalse(report['playback_attempted']);self.assertTrue(report['closed'])
        sequence.owner.query_authored_bindings.assert_called_once_with(1,catalog.objects[1])
        sequence.close.assert_called_once();self.assertIsNone(mod._binding_query_retained)

    def test_unknown_remains_reachable_and_no_retry(self):
        mod,sequence,catalog=self.model();sequence.owner.state='unknown'
        sequence.owner.query_authored_bindings.side_effect=RuntimeError('unknown')
        with patch.object(probe,'capture_matching',return_value=catalog),patch.object(probe.OwnedLevelSequence,'__new__',return_value=sequence):
            report=probe.run(mod)
        self.assertFalse(report['closed']);sequence.close.assert_not_called()
        self.assertIs(mod._binding_query_retained,sequence)
        with self.assertRaisesRegex(RuntimeError,'no retry'):probe.run(mod)


if __name__=='__main__':unittest.main()
