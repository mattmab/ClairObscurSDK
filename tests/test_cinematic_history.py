import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.cinematics import history
from expedition33.values import StoredMap
from expedition33 import RuntimeQueryError


class CurrentHistoryTests(unittest.TestCase):
    def test_reader_diagnostics_are_reduced_to_bounded_ui_text(self):
        error = RuntimeQueryError('Read worker rejected query: {"event":"snapshot_start","address":"0x1234"}\n'
                                  '{"event":"error","message":"MATCH_TYPE_NOT_REGISTERED"}')
        message = history.observation_error_reason(error)
        self.assertIn('Game objects changed', message)
        self.assertNotIn('0x1234', message)
        self.assertNotIn('{', message)
        self.assertLess(len(message), 180)
        self.assertIn('MATCH_TYPE_NOT_REGISTERED', str(error))

    def test_unknown_or_untrusted_failure_does_not_leak_diagnostic_payload(self):
        for error in (RuntimeQueryError('{"event":"error","message":"UNKNOWN_NATIVE_FAILURE"}'),
                      RuntimeError('private diagnostic\n' * 500)):
            message = history.observation_error_reason(error)
            self.assertIn('SDK log', message)
            self.assertLess(len(message), 180)
            self.assertNotIn('\n', message)
        self.assertEqual(history.observation_error_reason(RuntimeError('A save load is in progress')),
                         'A save load is in progress')

    def test_mod_logs_original_failure_but_exposes_no_raw_payload_or_unlocks(self):
        from test_cinematics import module as mod
        from cinematics_v2_fixtures import ready_model
        error = RuntimeQueryError('Read worker rejected query: {"event":"error","message":"MATCH_TYPE_NOT_REGISTERED"}')
        for stage in ('controller', 'history'):
            with self.subTest(stage=stage):
                model = ready_model(mod, {'id': 'old-unlocked-scene', 'unlocked': True})
                model.session._session._transport.original_game_action_protocol = 0
                model._catalog_inputs = Mock(return_value=({}, b''))
                with patch.object(mod, 'shared_operation'), \
                     patch.object(mod, 'controller_context', return_value={},
                                  side_effect=error if stage == 'controller' else None), \
                     patch.object(mod, 'read_current_history', side_effect=error), \
                     patch.object(mod, 'catalog_scenes', return_value=[]), \
                     patch.object(mod.LOG, 'exception') as logged:
                    result = mod.Mod._refresh_now(model)
                logged.assert_called_once_with('Cinematics current-history observation failed')
                self.assertEqual(result['state'], 'history_unavailable')
                self.assertEqual(result['confirmed'], [])
                self.assertIsNone(model._context)
                self.assertNotIn('MATCH_TYPE_NOT_REGISTERED', model.reason)
                self.assertNotIn('{', model.reason)

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
        indices.update({o.index:o for o in self.objects})
        self.catalog = SimpleNamespace(pid=17, by_index=indices,
            select=lambda name: [o for o in self.objects if o.class_name == name],
            path_name=lambda o: f'/Engine/Transient.{o.class_name}_{o.index}',
            find_class=lambda name: self.classes[name])
        self.session = SimpleNamespace(pid=17, _check=Mock())
        self.references = dict(GameViewport=self.viewport, World=self.world, OwningGameInstance=self.gi,
                               GameInstanceReference=self.gi, SaveManager=self.manager)
        self.reference_calls = []
        self.reference_projection = []
        self.value_requests = []
        self.read_counts = dict(manager=0, gi=0)
        self.hook = lambda name, count, data: None
        self.patches = (
            patch.object(history, 'capture_matching', return_value=self.catalog),
            patch.object(history, 'read_object_reference', side_effect=self.reference),
            patch.object(history, 'read_values_many', side_effect=self.values_many))
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def reference(self, catalog, obj, owner, name, *, project=False):
        self.reference_calls.append(name)
        self.reference_projection.append(project)
        return self.references[name], catalog

    def values_many(self, catalog, objects, *, fields):
        self.value_requests.append((tuple(objects), tuple(fields)))
        return {obj.index: self.values(catalog, obj) for obj in objects}

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

    def test_prepared_selectors_preserve_both_fresh_history_observations(self):
        prepared=Mock();prepared.capture.return_value=self.catalog
        with patch.object(history,'capture_matching') as scan:
            result=history.read_current_history(self.session,prepared=prepared)
        prepared.capture.assert_called_once_with(self.session);scan.assert_not_called()
        self.assertEqual(result['selected_slot'],0)
        self.assertEqual(self.read_counts,{'manager':2,'gi':2})
        self.assertEqual(self.reference_calls.count('OwningGameInstance'),2)

    def test_prepared_anchor_batches_both_observations_and_rejects_changed_links(self):
        prepared=object.__new__(history.PreparedHistorySelectors)
        prepared.chain_indices=(1,2,3,4);prepared.capture=Mock(return_value=self.catalog)
        for corrupt_at in (None,1,2):
            self.read_counts=dict(manager=0,gi=0);batches=[]
            def values(catalog,objects,*,fields):
                if tuple(objects)==(self.engine,self.viewport,self.world):
                    batches.append(tuple(fields));result={}
                    for owner,name,target in zip(objects,('GameViewport','World','OwningGameInstance'),(self.viewport,self.world,self.gi)):
                        if corrupt_at==len(batches) and owner is self.world:target=self.manager
                        key=(owner.class_index,name)
                        result[owner.index]=SimpleNamespace(types={key:'ObjectProperty'},values={key:target},errors={},truncated=set())
                    return result
                return self.values_many(catalog,objects,fields=fields)
            with patch.object(history,'read_values_many',side_effect=values):
                if corrupt_at is None:
                    result=history.read_current_history(self.session,prepared=prepared)
                    self.assertEqual(result['selected_slot'],0)
                    self.assertEqual(self.read_counts,{'manager':2,'gi':2})
                    self.assertEqual(len(batches),2)
                else:
                    with self.assertRaisesRegex(RuntimeError,'Active world context changed'):
                        history.read_current_history(self.session,prepared=prepared)
                    self.assertEqual(len(batches),corrupt_at)
            self.assertTrue(all(set(fields)=={'GameViewport','World','OwningGameInstance'} for fields in batches))

    def test_prepared_identity_rejection_does_not_fallback_to_scan(self):
        prepared=Mock();prepared.capture.side_effect=RuntimeError('identity changed')
        with patch.object(history,'capture_matching') as scan:
            with self.assertRaisesRegex(RuntimeError,'identity changed'):
                history.read_current_history(self.session,prepared=prepared)
        scan.assert_not_called();self.assertEqual(self.read_counts,{'manager':0,'gi':0})

    def test_refresh_projects_only_six_context_fields_in_two_fresh_batches(self):
        history.read_current_history(self.session)
        self.assertEqual(len(self.value_requests), 2)
        for objects, fields in self.value_requests:
            self.assertEqual(objects, (self.manager, self.gi))
            self.assertEqual(set(fields), {'GameInstanceReference', 'LoadIsInProgress', 'SelectedSlot',
                                          'SaveManager', 'SaveLoaded', 'InteractedCinematics'})
        self.assertEqual(len(self.reference_projection), 8)
        self.assertTrue(all(self.reference_projection))
        self.assertNotIn('read_values', vars(history))

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

    def test_each_fresh_projected_context_requires_reciprocal_references(self):
        for target, key, replacement in (('manager', 'GameInstanceReference', self.world),
                                         ('gi', 'SaveManager', self.world)):
            for observation in (1, 2):
                with self.subTest(target=target, observation=observation):
                    self.read_counts = dict(manager=0, gi=0)
                    def corrupt(name, count, data):
                        if name == target and count == observation:
                            data.values[(105 if target == 'manager' else 104, key)] = replacement
                    self.hook = corrupt
                    with self.assertRaisesRegex(RuntimeError, 'another game instance|not reciprocal'):
                        history.read_current_history(self.session)

    def test_projection_does_not_accept_missing_or_wrongly_typed_required_fields(self):
        for target, name in (('manager', 'SelectedSlot'), ('gi', 'SaveLoaded')):
            for mode in ('missing', 'wrong_type'):
                with self.subTest(target=target, mode=mode):
                    def corrupt(observed, count, data):
                        if observed == target:
                            key = (105 if target == 'manager' else 104, name)
                            if mode == 'missing': del data.values[key]
                            else: data.types[key] = 'StringProperty'
                    self.hook = corrupt
                    with self.assertRaisesRegex(RuntimeError, 'field is incomplete'):
                        history.read_current_history(self.session)

    def test_active_world_chain_change_rejects(self):
        original = self.reference
        def changed(catalog, obj, owner, name, *, project=False):
            if name == 'World' and self.reference_calls.count('World') == 1:
                self.references['World'] = SimpleNamespace(**{**vars(self.world), 'serial': 4})
            return original(catalog, obj, owner, name, project=project)
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

