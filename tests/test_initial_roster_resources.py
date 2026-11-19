from contextlib import nullcontext
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33 import initial_encounter_roster as roster


def obj(index):
    return N(index=index, serial=index + 1, address=index * 100)


class InitialRosterResourceTests(unittest.TestCase):
    def setUp(self):
        self.session = N(_transport=N(_executable='candidate-reader'))
        self.actor, self.world, self.pc, self.manager, self.spawn, self.table, self.map_add = map(obj, range(1, 8))
        self.context = dict(world=(7, 2, 3, 200), controller=(7, 3, 4, 300), world_path='World')
        self.scope = N(pid=7, _session=self.session, _check=Mock())
        self.resources = N(scope=self.scope, load=Mock(return_value=self.table),
                           hold=Mock(side_effect=lambda item: N(object=item, active=True)))
        paths = {roster.METADATA[0]: self.spawn, roster.METADATA[1]: self.map_add, roster.ENEMY_TABLE: self.table}
        self.catalog = N(by_index={o.index: o for o in (self.actor, self.world, self.pc, self.manager,
                         self.spawn, self.table, self.map_add)}, find_path=paths.__getitem__)
        self.catalog.with_observations = lambda other: self.catalog
        self.owner = roster.InitialEncounterRoster.__new__(roster.InitialEncounterRoster)
        self.owner.scope = self.scope
        self.owner.started = False
        self.owner.objects = []
        self.owner.enemy = N(actor_identity=(1, 2, 100))
        self.owner.hold = Mock(side_effect=self.owner.objects.append)
        self.owner.send = Mock()
        self.observe = Mock(return_value=self.context)
        self.enterContext(patch('expedition33._reader.shared_operation', side_effect=lambda *a, **kw: nullcontext()))
        self.capture = self.enterContext(patch('expedition33.catalog.capture_selected', return_value=self.catalog))
        self.metadata = self.enterContext(patch('expedition33.catalog.capture_matching', return_value=self.catalog))
        self.manager_read = self.enterContext(patch('expedition33._npc_encounter_preparation._controller_battle_manager',
                                                    return_value=(self.manager, self.catalog)))

    def test_title_warm_owns_only_immutable_inputs_and_rejects_expired_leases(self):
        first = roster.warm(self.resources)
        self.assertEqual(first, (self.spawn, self.map_add, self.table))
        self.assertEqual(roster.warm(self.resources), first)
        self.metadata.assert_called_once_with(7, names=('SpawnEnemies', 'Map_Add'))
        self.resources.load.assert_called_once_with(roster.ENEMY_TABLE)
        self.owner.send.assert_not_called()
        self.resources._initial_roster_inputs['objects'][0].active = False
        with self.assertRaisesRegex(RuntimeError, 'lease expired'):
            roster.warm(self.resources)

    def test_failed_warm_is_published_and_not_retried(self):
        self.resources.load.side_effect = RuntimeError('load outcome unknown')
        with self.assertRaisesRegex(RuntimeError, 'load outcome unknown'):
            roster.warm(self.resources)
        with self.assertRaisesRegex(RuntimeError, 'not replayed'):
            roster.warm(self.resources)
        self.assertEqual(self.resources.load.call_count, 1)

    def test_fresh_selected_inputs_use_controller_manager_and_native_holds(self):
        roster.warm(self.resources)
        self.metadata.reset_mock()
        with patch('expedition33.assets.load_asset', side_effect=AssertionError('No duplicate table load')):
            self.owner.prepare(('ExampleTrainingTarget',), resources=self.resources, observe_context=self.observe)
        self.metadata.assert_not_called()
        self.capture.assert_called_once_with(7, ((1, 2, 100), (2, 3, 200), (3, 4, 300),
                                               (5, 6, 500), (7, 8, 700), (6, 7, 600)))
        self.manager_read.assert_called_once_with(self.catalog, self.pc)
        self.assertEqual(self.owner.objects, [self.actor, self.world, self.pc, self.manager,
                                             self.spawn, self.table, self.map_add])
        self.assertEqual(self.observe.call_count, 2)
        self.owner.send.assert_called_once_with(0)
        self.assertTrue(self.owner.started)

    def test_context_change_prevents_any_native_hold_or_hook(self):
        self.observe.side_effect = [self.context, dict(self.context, controller=(7, 3, 99, 300))]
        with self.assertRaisesRegex(RuntimeError, 'World/controller changed'):
            self.owner.prepare(('ExampleTrainingTarget',), resources=self.resources, observe_context=self.observe)
        self.owner.hold.assert_not_called()
        self.owner.send.assert_not_called()

    def test_foreign_resource_session_is_rejected_before_observation(self):
        self.resources.scope = N(_session=object())
        with self.assertRaisesRegex(RuntimeError, 'another session'):
            self.owner.prepare(('ExampleTrainingTarget',), resources=self.resources, observe_context=self.observe)
        self.observe.assert_not_called()
        self.owner.send.assert_not_called()

    def test_legacy_callers_keep_load_and_retention_behavior_without_manager_scan(self):
        table = N(return_value=self.table, release=Mock())
        with (patch('expedition33.cinematics.controller_anchor.context_observer', return_value=self.observe),
              patch('expedition33.assets.load_asset', return_value=table) as load):
            self.owner.prepare(('Goblu',))
        self.metadata.assert_called_once_with(7, names=('SpawnEnemies', 'Map_Add'))
        load.assert_called_once_with(self.scope, roster.ENEMY_TABLE)
        table.release.assert_called_once_with()
        self.owner.send.assert_called_once_with(0)


if __name__ == '__main__':
    unittest.main()
