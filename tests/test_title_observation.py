from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33.world_admission import Admission

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/ui_admission.py'
spec=importlib.util.spec_from_file_location('expedition33._title_observation_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


def result(index=1,path='/Game/Levels/UI/MainMenu/Level_MainMenu.Level_MainMenu'):
    obj=N(pid=7,index=index,serial=1,address=0x10000+index)
    return dict(context=dict(world_path=path,world=(7,1,1,0x10000),controller=(7,2,1,0x20000)),local_player=obj,
                main=obj,title=obj,box=obj)


class TitleObservationTests(unittest.TestCase):
    def observe(self,results,*,current=True):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext())
        observer._title_prewarm_context=Mock(return_value=None)
        observer._detached_prewarm_context=Mock(return_value=None)
        resolver=Mock(side_effect=results)
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('inactive','save_not_loaded')), \
             patch.dict(sys.modules,{'expedition33.title_menu':N(resolve_title_context=resolver,
                 title_authority_current=Mock(return_value=current))}):
            snapshot=observer.observe()
            self.assertEqual(resolver.call_count,1)
            return snapshot

    def test_exact_double_title_chain_admits_title_without_gameplay(self):
        snapshot=self.observe((result(),result()))
        self.assertTrue(snapshot.title_ready);self.assertFalse(snapshot.menu_ready)
        self.assertFalse(snapshot.admission.activation_ready);self.assertIsNotNone(snapshot.title_token)

    def test_wrong_world_and_no_title_are_not_ready(self):
        self.assertFalse(self.observe((None,None)).title_ready)
        self.assertFalse(self.observe((result(path='/Other'),result(path='/Other'))).title_ready)

    def test_changed_widget_identity_is_uncertain(self):
        self.assertIsNone(self.observe((result(),),current=False).title_ready)

    def test_steady_title_revalidates_binding_without_rediscovery(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext())
        resolver=Mock(return_value=result());authority=Mock(return_value=True)
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('inactive','save_not_loaded')), \
             patch.dict(sys.modules,{'expedition33.title_menu':N(resolve_title_context=resolver,
                 title_authority_current=authority)}):
            self.assertTrue(observer.observe().title_ready)
            self.assertTrue(observer.observe().title_ready)
            self.assertEqual(resolver.call_count,1);self.assertEqual(authority.call_count,2)


if __name__=='__main__':unittest.main()
