import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
from contextlib import nullcontext
from unittest.mock import Mock,patch
import sys,unittest
from expedition33.cinematics import history
spec=importlib.util.spec_from_file_location('expedition33._prewarm_admission',Path(__file__).resolve().parents[1]/'src/expedition33/ui_admission.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def obj(n,kind):return N(pid=7,index=n,serial=1,address=100+n,class_name=kind,object_flags=0)
def identity(o):return(o.pid,o.index,o.serial,o.address)
class PrewarmAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.world=obj(1,'World');self.gi=obj(2,'GameInstance');self.pc=obj(3,'BP_jRPG_Controller_MainMenu_C');self.lp=obj(4,'LocalPlayer')
        self.catalog=N(by_index={3:self.pc},path_name=lambda o:'/Game/Levels/UI/MainMenu/Level_MainMenu.Level_MainMenu',find_class=lambda name:object(),outer_chain=lambda o:(self.world,))
        self.observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        self.observer.pid=7;self.observer._reader=N(bind=lambda:nullcontext());self.observer._ui_local_player=identity(self.lp)
        self.observer.engine_catalog=Mock(return_value=self.catalog)
        self.observer.controller=Mock(return_value=dict(world=identity(self.world),controller=identity(self.pc)))
    def run_probe(self,chains=None):
        with patch.object(history,'anchor',side_effect=chains,return_value=((None,None,self.world,self.gi),self.catalog)),patch.object(m,'capture_selected',return_value=self.catalog),patch.object(m,'read_object_reference',return_value=(self.lp,self.catalog)):
            return self.observer._title_prewarm_context()
    def test_two_fresh_proofs_create_only_copied_title_context(self):
        found=self.run_probe();self.assertEqual(found.kind,'title');self.assertEqual(found.controller,identity(self.pc))
        self.assertEqual(self.observer.controller.call_count,2);self.assertEqual(self.observer.engine_catalog.call_count,2)
    def test_wrong_controller_class_never_grants_prewarm(self):
        self.pc.class_name='PlayerController';self.assertIsNone(self.run_probe())
    def test_anchor_change_between_proofs_never_grants_prewarm(self):
        changed=obj(8,'GameInstance')
        self.assertIsNone(self.run_probe([((None,None,self.world,self.gi),self.catalog),((None,None,self.world,changed),self.catalog)]))
    def test_controller_outer_world_mismatch_never_grants_prewarm(self):
        self.catalog.outer_chain=lambda o:(obj(9,'World'),);self.assertIsNone(self.run_probe())
    def test_exact_null_anchor_transition_is_pending_without_retry(self):
        with patch.object(history,'anchor',side_effect=RuntimeError('Current history context reference is null')) as anchor:
            self.assertIsNone(self.observer._title_prewarm_context())
        anchor.assert_called_once()
    def test_unknown_runtime_schema_error_is_not_treated_as_transition(self):
        with patch.object(history,'anchor',side_effect=RuntimeError('Unexpected reflected schema')):
            with self.assertRaisesRegex(RuntimeError,'Unexpected reflected schema'):
                self.observer._title_prewarm_context()
if __name__=='__main__':unittest.main()
