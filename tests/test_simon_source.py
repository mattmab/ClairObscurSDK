from dataclasses import replace
from types import MappingProxyType
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.values import StoredArray, StoredStruct, StoredValues
from expedition33 import simon_source as source


def fixture():
    names = ['Object', 'Class', 'Package', 'ScriptStruct', 'World',
             'BP_GameAction_Sequential_C', 'BP_GameAction_CinematicWithLightingScenario_C',
             'BP_GameAction_TriggerBattle_C', 'BP_GameAction_WritePersistentFlag_C',
             'BP_GameAction_AddItemToInventory_C', 'BP_GameAction_PlaySound_C']
    classes = [ClassRelation(i, 1, name, -1 if i == 0 else 0, 256)
               for i, name in enumerate(names)]
    objects = [CatalogObject(123, i, 1, 0x10000 + i*256, name, 'Class', 'Class',
                             1, -1, 0, 0, 0) for i, name in enumerate(names)]
    def add(name, cls, outer=None):
        obj = CatalogObject(123, len(objects), 1, 0x10000 + len(objects)*256,
                            name, names[cls], 'Class', cls,
                            -1 if outer is None else outer.index, 0 if outer is None else 1, 0, 0)
        objects.append(obj); return obj
    packages = {}
    def package(path):
        if path not in packages: packages[path] = add(path, 2)
        return packages[path]
    for index in range(5,11):
        objects[index] = replace(objects[index],
            outer_index=package(source._CLASS_PACKAGES[names[index]]).index, outer_serial=1)
    wrapper_type = add('GameAction_Wrapper', 3, package('/Script/SandFall'))
    root = add('DA_GA_SQT_BossSimon', 5, package(source.PACKAGE))
    actions = []
    for stage in source._EXPECTED:
        if ':' in stage.path:
            obj = add(stage.path.split(':')[1], names.index(stage.class_name), root)
        else:
            pkg, name = stage.path.split('.')
            obj = add(name, names.index(stage.class_name), package(pkg))
        actions.append(obj)
    catalog = Catalog(123, objects, classes)
    wrappers = []
    for action, stage in zip(actions, source._EXPECTED):
        values = dict(GameActionReference=None, GameActionInline=None)
        values[stage.wrapper_field] = action
        wrappers.append(StoredStruct(wrapper_type, MappingProxyType(values), {},
            dict(GameActionReference='ObjectProperty', GameActionInline='ObjectProperty'), False))
    key = (root.class_index, 'GameActionsToExecute')
    observation = StoredValues(root, {key: StoredArray(tuple(wrappers), 10)}, {}, {key:'ArrayProperty'})
    return catalog, root, observation, key


class SimonSourceTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.root, self.observation, self.key = fixture()

    def test_exact_original_graph_includes_both_sources_and_campaign_tail(self):
        graph = source.validate_graph(self.catalog, self.root, self.observation)
        self.assertEqual(len(graph.actions), 10)
        self.assertTrue(graph.includes_campaign_tail)
        self.assertEqual(self.catalog.path_name(graph.actions[1]), source.ROOT + ':BP_GameAction_TriggerBattle_C_1')
        self.assertEqual(self.catalog.path_name(graph.actions[3]), source.ROOT + ':BP_GameAction_TriggerBattle_C_0')
        self.assertEqual(graph.actions[5].class_name, 'BP_GameAction_WritePersistentFlag_C')

    def test_partial_or_truncated_graph_rejected(self):
        original = self.observation.values[self.key]
        for array in (StoredArray(original.items[:5], 5), StoredArray(original.items[:5], 10)):
            with self.assertRaises(ValueError):
                source.validate_graph(self.catalog, self.root, replace(self.observation, values={self.key:array}))
        with self.assertRaises(ValueError):
            source.validate_graph(self.catalog, self.root, replace(self.observation, truncated=frozenset((self.key,))))

    def test_wrong_source_or_stage_order_rejected(self):
        original = self.observation.values[self.key]
        items = list(original.items); items[1], items[3] = items[3], items[1]
        with self.assertRaisesRegex(ValueError, 'order or source'):
            source.validate_graph(self.catalog, self.root, replace(self.observation,
                values={self.key:StoredArray(tuple(items), 10)}))

    def test_wrapper_ambiguity_errors_and_missing_fields_rejected(self):
        original = self.observation.values[self.key]
        wrapper = original.items[0]
        bad_values = dict(wrapper.fields, GameActionInline=wrapper.fields['GameActionReference'])
        for bad in (replace(wrapper, truncated=True), replace(wrapper, errors={'GameActionInline':'unsupported'}),
                    replace(wrapper, fields=bad_values), replace(wrapper, fields={'GameActionReference':None})):
            items = (bad,) + original.items[1:]
            with self.assertRaises(ValueError):
                source.validate_graph(self.catalog, self.root, replace(self.observation,
                    values={self.key:StoredArray(items, 10)}))

    def test_source_identity_and_class_checks(self):
        with self.assertRaises(RuntimeQueryError):
            source.validate_graph(self.catalog, replace(self.root, serial=2), self.observation)
        with self.assertRaises(ValueError):
            source.validate_graph(self.catalog, self.root, replace(self.observation, target=self.catalog.objects[0]))
        objects = list(self.catalog.objects)
        objects[self.root.index] = replace(self.root, object_flags=0x20)
        changed = Catalog(123, objects, tuple(self.catalog.classes.values()))
        with self.assertRaises(ValueError):
            source.validate_graph(changed, objects[self.root.index], self.observation)

    def test_exact_original_cinematic_dependencies(self):
        cinematics = tuple(stage for stage in source.STAGES if stage.sequence)
        self.assertEqual(tuple(stage.cinematic_id for stage in cinematics),
                         ('SimonIntro', 'SimonPhaseTransition', 'SimonOutro'))
        self.assertIn('/Simon/Sequences/SEQ_Simon_Skill_10_PhaseSwitch.', cinematics[1].sequence)
        self.assertTrue(source.EXIT.startswith(source.WORLD + ':PersistentLevel.BP_Cine_ExitPoint_C_'))

    def test_same_named_class_in_another_package_rejected(self):
        objects = list(self.catalog.objects)
        cls = objects[7]
        objects[7] = replace(cls, outer_index=self.root.outer_index)
        altered = Catalog(123,objects,tuple(self.catalog.classes.values()))
        with self.assertRaisesRegex(ValueError,'order or source'):
            source.validate_graph(altered,self.root,self.observation)

    def test_observer_projects_only_the_original_array(self):
        with patch('expedition33.simon_source.read_values_with_references',
                   return_value=(self.observation,self.catalog)) as read:
            graph, catalog = source.observe_graph(self.catalog,self.root)
        read.assert_called_once_with(self.catalog,self.root,fields=('GameActionsToExecute',))
        self.assertIs(catalog,self.catalog)
        self.assertEqual(len(graph.actions),10)
