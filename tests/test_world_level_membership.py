from dataclasses import FrozenInstanceError
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest

from expedition33 import _world_level_membership as m
from expedition33.values import StoredArray,StoredValues


class WorldLevelMembershipTests(unittest.TestCase):
    def setUp(self):
        def obj(index,cls,outer=-1):
            return N(pid=123,index=index,serial=1,address=0x10000+index*256,name=cls,
                class_name=cls,class_index=index+10,outer_index=outer,outer_serial=1,object_flags=0,item_flags=0)
        self.actor=obj(1,'CineActor',2);self.level=obj(2,'Level',4)
        self.world=obj(3,'World');self.generated_world=obj(4,'World')
        objects={o.index:o for o in (self.actor,self.level,self.world,self.generated_world)}
        objects[11]=N(name='/Script/Engine.Actor');objects[12]=N(name='/Script/Engine.Level')
        self.catalog=N(by_index=objects,resolve=lambda obj:objects[obj.index],
            ancestors=lambda cls:(cls,),path_name=lambda obj:obj.name)
        self.context=dict(controller=(123,5,1,0x20000),world=m.identity(self.world),world_path='/Game/Current.World')
        self.scope=N(pid=123,_check=Mock(),_session=N(_transport=N(_executable='candidate-reader')))
        self.owner=self.world;self.visible=True;self.levels=StoredArray((self.level,),1)
        self.enterContext(patch.object(m,'ReadBatch'))
        self.active=self.enterContext(patch.object(m,'active_reader',return_value=None))
        self.context_read=self.enterContext(patch.object(m,'controller_context',return_value=self.context))
        self.capture=self.enterContext(patch.object(m,'capture_selected',return_value=self.catalog))
        self.read=self.enterContext(patch.object(m,'read_values_with_references',side_effect=self.values))

    def values(self,catalog,obj,*,fields):
        data={'OwningWorld':self.owner,'bIsVisible':self.visible,'Levels':self.levels}
        types={'OwningWorld':'ObjectProperty','bIsVisible':'BoolProperty','Levels':'ArrayProperty'}
        return StoredValues(obj,{(obj.index,n):data[n] for n in fields},{},
                            {(obj.index,n):types[n] for n in fields}),catalog

    def observe(self):
        return m.observe_actor_membership(self.scope,self.actor,expected_context=self.context)

    def test_generated_outer_world_admitted_only_by_reciprocal_live_membership(self):
        result=self.observe()
        self.assertEqual(result.world,m.identity(self.world))
        self.assertEqual(result.level,m.identity(self.level))
        self.assertNotEqual(self.level.outer_index,self.world.index)
        self.assertEqual(self.capture.call_count,2)
        self.assertEqual(self.context_read.call_count,2)
        with self.assertRaises(FrozenInstanceError):result.level_visible=False

    def test_loaded_source_world_alone_does_not_admit(self):
        self.owner=self.generated_world
        with self.assertRaisesRegex(RuntimeError,'current owning World'):self.observe()
        self.owner=self.world;self.levels=StoredArray((self.world,),1)
        with self.assertRaisesRegex(RuntimeError,'World.Levels'):self.observe()

    def test_hidden_level_and_nonboolean_visibility_reject(self):
        for visible in (False,None,1):
            self.visible=visible
            with self.assertRaises(RuntimeError):self.observe()

    def test_incomplete_null_duplicate_and_overbudget_level_arrays_reject(self):
        for levels in (StoredArray((),1),StoredArray((None,),1),StoredArray((self.level,self.level),2),
                       StoredArray(tuple(self.level for _ in range(257)),257)):
            self.levels=levels
            with self.assertRaises(RuntimeError):self.observe()

    def test_context_replacement_before_and_during_observation_reject(self):
        changed=dict(self.context,controller=(123,55,1,0x90000))
        self.context_read.return_value=changed
        with self.assertRaisesRegex(RuntimeError,'before observation'):self.observe()
        self.capture.assert_not_called()
        self.context_read.side_effect=[self.context,changed]
        with self.assertRaisesRegex(RuntimeError,'during observation'):self.observe()

    def test_level_membership_change_during_read_rejects(self):
        original=self.values;count=0
        def changing(catalog,obj,*,fields):
            nonlocal count
            if fields==('Levels',):
                count+=1
                if count==2:self.levels=StoredArray((),0)
            return original(catalog,obj,fields=fields)
        self.read.side_effect=changing
        with self.assertRaises(RuntimeError):self.observe()

    def test_source_templates_retiring_objects_and_nonactor_reject(self):
        self.actor.object_flags=0x10
        with self.assertRaisesRegex(RuntimeError,'template'):self.observe()
        self.actor.object_flags=0;self.actor.item_flags=0x200000
        with self.assertRaisesRegex(RuntimeError,'retiring'):self.observe()
        self.actor.item_flags=0;self.catalog.ancestors=lambda cls:()
        with self.assertRaisesRegex(RuntimeError,'not an actor'):self.observe()

    def test_closed_scope_and_foreign_process_prevent_reads(self):
        self.scope._check.side_effect=RuntimeError('closed')
        with self.assertRaisesRegex(RuntimeError,'closed'):self.observe()
        self.capture.assert_not_called()
        self.scope._check.side_effect=None;self.actor.pid=999
        with self.assertRaises(ValueError):self.observe()

    def test_nested_read_operation_borrows_without_new_shared_owner(self):
        self.active.return_value=object()
        self.observe()
        m.ReadBatch.assert_called_once_with(123,share=False,_executable='candidate-reader')
