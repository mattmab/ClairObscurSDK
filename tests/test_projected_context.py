import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/cinematics'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
h=load('projected_context_history',SOURCE/'history.py')
c=load('projected_context_original',SOURCE/'original_game_action.py')


class ProjectedContextTests(unittest.TestCase):
    def test_anchor_default_preserves_calls_and_projection_is_explicit(self):
        engine=N(object_flags=0,pid=7,index=1,serial=2,address=3)
        viewport=N(pid=7,index=2,serial=2,address=4)
        world=N(pid=7,index=3,serial=2,address=5)
        gi=N(pid=7,index=4,serial=2,address=6,class_name='BP_jRPG_GI_Custom_C',object_flags=0)
        owner=object()
        catalog=Mock(by_index={9:owner})
        catalog.select.return_value=(engine,)
        catalog.find_class.return_value=N(index=9)
        for projected in (False,True):
            with self.subTest(projected=projected), patch.object(h,'read_object_reference',
                    side_effect=((viewport,catalog),(world,catalog),(gi,catalog))) as read:
                result,_=h.anchor(catalog,project=projected)
                self.assertEqual(tuple(map(h.identity,result)),((7,1,2,3),(7,2,2,4),(7,3,2,5),(7,4,2,6)))
                for call in read.call_args_list:
                    self.assertEqual(call.kwargs,{'project':True} if projected else {})

    def controller(self,project):
        local=N(index=1,class_name='LocalPlayer',object_flags=0)
        player=N(pid=7,index=2,serial=3,address=4)
        world=N(pid=7,index=5,serial=6,address=7,class_name='World')
        owner=object()
        catalog=Mock(objects=(local,),by_index={9:owner})
        catalog.outer_chain.return_value=(world,)
        catalog.path_name.return_value='/World'
        observed=N(types={(9,'PlayerController'):'ObjectProperty'})
        with patch.object(c,'capture_matching',return_value=catalog), \
             patch.object(c,'read_values',return_value=observed) as full, \
             patch.object(c,'read_values_many',return_value={1:observed}) as selected, \
             patch.object(c,'read_object_reference',return_value=(player,catalog)) as reference:
            result=c.controller_context(N(pid=7),project=project)
            if project:
                full.assert_not_called()
                selected.assert_called_once_with(catalog,(local,),fields=('PlayerController',))
                reference.assert_called_once_with(catalog,local,owner,'PlayerController',project=True)
            else:
                full.assert_called_once_with(catalog,local)
                selected.assert_not_called()
                reference.assert_called_once_with(catalog,local,owner,'PlayerController')
            return result

    def test_controller_projection_preserves_exact_identity_default_unchanged(self):
        self.assertEqual(self.controller(False),self.controller(True))

    def test_projection_does_not_hide_incomplete_reference(self):
        local=N(index=1,class_name='LocalPlayer',object_flags=0)
        catalog=N(objects=(local,),by_index={9:object()})
        with patch.object(c,'capture_matching',return_value=catalog), \
             patch.object(c,'read_values_many',return_value={1:N(types={(9,'PlayerController'):'ObjectProperty'})}), \
             patch.object(c,'read_object_reference',side_effect=RuntimeQueryError('Expected one readable scalar object property')):
            with self.assertRaises(RuntimeQueryError):c.controller_context(N(pid=7),project=True)

    def test_anchor_projection_does_not_hide_decoder_failure(self):
        catalog=Mock(by_index={9:object()})
        catalog.select.return_value=(N(object_flags=0),)
        catalog.find_class.return_value=N(index=9)
        with patch.object(h,'read_object_reference',side_effect=RuntimeQueryError('incomplete field')):
            with self.assertRaises(RuntimeQueryError):h.anchor(catalog,project=True)

    def test_controller_projection_keeps_identity_race_not_ready(self):
        with patch.object(c,'_controller_context_once',side_effect=RuntimeQueryError(
                'Object identity changed or belongs to another process')) as read:
            with self.assertRaises(c.NotReady):c.controller_context(N(pid=7),project=True)
            self.assertEqual(read.call_count,1)


if __name__=='__main__':unittest.main()
