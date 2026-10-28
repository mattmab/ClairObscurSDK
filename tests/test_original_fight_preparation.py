"""Presentation gaps must not authorize stale or repeated combat entry."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33._original_trigger_fight import OriginalTriggerFight
from expedition33.enemy_spawning import load_catalog


class OriginalFightPreparationTests(unittest.TestCase):
    def setUp(self):
        transport = NS(battle_completion_receipt_protocol=1)
        scope = NS(_check=Mock(), _session=NS(_transport=transport),
                   _register_native_owner=Mock())
        spawner = NS(_scope=scope, _owner=Mock(), catalog=load_catalog())
        self.fight = OriginalTriggerFight(spawner, 'simon-normal')
        self.fight._preflight = Mock()
        self.fight._current_context = Mock(return_value={'world': 'current'})
        self.fight._idle = Mock()
        self.fight._retain = Mock(return_value=NS())
        self.fight._construction_inputs = Mock(return_value=((), {}))
        self.fight._arena_frames = Mock()
        self.fight._entry_inputs = Mock(return_value=('fresh',))
        self.fight.status = Mock(side_effect=lambda: {'phase': self.fight.phase})
        self.arena = Mock(actor_identity=(1, 2, 0x10000))
        self.parameters = Mock()
        self.patches = [
            patch('expedition33.owned_battle_arena.OwnedBattleArena', return_value=self.arena),
            patch('expedition33._npc_encounter_preparation.bind_original_arena'),
            patch('expedition33._original_trigger_sequences.OriginalFightSequenceCleanup',
                  side_effect=RuntimeError('Not this source')),
            patch('expedition33._battle_parameter_owner.ParameterResearchOwner',
                  return_value=self.parameters),
        ]
        self.mocks = [p.start() for p in self.patches]
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def test_preparation_holds_owned_resources_without_entry(self):
        self.assertEqual(self.fight.prepare()['phase'], 'prepared')
        self.arena.ground_once.assert_called_once()
        self.fight._owner.spawn_trigger_prepared.assert_called_once()
        self.mocks[3].assert_not_called()
        self.assertFalse(self.fight.dispatch_attempted)

    def test_entry_rechecks_dependencies_after_presentation(self):
        self.fight.prepare()
        self.fight._entry_inputs.side_effect = RuntimeError('World changed during intro')
        with self.assertRaisesRegex(RuntimeError, 'World changed'):
            self.fight.dispatch_prepared(track_completion=True)
        self.mocks[3].assert_not_called()
        self.assertFalse(self.fight.dispatch_attempted)

    def test_uncertain_entry_is_not_replayed(self):
        self.fight.prepare()
        self.parameters.dispatch_trigger_cleanup.side_effect = RuntimeError('Lost acknowledgement')
        with self.assertRaisesRegex(RuntimeError, 'Lost acknowledgement'):
            self.fight.dispatch_prepared(track_completion=True)
        self.assertEqual(self.fight.phase, 'unknown')
        with self.assertRaisesRegex(RuntimeError, 'enter once'):
            self.fight.dispatch_prepared(track_completion=True)
        self.parameters.dispatch_trigger_cleanup.assert_called_once()

    def test_completion_opt_in_requires_actual_protocol_integer(self):
        self.fight.prepare()
        for capability in (True, 0, 2):
            self.fight._transport.battle_completion_receipt_protocol = capability
            with self.subTest(capability=capability), self.assertRaisesRegex(RuntimeError, 'capability'):
                self.fight.dispatch_prepared(track_completion=True)
        self.mocks[3].assert_not_called()
        self.assertFalse(self.fight.dispatch_attempted)

    def test_legacy_start_still_prepares_then_dispatches_once(self):
        self.assertEqual(self.fight.start()['phase'], 'entry_pending')
        self.assertEqual(self.fight._entry_inputs.call_count, 2)
        self.parameters.dispatch_trigger_cleanup.assert_called_once_with(
            ('fresh',), anchor=self.fight._owner, arena=self.arena, mode=1)

    def test_native_preparation_timings_survive_a_failed_grounding_step(self):
        self.arena.ground_once.side_effect=RuntimeError('placement blocked')
        with self.assertRaisesRegex(RuntimeError,'placement blocked'):
            self.fight.prepare()
        timings=self.fight.latency.snapshot()['timings']
        self.assertEqual(timings['prepare.arena_native_construction']['count'],1)
        self.assertEqual(timings['prepare.arena_grounding_clearance']['failed'],1)
        self.assertEqual(timings['battle.prepare_total']['failed'],1)
        self.assertNotIn('prepare.trigger_native_construction',timings)
        self.mocks[3].assert_not_called()

    def test_all_owned_preparation_steps_are_measured_without_dispatch(self):
        self.fight.prepare()
        timings=self.fight.latency.snapshot()['timings']
        for name in ('prepare.arena_native_construction','prepare.arena_grounding_clearance',
                     'prepare.arena_camera_focus','prepare.trigger_native_construction','prepare.arena_binding'):
            self.assertEqual(timings[name]['count'],1)
            self.assertEqual(timings[name]['failed'],0)
        self.assertFalse(self.fight.dispatch_attempted)


if __name__ == '__main__':
    unittest.main()
