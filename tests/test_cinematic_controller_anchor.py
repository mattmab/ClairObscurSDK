import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.controller_anchor import ControllerAnchor,for_scope,context_observer
from expedition33.cinematics.original_game_action import NotReady


class ControllerAnchorTests(unittest.TestCase):
    def test_context_observer_requires_strict_capability_and_never_caches_values(self):
        scope=N(_session=N(_transport=N(stable_lease_protocol=1)))
        observe=Mock(side_effect=({'world':1},{'world':2}))
        with patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)) as anchor:
            reader=context_observer(scope)
            self.assertNotEqual(reader(),reader());anchor.assert_called_once_with(scope)
        for cap in (0,True,'1'):
            scope._session._transport.stable_lease_protocol=cap
            with patch('expedition33.cinematics.controller_anchor.for_scope') as anchor,\
                 patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world':3}) as scan:
                reader=context_observer(scope);reader();reader()
                anchor.assert_not_called();self.assertEqual(scan.call_count,2)
    def fixture(self):
        scope=N(pid=123,_check=Mock())
        local=N(index=1,serial=2,address=256,class_name='LocalPlayer',object_flags=0)
        player=N(index=3,serial=4,address=512,class_index=10,object_flags=0)
        world=N(index=5,serial=6,address=768,class_name='World')
        catalog=N(objects=(local,),by_index={1:local},classes={10:N(name='PlayerController')},
                  ancestors=lambda i:(10,),outer_chain=lambda p:(world,),path_name=lambda w:'/Game/QA.Map')
        value=N(types={(8,'PlayerController'):'ObjectProperty'},values={(8,'PlayerController'):player},errors={},truncated=False)
        return scope,local,player,world,catalog,value
    def test_selector_is_retained_once_but_current_controller_is_read_every_time(self):
        scope,local,player,world,catalog,value=self.fixture();held=N(object=local,active=True)
        with patch('expedition33.cinematics.controller_anchor.capture_matching',return_value=catalog) as capture,\
             patch('expedition33._stable_lease.acquire_stable',return_value=(held,catalog)) as acquire,\
             patch('expedition33.cinematics.controller_anchor.capture_selected_values',return_value=(catalog,{1:value})) as read:
            anchor=for_scope(scope);first=anchor.context();self.assertIs(for_scope(scope),anchor)
            value.values[(8,'PlayerController')]=N(index=9,serial=10,address=1024,class_index=10,object_flags=0)
            second=anchor.context()
        capture.assert_called_once();acquire.assert_called_once_with(scope,local);self.assertEqual(read.call_count,2)
        self.assertNotEqual(first['controller'],second['controller']);self.assertEqual(first['controller'],(123,3,4,512))
        self.assertEqual(second['controller'],(123,9,10,1024))
    def test_incomplete_and_wrong_type_projections_do_not_grant_context(self):
        scope,local,player,world,catalog,value=self.fixture();anchor=ControllerAnchor.__new__(ControllerAnchor)
        anchor.scope=scope;anchor.identity=(1,2,256);anchor._held=N(active=True)
        with patch('expedition33.cinematics.controller_anchor.capture_selected_values',return_value=(catalog,{1:value})):
            value.errors={'PlayerController':'unavailable'}
            with self.assertRaises(NotReady):anchor.context()
            value.errors={};value.values[(8,'PlayerController')]=None
            with self.assertRaises(NotReady):anchor.context()
            value.types[(8,'PlayerController')]='WeakObjectProperty'
            with self.assertRaises(RuntimeError):anchor.context()
        anchor._held.active=False
        with patch('expedition33.cinematics.controller_anchor.capture_selected_values') as read,self.assertRaisesRegex(RuntimeError,'inactive'):
            anchor.context()
        read.assert_not_called()
    def test_ambiguous_local_players_and_foreign_cached_anchors_rejected(self):
        scope,local,player,world,catalog,value=self.fixture();catalog.objects=(local,local)
        with patch('expedition33.cinematics.controller_anchor.capture_matching',return_value=catalog),\
             patch('expedition33._stable_lease.acquire_stable') as acquire,self.assertRaises(NotReady):ControllerAnchor(scope)
        acquire.assert_not_called()
        scope._cinematic_controller_anchor=N(scope=scope)
        with self.assertRaises(ValueError):for_scope(scope)
