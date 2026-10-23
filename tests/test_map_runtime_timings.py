import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path,submodule_search_locations=[str(path.parent)] if name=='map_loader_timing_test' else None)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
runtime=module('expedition33.map_runtime_timing_test',ROOT/'src/expedition33/map_runtime.py')
loader=module('map_loader_timing_test',ROOT/'mods/WorldBuilderMapLoader/mod.py')
state=module('map_loader_state_test',ROOT/'mods/WorldBuilderMapLoader/state.py')
class Timings(unittest.TestCase):
    def test_native_timings_keep_failure_without_replay(self):
        owner=runtime.MapRuntime.__new__(runtime.MapRuntime);owner.profile={}
        calls=[]
        def send(op,**kwargs):calls.append(op);raise RuntimeError('not dispatched')
        owner._send_packet=send
        with patch.object(runtime.time,'perf_counter',side_effect=[10.,10.125]):
            with self.assertRaises(RuntimeError):owner._send(97,path='/Game/Only.Test')
        self.assertEqual(calls,[97]);self.assertEqual(owner.profile['native_97']['total_ms'],125.)
        self.assertNotIn('/Game/',str(owner.profile))
    def test_loader_timing_status_contains_only_aggregates_and_is_detached(self):
        mod=loader.Mod();mod.runtime=type('Runtime',(),{'profile':{'native_94':{'calls':1,'items':32,'total_ms':4.,'max_ms':4.}}})()
        mod.current={'world':'private'}
        with patch.object(loader.time,'perf_counter',return_value=2.):mod._mark('enable',1.)
        report=mod.timing_status();self.assertEqual(report['stages']['enable']['total_ms'],1000.)
        self.assertNotIn('private',str(report));report['stages']['enable']['calls']=9
        self.assertEqual(mod.timings['enable']['calls'],1)
    def test_once_per_exact_visit_survives_absence(self):
        visit=state.Visits();ctx=dict(world='/Game/Test.Test',visit=[1,2,3],pawn=[4,5,6],ready=True)
        self.assertFalse(visit.observe(ctx,0));self.assertFalse(visit.observe(ctx,1));self.assertTrue(visit.observe(ctx,2))
        visit.attempted=True
        self.assertFalse(visit.observe(None,3));self.assertFalse(visit.observe(ctx,4));self.assertFalse(visit.observe(ctx,9))
        new=dict(ctx,visit=[1,3,4]);self.assertFalse(visit.observe(new,10));self.assertTrue(visit.observe(new,12))
    def test_pawn_change_restarts_gate_without_duplicate_attempt(self):
        visit=state.Visits();ctx=dict(world='/Game/Test.Test',visit=[1,2,3],pawn=[4,5,6],ready=True)
        visit.observe(ctx,0);new=dict(ctx,pawn=[4,6,7]);self.assertFalse(visit.observe(new,2));self.assertFalse(visit.observe(new,3));self.assertTrue(visit.observe(new,4))
        visit.attempted=True;self.assertFalse(visit.observe(ctx,10));self.assertFalse(visit.observe(ctx,12))
if __name__=='__main__':unittest.main()
