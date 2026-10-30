import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.authored_activity import disable_sections


class ActivityTests(unittest.TestCase):
    def fixture(self):
        root=N(index=1,serial=1,address=65536,class_name='LevelSequence',name='Root')
        outer=N(index=2,serial=1,address=131072,name='Outer')
        target=N(index=3,serial=1,address=196608,class_name='MovieSceneSpawnSection',name='SpawnSection')
        original=N(index=4,serial=1,address=262144,class_name=target.class_name,name=target.name)
        path='/Game/Movie.Movie:MovieScene.SpawnSection'
        guid=dict(struct='/Script/CoreUObject.Guid',complete=True,errors={},fields=dict(A=1,B=2,C=3,D=4))
        document=dict(source=dict(sequence='/Game/Movie.Movie',nodes={path:dict(fields=dict(Signature=guid,bIsActive=True))}))
        record=dict(state='fresh',outer=(2,1,131072),source=document['source']['sequence'])
        planner=Mock();scope=N(pid=42,_check=Mock(),_session=N(_transport=N(_executable='probe')),
            _authored_copy_states={(1,1,65536):record},invocation_planner=Mock(return_value=planner))
        catalog=Mock();catalog.with_observations.return_value=catalog;catalog.objects=(target,original)
        catalog.outer_chain.side_effect=lambda o:(root,outer) if o is target else (outer,) if o is root else ()
        catalog.find_path.side_effect=lambda p:original if p==path else p
        active={3:True,4:True}
        def read(c,o,fields):return N(errors={},truncated=(),values={(o.index,'Signature'):guid,(o.index,'bIsActive'):active[o.index]}),catalog
        def invoke():active[3]=False;return nullcontext()
        planner.prepare.return_value.invoke.side_effect=invoke
        return N(args=(scope,root,outer,document,(path,)),record=record,planner=planner,catalog=catalog,read=read,active=active,target=target)
    def run_fixture(self,f,reachable=(3,)):
        p='expedition33.cinematics.authored_activity.'
        with patch(p+'shared_operation',return_value=nullcontext()),patch(p+'capture_matching',return_value=f.catalog),\
             patch(p+'capture_selected'),patch(p+'read_values_with_references',side_effect=f.read),\
             patch(p+'copied',side_effect=lambda v,c:v),\
             patch('expedition33.cinematics.authored_references.reachable_sections',return_value=set(reachable)):
            disable_sections(*f.args)
    def test_exact_private_dispatch_and_unchanged_original(self):
        f=self.fixture();self.run_fixture(f)
        f.planner.prepare.assert_called_once_with(f.target,'/Script/MovieScene.MovieSceneSection:SetIsActive',bInIsActive=False)
        self.assertEqual(f.active,{3:False,4:True});self.assertEqual(f.record['state'],'ready')
    def test_unreachable_or_changed_original_rejects_before_dispatch(self):
        for changed in (False,True):
            f=self.fixture()
            if changed:f.active[4]=False
            with self.assertRaises(RuntimeError):self.run_fixture(f,(3,) if changed else ())
            f.planner.prepare.assert_not_called()
    def test_unknown_dispatch_poisoned_without_replay(self):
        f=self.fixture();f.planner.prepare.return_value.invoke.side_effect=RuntimeError('uncertain')
        with self.assertRaises(RuntimeError):self.run_fixture(f)
        self.assertEqual(f.record['state'],'rejected')
        with self.assertRaises(RuntimeError):self.run_fixture(f)
        self.assertEqual(f.planner.prepare.call_count,1)
    def test_missing_readback_or_mutated_source_poisoned(self):
        for source_changed in (False,True):
            f=self.fixture()
            def invoke():
                if source_changed:f.active.update({3:False,4:False})
                return nullcontext()
            f.planner.prepare.return_value.invoke.side_effect=invoke
            with self.assertRaises(RuntimeError):self.run_fixture(f)
            self.assertEqual(f.record['state'],'rejected')
