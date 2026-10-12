import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.cinematics import history
from expedition33.values import StoredMap


class CurrentHistoryTests(unittest.TestCase):
    def setUp(self):
        def obj(index, class_name):
            return SimpleNamespace(pid=17, index=index, serial=3, address=0x1000+index*0x100,
                class_index=index+100, class_name=class_name, object_flags=0)
        self.engine, self.viewport, self.world, self.gi, self.manager = (
            obj(1, 'GameEngine'), obj(2, 'GameViewportClient'), obj(3, 'World'),
            obj(4, 'BP_jRPG_GI_Custom_C'), obj(5, 'BP_SaveManager_C'))
        self.objects = (self.engine, self.viewport, self.world, self.gi, self.manager)
        self.classes = {name: SimpleNamespace(index=i) for i, name in enumerate(
            ('Engine', 'GameViewportClient', 'World'), 200)}
        indices = {value.index: value for value in self.classes.values()}
        indices.update({o.class_index: SimpleNamespace(index=o.class_index) for o in self.objects})
        self.catalog = SimpleNamespace(pid=17, by_index=indices,
            select=lambda name: [o for o in self.objects if o.class_name == name],
            path_name=lambda o: f'/Engine/Transient.{o.class_name}_{o.index}',
            find_class=lambda name: self.classes[name])
        self.session = SimpleNamespace(pid=17, _check=Mock())
        self.references = dict(GameViewport=self.viewport, World=self.world, OwningGameInstance=self.gi,
                               GameInstanceReference=self.gi, SaveManager=self.manager)
        self.reference_calls = []
        self.read_counts = dict(manager=0, gi=0)
        self.hook = lambda name, count, data: None
        self.patches = (
            patch.object(history, 'capture_matching', return_value=self.catalog),
            patch.object(history, 'read_object_reference', side_effect=self.reference),
            patch.object(history, 'read_values', side_effect=self.values))
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def reference(self, catalog, obj, owner, name):
        self.reference_calls.append(name)
        return self.references[name], catalog

    def values(self, catalog, obj):
        name = 'manager' if obj is self.manager else 'gi'
        rows = {'GameInstanceReference': ('ObjectProperty', self.gi), 'LoadIsInProgress': ('BoolProperty', False),
                'SelectedSlot': ('IntProperty', 0)} if name == 'manager' else {
                    'SaveManager': ('ObjectProperty', self.manager), 'SaveLoaded': ('BoolProperty', True),
                    'InteractedCinematics': ('MapProperty', StoredMap({'PrologueTitle': True, 'locked': False}))}
        self.read_counts[name] += 1
        data = SimpleNamespace(types={(obj.class_index, k): kind for k, (kind, value) in rows.items()},
            values={(obj.class_index, k): value for k, (kind, value) in rows.items()}, errors={}, truncated=set())
        self.hook(name, self.read_counts[name], data)
        return data

    def test_active_game_history_does_not_require_or_read_last_save_snapshot(self):
        result = history.read_current_history(self.session)
        self.assertEqual(dict(result['history'].items), {'PrologueTitle': True, 'locked': False})
        self.assertEqual(result['history_source'], 'current-session game history')
        self.assertEqual(result['selected_slot'], 0)
        self.assertNotIn('LastSaveGameObject', self.reference_calls)
        self.assertEqual(self.reference_calls.count('OwningGameInstance'), 2)
        self.assertEqual(self.read_counts, {'manager': 2, 'gi': 2})
        self.assertEqual(self.session._check.call_count, 2)

    def test_selected_slot_change_rejects_instead_of_combining(self):
        def change(name, count, data):
            if name == 'manager' and count == 2:
                data.values[(105, 'SelectedSlot')] = 1
        self.hook = change
        with self.assertRaisesRegex(RuntimeError, 'changed during'):
            history.read_current_history(self.session)

    def test_loading_and_not_loaded_contexts_reject(self):
        for target, key, value in [('manager', 'LoadIsInProgress', True), ('gi', 'SaveLoaded', False)]:
            with self.subTest(key=key):
                self.hook = lambda name, count, data: data.values.__setitem__((105 if target == 'manager' else 104, key), value) if name == target else None
                with self.assertRaises(RuntimeError):
                    history.read_current_history(self.session)

    def test_reciprocal_manager_mismatch_rejects(self):
        self.references['SaveManager'] = self.world
        with self.assertRaisesRegex(RuntimeError, 'reciprocal'):
            history.read_current_history(self.session)

    def test_active_world_chain_change_rejects(self):
        original = self.reference
        def changed(catalog, obj, owner, name):
            if name == 'World' and self.reference_calls.count('World') == 1:
                self.references['World'] = SimpleNamespace(**{**vars(self.world), 'serial': 4})
            return original(catalog, obj, owner, name)
        with patch.object(history, 'read_object_reference', side_effect=changed):
            with self.assertRaisesRegex(RuntimeError, 'Active world context changed'):
                history.read_current_history(self.session)

    def test_sparse_descriptor_catalog_and_empty_history_grant_no_unlocks(self):
        # No unrelated property descriptors exist in the fixture catalog.
        self.hook = lambda name, count, data: data.values.__setitem__(
            (104, 'InteractedCinematics'), StoredMap({})) if name == 'gi' else None
        result = history.read_current_history(self.session)
        self.assertEqual(dict(result['history'].items), {})
        self.assertNotIn('describe', vars(history))

    def test_incomplete_map_and_numeric_true_are_rejected(self):
        for mode in ('error', 'truncated', 'numeric'):
            def corrupt(name, count, data):
                if name == 'gi':
                    key = (104, 'InteractedCinematics')
                    if mode == 'error': data.errors[key] = 'partial'
                    elif mode == 'truncated': data.truncated.add(key)
                    else: data.values[key] = StoredMap({'PrologueTitle': 1})
            self.hook = corrupt
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                history.read_current_history(self.session)

    def test_history_change_while_reading_is_not_cached_or_merged(self):
        def changed(name, count, data):
            if name == 'gi' and count == 2:
                data.values[(104, 'InteractedCinematics')] = StoredMap({'different': True})
        self.hook = changed
        with self.assertRaisesRegex(RuntimeError, 'changed during'):
            history.read_current_history(self.session)

