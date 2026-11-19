"""Speech/listen/speech must survive observation of the generated montage."""
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33.prepared_invocation import PreparedInvocation
from expedition33.story_facial import DialogueFacialPerformance


class FacialPlanRefreshTests(unittest.TestCase):
    def make_owner(self):
        actor=N(index=1, serial=2, address=100, class_index=20)
        clip=N(index=3, serial=4, address=300, class_index=21)
        play='/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage'
        stop='/Script/Engine.AnimInstance:Montage_Stop'
        functions={play:N(index=5),stop:N(index=6)}
        class Planner:
            _generation=1
            _check=Mock()
            def __init__(self):
                self._catalog=N(by_index={1:actor,3:clip},find_path=functions.__getitem__)
            def prepare(self,obj,fn,**kwargs):
                return PreparedInvocation(self,N(target=obj,function=fn,wire_version=12 if fn is functions[play] else 1))
            prepare_dialogue_slot=prepare
            def adopt_observations(self,observations):
                self._catalog.by_index.update(observations.by_index)
                self._generation+=1
        planner=Planner()
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.scope=N(pid=7)
        owner.calls={((1,2,100),path):planner.prepare(actor,fn) for path,fn in functions.items()}
        return owner,planner,actor,clip,play,stop

    def test_speech_after_stop_rebuilds_revoked_sibling_without_dispatch(self):
        owner,planner,actor,clip,play,stop=self.make_owner()
        original=owner.calls[((1,2,100),play)]
        montage=N(index=7,serial=8,address=700,class_index=22)
        with patch('expedition33.story_facial.capture_selected',return_value=N(by_index={7:montage})):
            owner._prepare_call(actor,stop,Montage=montage)
        with self.assertRaisesRegex(RuntimeError,'revoked'):original.bind(Asset=clip)
        with patch.object(PreparedInvocation,'invoke') as dispatch:
            next_call=owner._prepare_call(actor,play,Asset=clip)
            self.assertEqual(next_call._generation,planner._generation)
            next_call._check()
            dispatch.assert_not_called()
        self.assertIs(owner.calls[((1,2,100),play)],next_call)

    def test_refreshed_target_generation_cannot_be_substituted(self):
        owner,planner,actor,clip,play,_=self.make_owner()
        planner._generation+=1
        planner._catalog.by_index[1]=N(index=1,serial=99,address=100,class_index=20)
        with self.assertRaisesRegex(RuntimeError,'target changed'):
            owner._prepare_call(actor,play,Asset=clip)

    def test_failed_refresh_does_not_fall_back_to_old_plan(self):
        owner,planner,actor,clip,play,_=self.make_owner()
        planner._generation+=1;planner._catalog=None
        with self.assertRaisesRegex(RuntimeError,'Refresh the facial planner'):
            owner._prepare_call(actor,play,Asset=clip)

    def test_closed_planner_stays_closed(self):
        owner,planner,actor,clip,play,_=self.make_owner()
        planner._check=Mock(side_effect=RuntimeError('Invocation planner is closed'))
        with self.assertRaisesRegex(RuntimeError,'closed'):
            owner._prepare_call(actor,play,Asset=clip)
