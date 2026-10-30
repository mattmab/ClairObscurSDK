"""Original battle source/arena preflight; no engine dispatch occurs."""
from contextlib import ExitStack
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

from expedition33 import simon_original as simon,simon_source as source
from expedition33.catalog import Catalog,CatalogObject,ClassRelation
from expedition33.values import StoredValues,StoredStruct,StoredArray,StoredSoftObjectPath
from expedition33.enemy_spawning import load_catalog
from expedition33._original_trigger_fight import _recipes
from test_simon_source import fixture


class SimonBattleDependencyTests(unittest.TestCase):
    def setUp(self):
        initial,root,observed,_ = fixture()
        self.graph = source.validate_graph(initial,root,observed)
        self.recipes = {row['id']:row for row in _recipes(load_catalog())}
        self.profile = self.recipes['simon-normal']['arena']
        objects,classes = list(initial.objects),list(initial.classes.values())
        def add(name,cls,outer=None):
            descriptor = next(row for row in classes if row.index == cls)
            obj = CatalogObject(123,len(objects),1,0x10000+len(objects)*256,name,
                descriptor.name,'Class',cls,-1 if outer is None else outer.index,
                0 if outer is None else outer.serial,0,0)
            objects.append(obj);return obj
        def package(name):
            matches = [obj for obj in objects if obj.class_name == 'Package' and obj.name == name]
            return matches[0] if matches else add(name,2)
        def add_class(name,pkg):
            parent = package(pkg)
            index = len(objects)
            classes.append(ClassRelation(index,1,name,0,256))
            objects.append(CatalogObject(123,index,1,0x10000+index*256,name,'Class','Class',
                1,parent.index,parent.serial,0,0))
            return index
        self.world = add('SmallLevel_SimonArea',4,package(source.WORLD.split('.')[0]))
        level = add('PersistentLevel',0,self.world)
        arena_class = add_class('BP_BattleMap_C','/Game/Levels/Battle_Maps/BP_BattleMap')
        self.arena = add(self.profile['source_actor'].rsplit('.',1)[-1],arena_class,level)
        component_class = add_class('SceneComponent','/Script/Engine')
        self.component = add('DefaultSceneRoot',component_class,self.arena)
        self.controller = add('Controller',0,level)
        self.manager = add('BattleManager',0,self.controller)
        self.catalog = Catalog(123,objects,classes)
        self.context = dict(world=(123,self.world.index,1,self.world.address),
            controller=(123,self.controller.index,1,self.controller.address),world_path=source.WORLD)
        pkg,remainder = self.profile['source_actor'].split('.',1)
        asset,subpath = remainder.split(':',1)
        self.parameters = StoredStruct(None,dict(BattleMapBP_x=None,
            BattleMapBPSoft_x=StoredSoftObjectPath(pkg,asset,subpath)),{},
            dict(BattleMapBP_x='ObjectProperty',BattleMapBPSoft_x='SoftObjectProperty'),False)
        self.frame = self.profile['frames']['DefaultSceneRoot']
        self.pose_values = dict(RelativeLocation=self.frame['location'],
            RelativeRotation=self.frame['rotation'],RelativeScale3D=self.frame['scale'])
        self.busy = False
        self.missing = False
        self.verify = Mock()

    def read(self,catalog,obj,*,fields):
        types = {}
        values = {}
        for name in fields:
            if name == 'Battle Start Params': value,kind = self.parameters,'StructProperty'
            elif name == 'RootComponent': value,kind = self.component,'ObjectProperty'
            elif name in self.pose_values:
                value,kind = StoredStruct(None,self.pose_values[name],{},{},False),'StructProperty'
            elif name == 'AttachParent': value,kind = None,'ObjectProperty'
            elif name in ('Enemies','PlayerCharacters'): value,kind = StoredArray((),0),'ArrayProperty'
            elif name == 'BattleMapBP': value,kind = None,'ObjectProperty'
            elif name in ('IsBattleInitialized','HasBattleStartedEndFlow'): value,kind = self.busy,'BoolProperty'
            else: raise AssertionError(name)
            key = (obj.class_index,name)
            types[key],values[key] = kind,value
        return StoredValues(obj,values,{},types),self.catalog

    def run_preflight(self):
        with ExitStack() as stack:
            stack.enter_context(patch('expedition33.simon_original.read_values_with_references',side_effect=self.read))
            matched = stack.enter_context(patch('expedition33.simon_original.capture_matching',return_value=self.catalog))
            stack.enter_context(patch('expedition33.simon_original.capture_selected',return_value=self.catalog))
            stack.enter_context(patch('expedition33.original_encounter_roster._verify_source',self.verify))
            stack.enter_context(patch('expedition33._npc_encounter_preparation._controller_battle_manager',
                                      return_value=(self.manager,self.catalog)))
            result = simon._battle_dependencies(SimpleNamespace(pid=123),self.catalog,self.graph,self.context)
            self.assertTrue(all(call.kwargs == dict(names=(self.arena.name,)) for call in matched.call_args_list))
            return result

    def test_both_exact_sources_share_loaded_original_arena(self):
        self.assertIs(self.run_preflight(),self.catalog)
        self.assertEqual([call.args[2] for call in self.verify.call_args_list],
                         ['Boss_Simon*1','Boss_SimonPhase2*1'])
        self.assertEqual([call.args[1] for call in self.verify.call_args_list],
                         [self.graph.actions[1],self.graph.actions[3]])

    def test_wrong_soft_reference_fails_before_arena_use(self):
        self.parameters = replace(self.parameters,fields=dict(self.parameters.fields,
            BattleMapBPSoft_x=StoredSoftObjectPath('/Game/Other','Other','')))
        with self.assertRaisesRegex(RuntimeError,'soft arena source'):
            self.run_preflight()

    def test_foreign_hard_reference_rejected(self):
        self.parameters = replace(self.parameters,fields=dict(self.parameters.fields,BattleMapBP_x=self.controller))
        with self.assertRaisesRegex(RuntimeError,'hard arena reference'):
            self.run_preflight()

    def test_distant_arena_missing_does_not_fall_back_to_map_name(self):
        objects = [replace(obj,name='DifferentArena') if obj.index == self.arena.index else obj
                   for obj in self.catalog.objects]
        self.catalog = Catalog(123,objects,tuple(self.catalog.classes.values()))
        with self.assertRaisesRegex(RuntimeError,'Expected one object'):
            self.run_preflight()

    def test_original_frame_required_without_relocation(self):
        self.pose_values['RelativeLocation'] = dict(self.frame['location'],Z=0)
        with self.assertRaisesRegex(RuntimeError,'arena frame differs'):
            self.run_preflight()

    def test_current_world_token_and_idle_manager_required(self):
        original = dict(self.context)
        self.context['world'] = (123,self.world.index,99,self.world.address)
        with self.assertRaisesRegex(RuntimeError,'world identity'):
            self.run_preflight()
        self.context = original
        self.busy = True
        with self.assertRaisesRegex(RuntimeError,'battle manager is busy'):
            self.run_preflight()
