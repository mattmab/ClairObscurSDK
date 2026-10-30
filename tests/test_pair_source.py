from dataclasses import replace
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError, pair_source as source
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.values import StoredArray, StoredStruct, StoredValues


def fixture():
    names = ['Object','Class','Package','ScriptStruct','World','Level',
             'BP_GameAction_Sequential_C','BP_GameAction_TriggerBattle_C',
             'BP_GameAction_WritePersistentFlag_C','BP_BattleMap_DuollistAlpha_C','NamedID']
    classes = [ClassRelation(i,1,name,-1 if i == 0 else 0,256) for i,name in enumerate(names)]
    objects = [CatalogObject(123,i,1,0x10000+i*256,name,'Class','Class',1,-1,0,0,0)
               for i,name in enumerate(names)]
    def add(name,cls,outer=None):
        obj = CatalogObject(123,len(objects),1,0x10000+len(objects)*256,name,names[cls],
                            'Class',cls,-1 if outer is None else outer.index,0 if outer is None else 1,0,0)
        objects.append(obj);return obj
    packages = {}
    def package(path):
        if path not in packages:packages[path] = add(path,2)
        return packages[path]
    for cls,pkg in source._CLASS_PACKAGES.items():
        index = names.index(cls)
        objects[index] = replace(objects[index],outer_index=package(pkg).index,outer_serial=1)
    objects[9] = replace(objects[9],outer_index=package(source.ARENA_CLASS.split('.')[0]).index,outer_serial=1)
    root = add('DA_GA_SQT_DuallisteAlpha',6,package(source.PACKAGE))
    actions = [add(stage.path.split(':')[1],names.index(stage.class_name),root) for stage in source.STAGES]
    wrapper = add('GameAction_Wrapper',3,package('/Script/SandFall'))
    wrappers = tuple(StoredStruct(wrapper,dict(GameActionReference=None,GameActionInline=action),{},
                                 dict(GameActionReference='ObjectProperty',GameActionInline='ObjectProperty'),False)
                     for action in actions)
    key = (root.class_index,'GameActionsToExecute')
    observed = StoredValues(root,{key:StoredArray(wrappers,2)},{},{key:'ArrayProperty'})
    flag_pkg,flag_name = source.FLAG.split('.')
    flag = add(flag_name,10,package(flag_pkg))
    fkey,vkey = (actions[1].class_index,'NamedID'),(actions[1].class_index,'Value')
    tail = StoredValues(actions[1],{fkey:flag,vkey:True},{},{fkey:'ObjectProperty',vkey:'BoolProperty'})
    pkg,world_name = source.WORLD.split('.')
    world = add(world_name,4,package(pkg));level = add('PersistentLevel',5,world)
    arena = add(source.ARENA.split(':PersistentLevel.')[1],9,level)
    catalog = Catalog(123,objects,classes)
    context = dict(world=(world.pid,world.index,world.serial,world.address),world_path=source.WORLD)
    return catalog,root,observed,key,tail,world,arena,context


class PairSourceTests(unittest.TestCase):
    def setUp(self):
        self.c,self.root,self.observed,self.key,self.tail,self.world,self.arena,self.context = fixture()

    def test_exact_two_action_order_and_persistent_tail(self):
        graph = source.validate_graph(self.c,self.root,self.observed)
        self.assertEqual(tuple(self.c.path_name(a) for a in graph.actions),tuple(s.path for s in source.STAGES))
        graph = source.validate_tail(self.c,graph,self.tail)
        self.assertEqual(self.c.path_name(graph.persistent_flag),source.FLAG)
        self.assertTrue(graph.includes_campaign_tail)

    def test_missing_tail_partial_or_reordered_array_rejected(self):
        array = self.observed.values[self.key]
        for bad in (StoredArray(array.items[:1],1),StoredArray(array.items[:1],2),StoredArray(array.items[::-1],2)):
            with self.assertRaises(ValueError):
                source.validate_graph(self.c,self.root,replace(self.observed,values={self.key:bad}))
        with self.assertRaises(ValueError):
            source.validate_graph(self.c,self.root,replace(self.observed,truncated=frozenset((self.key,))))

    def test_wrong_root_identity_owner_or_same_named_class_rejected(self):
        with self.assertRaises(RuntimeQueryError):
            source.validate_graph(self.c,replace(self.root,serial=2),self.observed)
        objects = list(self.c.objects)
        cls = objects[7]
        objects[7] = replace(cls,outer_index=self.root.outer_index)
        altered = Catalog(123,objects,tuple(self.c.classes.values()))
        with self.assertRaises(ValueError):
            source.validate_graph(altered,self.root,self.observed)
        with self.assertRaises(ValueError):
            source.validate_graph(self.c,self.root,replace(self.observed,target=self.world))

    def test_wrapper_ambiguity_or_error_rejected(self):
        array = self.observed.values[self.key];wrapper = array.items[0]
        for bad in (replace(wrapper,truncated=True),replace(wrapper,errors={'GameActionInline':'bad'}),
                    replace(wrapper,fields=dict(wrapper.fields,GameActionReference=self.root)),
                    replace(wrapper,types={})):
            with self.assertRaises(ValueError):
                source.validate_graph(self.c,self.root,replace(self.observed,
                    values={self.key:StoredArray((bad,array.items[1]),2)}))

    def test_tail_false_wrong_flag_or_incomplete_values_rejected(self):
        graph = source.validate_graph(self.c,self.root,self.observed)
        key = (graph.actions[1].class_index,'Value')
        for bad in (replace(self.tail,values={**self.tail.values,key:False}),
                    replace(self.tail,errors={key:'unsupported'}),
                    replace(self.tail,values={**self.tail.values,(key[0],'NamedID'):self.root})):
            with self.assertRaises(ValueError):
                source.validate_tail(self.c,graph,bad)

    def test_original_context_arena_frame_and_source_reference_required(self):
        pose = source.frame.original_pose(source.WORLD)
        self.assertEqual(source.validate_original_context(self.c,self.context,self.world,self.arena,pose,
                         arena_reference=source.ARENA),(self.world,self.arena))
        for change in (dict(arena_reference='None'),dict(context=dict(self.context,world=(123,1,2,3))),
                       dict(pose=pose[:4]+(0.,)+pose[5:])):
            args = dict(catalog=self.c,context=self.context,world=self.world,arena=self.arena,pose=pose,
                        arena_reference=source.ARENA);args.update(change)
            with self.assertRaises(ValueError):source.validate_original_context(**args)

    def test_observer_projects_only_graph_and_tail(self):
        with patch('expedition33.pair_source.read_values_with_references',
                   side_effect=((self.observed,self.c),(self.tail,self.c))) as read:
            graph,catalog = source.observe_graph(self.c,self.root)
        self.assertEqual(read.call_args_list[0].kwargs,dict(fields=('GameActionsToExecute',)))
        self.assertEqual(read.call_args_list[1].kwargs,dict(fields=('NamedID','Value')))
        self.assertIs(catalog,self.c)
        self.assertIsNotNone(graph.persistent_flag)

    def test_pinned_recipe_preserves_exact_trigger_and_source_arena(self):
        rows = json.loads((Path(__file__).resolve().parents[1]/'src/expedition33/_original_trigger_recipes.json').read_text())['recipes']
        pair = next(row for row in rows if row['id']=='duolliste-pair')
        self.assertEqual(pair['battle_source'],source.STAGES[0].path)
        self.assertEqual(pair['arena']['source_actor'],source.ARENA)


if __name__ == '__main__':unittest.main()
