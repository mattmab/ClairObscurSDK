"""Fresh campaign gates preserve Map_Find semantics and current-save provenance."""
from dataclasses import replace
from types import SimpleNamespace as N
from unittest import TestCase
from unittest.mock import Mock,patch

from expedition33.catalog import Catalog,CatalogObject,ClassRelation
from expedition33.story_conditions import StoryConditions
from expedition33.values import StoredMap,StoredValues


class PersistentFlagTests(TestCase):
    def setUp(self):
        kinds=('Object','Class','GameEngine','GameViewportClient','World',
               'BP_jRPG_GI_Custom_C','BP_SaveManager_C','NamedID')
        classes=[ClassRelation(i,1,name,-1 if i==0 else 0,4096) for i,name in enumerate(kinds)]
        def obj(i,name,cls):
            return CatalogObject(123,i,1,0x10000+i*256,name,kinds[cls],'Class',cls,-1,0,0,0)
        objects=[obj(i,kind,1) for i,kind in enumerate(kinds)]
        objects.extend(obj(i,name,cls) for i,name,cls in (
            (8,'Engine',2),(9,'Viewport',3),(10,'WorldNow',4),(11,'CurrentGI',5),
            (12,'SaveManager',6),(13,'FlagA',7),(14,'FlagB',7)))
        self.catalog=Catalog(123,objects,classes)
        self.engine,self.viewport,self.world,self.gi,self.manager,self.a,self.b=objects[8:]
        self.paths=('/Game/Flags/FlagA.FlagA','/Game/Flags/FlagB.FlagB')
        self.load=Mock(side_effect=dict(zip(self.paths,(self.a,self.b))).__getitem__)
        prepared=N(engine=self.engine,viewport=self.viewport,resources=N(gi=self.gi,load=self.load))
        self.token=tuple((123,*self.ident(o)) for o in (self.world,self.gi,self.manager))+(9,)
        self.scope=N(pid=123,_world_binding_token=self.token,_check=Mock(),close=Mock(),
                     _session=N(_story_construction_resources=prepared),
                     invocation_planner=Mock(side_effect=AssertionError('Read must not dispatch Blueprint')))
        self.owner=object.__new__(StoryConditions)
        self.owner.scope=self.scope;self.owner.visit=None;self.owner.flags={}
        self.ctx={'visit':self.ident(self.world)}
        self.rows={o.index:StoredValues(o,{}, {},{}) for o in objects[8:]}
        for obj,name,kind,value in (
                (self.engine,'GameViewport','ObjectProperty',self.viewport),
                (self.viewport,'World','ObjectProperty',self.world),
                (self.world,'OwningGameInstance','ObjectProperty',self.gi),
                (self.gi,'SaveManager','ObjectProperty',self.manager),
                (self.manager,'GameInstanceReference','ObjectProperty',self.gi),
                (self.gi,'SaveLoaded','BoolProperty',True),
                (self.manager,'LoadIsInProgress','BoolProperty',False),
                (self.manager,'SelectedSlot','IntProperty',9)):
            self.field(obj,name,kind,value)
        self.states({self.a:True,self.b:False})
    @staticmethod
    def ident(obj):return obj.index,obj.serial,obj.address
    def field(self,obj,name,kind,value):
        row=self.rows[obj.index];key=(obj.class_index,name)
        row.values[key]=value;row.types[key]=kind
    def states(self,items):self.field(self.gi,'NamedIDsStates','MapProperty',StoredMap(items,'ObjectProperty','BoolProperty',self.catalog.by_index[7]))
    def read(self,paths=None):
        with (patch('expedition33.story_conditions.capture_selected_values',return_value=(self.catalog,self.rows)) as query,
                patch('expedition33.story_conditions.capture_matching',side_effect=AssertionError('No global scan'))):
            result=self.owner.persistent_flags(paths or self.paths,self.ctx)
        query.assert_called_once()
        self.assertTrue(query.call_args.kwargs['references'])
        self.assertEqual(query.call_args.args[1][:5],tuple(self.ident(o) for o in
            (self.engine,self.viewport,self.world,self.gi,self.manager)))
        return result
    def test_complete_true_false_and_absent_preserve_getter_semantics(self):
        self.assertEqual(self.read(),dict(zip(self.paths,(True,False))))
        self.states({self.b:True})
        self.assertEqual(self.read(),dict(zip(self.paths,(False,True))))
        self.assertEqual(self.load.call_count,2) # Retained selectors, fresh values.
        self.scope.invocation_planner.assert_not_called()
    def test_one_flag_facade_does_not_cache_result(self):
        with patch('expedition33.story_conditions.capture_selected_values',return_value=(self.catalog,self.rows)) as query:
            self.assertTrue(self.owner.persistent_flag(self.paths[0],self.ctx))
            self.states({self.a:False})
            self.assertFalse(self.owner.persistent_flag(self.paths[0],self.ctx))
        self.assertEqual(query.call_count,2)
    def test_incomplete_map_never_returns_false(self):
        row=self.rows[self.gi.index];key=(self.gi.class_index,'NamedIDsStates')
        for mode in ('error','truncated','absent','wrong_kind','untyped_empty','wrong_map','nonbool','wrong_owner'):
            values=dict(row.values);types=dict(row.types);errors={};truncated=frozenset()
            if mode=='error':errors[key]='MAP_OBSERVATION_CHANGED'
            elif mode=='truncated':truncated=frozenset((key,))
            elif mode=='absent':values.pop(key)
            elif mode=='wrong_kind':types[key]='ArrayProperty'
            elif mode=='untyped_empty':values[key]=StoredMap({})
            elif mode=='wrong_map':values[key]=StoredMap({},'NameProperty','BoolProperty')
            elif mode=='nonbool':values[key]=StoredMap({self.a:1},'ObjectProperty','BoolProperty',self.catalog.by_index[7])
            else:
                value=values.pop(key);types.pop(key)
                values[2,'NamedIDsStates']=value;types[2,'NamedIDsStates']='MapProperty'
            self.rows[self.gi.index]=StoredValues(self.gi,values,errors,types,truncated)
            with self.subTest(mode=mode),self.assertRaises(RuntimeError):self.read()
        self.rows[self.gi.index]=row
    def test_current_world_chain_is_required_even_when_old_world_still_exists(self):
        for obj,name in ((self.engine,'GameViewport'),(self.viewport,'World'),
                         (self.world,'OwningGameInstance'),(self.gi,'SaveManager'),
                         (self.manager,'GameInstanceReference')):
            key=(obj.class_index,name);old=self.rows[obj.index].values[key]
            self.rows[obj.index].values[key]=None
            with self.subTest(field=name),self.assertRaisesRegex(RuntimeError,'live binding'):self.read()
            self.rows[obj.index].values[key]=old
    def test_loading_changed_slot_and_invalid_save_types_are_rejected(self):
        for obj,name,values in ((self.gi,'SaveLoaded',(False,1)),
                               (self.manager,'LoadIsInProgress',(True,0)),
                               (self.manager,'SelectedSlot',(8,True,-1))):
            key=(obj.class_index,name);old=self.rows[obj.index].values[key]
            for value in values:
                self.rows[obj.index].values[key]=value
                with self.subTest(field=name,value=value),self.assertRaisesRegex(RuntimeError,'selected save'):self.read()
            self.rows[obj.index].values[key]=old
    def test_stale_scope_or_world_does_not_load_assets_or_query(self):
        for mode in ('closed','different_world','different_gi'):
            self.scope._check.side_effect=RuntimeError('Closed') if mode=='closed' else None
            self.ctx={'visit':self.ident(self.world)}
            self.scope._world_binding_token=self.token
            if mode=='different_world':self.ctx['visit']=(10,2,self.world.address)
            if mode=='different_gi':self.scope._world_binding_token=(self.token[0],(123,11,99,self.gi.address),*self.token[2:])
            with self.subTest(mode=mode),patch('expedition33.story_conditions.capture_selected_values') as query,self.assertRaises(RuntimeError):
                self.owner.persistent_flags(self.paths,self.ctx)
            query.assert_not_called()
        self.load.assert_not_called()
    def test_recycled_requested_asset_rejected_without_retry(self):
        self.read()
        self.catalog=Catalog(123,[replace(o,serial=7) if o.index==self.a.index else o for o in self.catalog.objects],tuple(self.catalog.classes.values()))
        with self.assertRaisesRegex(RuntimeError,'identity changed'):self.read()
    def test_wrong_requested_asset_class_never_becomes_absent_false(self):
        self.load.side_effect=lambda path:self.engine
        self.states({})
        with self.assertRaisesRegex(RuntimeError,'reflected NamedID class'):self.read()
    def test_close_releases_only_its_scope(self):
        self.read();self.assertTrue(self.owner.close())
        self.assertFalse(self.owner.flags);self.scope.close.assert_called_once()
