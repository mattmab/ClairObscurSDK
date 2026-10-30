import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.authored_relink import relink


class AuthoredRelinkTests(unittest.TestCase):
    def fixture(self):
        def obj(index,cls):return N(index=index,serial=1,address=index*65536,class_name=cls)
        parent,section,child,replacement,outer,source,original=(obj(i,c) for i,c in enumerate(
            ('LevelSequence','MovieSceneCinematicShotSection','LevelSequence','LevelSequence',
             'Object','LevelSequence','MovieSceneCinematicShotSection'),1))
        key=lambda o:(o.index,o.serial,o.address)
        journal={key(parent):dict(state='fresh',source='source',outer=key(outer)),
                 key(replacement):dict(state='fresh',source='child',outer=key(outer))}
        catalog=Mock();catalog.with_observations.return_value=catalog;catalog.resolve.side_effect=lambda o:o
        chains={parent.index:(outer,),replacement.index:(outer,),section.index:(parent,outer),original.index:(source,)}
        catalog.outer_chain.side_effect=lambda o:chains.get(o.index,())
        catalog.path_name.side_effect=lambda o:'source' if o is source else 'child'
        catalog.find_path.side_effect=lambda p:p
        planner=Mock();scope=N(pid=42,_check=Mock(),_authored_copy_states=journal,
            _session=N(_transport=N(_executable='probe')),invocation_planner=Mock(return_value=planner))
        current={'private':child,'original':child}
        guid={'struct':'/Script/CoreUObject.Guid','complete':True,'errors':{},'fields':dict(A=1,B=2,C=3,D=4)}
        def links(scope,root,*,recursive=True):
            if root is parent:return [(parent,section,current['private'])]
            if root is source:return [(source,original,current['original'])]
            return []
        def read(c,o,fields):
            rows={'Signature':guid,'SubSequence':current['private' if o is section else 'original']}
            return N(errors={},truncated=(),values={(o.index,k):v for k,v in rows.items()}),catalog
        def invoke():current['private']=replacement;return nullcontext()
        planner.prepare.return_value.invoke.side_effect=invoke
        return N(args=(scope,parent,section,child,replacement,outer,source,original),scope=scope,
            parent=parent,replacement=replacement,key=key,journal=journal,catalog=catalog,
            planner=planner,current=current,links=links,read=read)

    def run_fixture(self,f):
        prefix='expedition33.cinematics.authored_relink.'
        with patch(prefix+'shared_operation',return_value=nullcontext()),\
             patch(prefix+'capture_matching',return_value=f.catalog),\
             patch(prefix+'capture_selected'),patch(prefix+'sequence_links',side_effect=f.links),\
             patch(prefix+'read_values_with_references',side_effect=f.read),\
             patch(prefix+'copied',side_effect=lambda v,c:v):
            relink(*f.args)

    def test_private_subsection_dispatch_and_source_readback(self):
        f=self.fixture();self.run_fixture(f)
        self.assertIs(f.current['private'],f.replacement)
        self.assertIs(f.current['original'],f.args[3])
        f.planner.prepare.assert_called_once_with(f.args[2],
            '/Script/MovieScene.MovieSceneSubSection:SetSequence',Sequence=f.replacement)
        self.assertEqual(f.journal[f.key(f.parent)]['state'],'fresh')

    def test_foreign_or_sealed_copy_rejects_before_dispatch(self):
        for mutation in ('sealed','outer'):
            f=self.fixture();record=f.journal[f.key(f.replacement)]
            if mutation=='sealed':record['state']='sealed'
            else:record['outer']=(99,1,1)
            with self.assertRaises(RuntimeError):self.run_fixture(f)
            f.planner.prepare.assert_not_called()

    def test_unknown_dispatch_is_poisoned_and_not_replayed(self):
        f=self.fixture();f.planner.prepare.return_value.invoke.side_effect=RuntimeError('unknown completion')
        with self.assertRaisesRegex(RuntimeError,'unknown completion'):self.run_fixture(f)
        self.assertEqual(f.journal[f.key(f.parent)]['state'],'rejected')
        with self.assertRaises(RuntimeError):self.run_fixture(f)
        self.assertEqual(f.planner.prepare.call_count,1)

    def test_missing_readback_and_source_change_are_rejected(self):
        for change in ('none','source'):
            f=self.fixture()
            def invoke():
                if change=='source':
                    f.current['private']=f.replacement;f.current['original']=f.replacement
                return nullcontext()
            f.planner.prepare.return_value.invoke.side_effect=invoke
            with self.assertRaises(RuntimeError):self.run_fixture(f)
            self.assertEqual(f.journal[f.key(f.parent)]['state'],'rejected')
