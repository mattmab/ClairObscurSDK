"""No stage may advance on idle, interruption, stale context or deferred cleanup."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33.simon_portable import PortableSimon
from expedition33._sequence_owner import SequenceCleanupDeferred
from expedition33._menu_latency import MenuLatency


class PortableSimonTests(unittest.TestCase):
    def test_constructor_registers_the_actual_scope_owner(self):
        from expedition33._scope import SessionScope
        scope = NS(_check=Mock(), _native_owners=[],
                   _session=NS(_transport=NS(battle_completion_receipt_protocol=1)))
        scope._register_native_owner = lambda owner: SessionScope._register_native_owner(scope, owner)
        runner = PortableSimon(scope, disposable_test=True)
        self.assertIs(runner._scope, scope)
        self.assertIn(runner, scope._native_owners)

    def runner(self, state='intro'):
        r = PortableSimon.__new__(PortableSimon)
        r.state, r.error, r.scene = state, None, 'intro'
        r.scope = NS()
        r.context = {'world': (123, 1, 2, 0x10000)}
        r.initial_pawn, r.initial_position = (123, 2, 3, 0x20000), (1., 2., 3.)
        r.return_position = None
        r.panel = r.presentation = None
        r.latency = MenuLatency()
        r.receipts, r.completed_scenes = [], []
        r._battle_timings=[]
        r._current = Mock()
        r._close_scene = Mock()
        r.sequence = NS(completion=Mock(return_value={
            'state': 'playing', 'endpoint_observed': False}))
        r.fight = NS(recipe={'id':'simon-normal'},latency=MenuLatency(),dispatch_prepared=Mock(), poll=Mock(), close=Mock(return_value=True),
                     _parameters=NS(completion_receipt=Mock(return_value=NS(state='pending', result=None))))
        r._prepare_battle = Mock()
        r._start_scene = Mock()
        return r

    def test_idle_without_receipt_never_advances_battle(self):
        r = self.runner('battle1')
        r.fight.poll.return_value = {'phase': 'idle_retained'}
        r.poll()
        self.assertEqual(r.state, 'battle1')
        r._prepare_battle.assert_not_called()
        r._start_scene.assert_not_called()

    def test_intro_requires_qualified_endpoint_before_entry(self):
        r = self.runner()
        r.poll()
        r.fight.dispatch_prepared.assert_not_called()
        r.sequence.completion.return_value = {'state': 'endpoint_observed', 'endpoint_observed': True}
        r.poll()
        self.assertEqual(r.state, 'battle1')
        r._close_scene.assert_called_once()
        r.fight.dispatch_prepared.assert_called_once_with(track_completion=True)

    def test_interrupted_intro_never_enters_battle(self):
        r = self.runner()
        r.sequence.completion.return_value = {'state': 'interrupted', 'endpoint_observed': False}
        with self.assertRaisesRegex(RuntimeError, 'endpoint'):
            r.poll()
        self.assertEqual(r.state, 'blocked')
        r.fight.dispatch_prepared.assert_not_called()

    def test_victory_waits_for_retirement_before_phase_two_preparation(self):
        r = self.runner('battle1')
        r.fight._parameters.completion_receipt.return_value = NS(state='ready', result='victory')
        r.poll()
        self.assertEqual(r.state, 'victory_battle1')
        r.fight.close.return_value = False
        r.poll()
        r._prepare_battle.assert_not_called()
        r.fight.close.return_value = True
        r.poll()
        r._prepare_battle.assert_called_once_with('simon-phase2')
        r._start_scene.assert_called_once_with('transition')

    def test_defeat_never_plays_transition_or_second_battle(self):
        r = self.runner('battle1')
        r.fight._parameters.completion_receipt.return_value = NS(state='ready', result='defeat')
        r.poll()
        r.poll()
        self.assertEqual(r.state, 'defeated')
        r._prepare_battle.assert_not_called()
        r._start_scene.assert_not_called()

    def test_replaced_world_blocks_before_receipt_consumption(self):
        r = self.runner('battle2')
        r._current.side_effect = RuntimeError('World was replaced')
        with self.assertRaisesRegex(RuntimeError, 'replaced'):
            r.poll()
        r.fight._parameters.completion_receipt.assert_not_called()
        self.assertEqual(r.state, 'blocked')

    def test_outro_return_must_match_original_pawn_and_position(self):
        for position, expected in (((1., 2., 3.), 'completed'), ((100., 2., 3.), 'blocked')):
            r = self.runner('outro')
            r.scene = 'outro'
            r.sequence.completion.return_value = {'state': 'endpoint_observed', 'endpoint_observed': True}
            with self.subTest(position=position), patch('expedition33.simon_portable._snapshot',
                    return_value=(r.context, r.initial_pawn, position)):
                if expected == 'blocked':
                    with self.assertRaisesRegex(RuntimeError, 'start position'):
                        r.poll()
                else:
                    r.poll()
                self.assertEqual(r.state, expected)

    def test_scene_translation_is_copied_before_arena_retirement(self):
        r = self.runner()
        r.spawner = NS(original_fight=None)
        source = {'X':1., 'Y':2., 'Z':3.}
        grounding = {'verified':True, 'after':[101.,202.,303.]}
        fight = NS(prepare=Mock(), recipe={'arena':{'frames':{'DefaultSceneRoot':{'location':source}}}},
                   _arena=NS(grounding=grounding))
        with patch('expedition33.simon_portable.OriginalTriggerFight', return_value=fight):
            PortableSimon._prepare_battle(r, 'simon-normal')
        self.assertEqual(r._scene_delta, (100.,200.,300.))
        # Retirement may release/reset every live arena reference; the scene
        # consumes only the immutable placement captured while it was owned.
        grounding['after'][0] = -999.
        fight._arena = None
        panel = NS(state='built', uncertain=False, build=Mock(), open=Mock())
        sequence = NS(build=Mock(), prepare_completion=Mock(), play=Mock())
        with patch('expedition33.simon_portable.CinematicContextPanel', return_value=panel), \
                patch('expedition33.simon_portable.OwnedLevelSequence', return_value=sequence):
            r.scope = NS(_session=object())
            PortableSimon._start_scene(r, 'outro')
        self.assertEqual(sequence.build.call_args.kwargs['origin_translation'], (100.,200.,300.))
        self.assertEqual(r.state, 'outro')

    def test_unverified_or_nonfinite_grounding_never_supplies_scene_delta(self):
        for grounding in ({'verified':False,'after':[1.,2.,3.]},
                          {'verified':True,'after':[1.,float('nan'),3.]}):
            r = self.runner()
            r.spawner = NS(original_fight=None)
            fight = NS(prepare=Mock(), recipe={'arena':{'frames':{'DefaultSceneRoot':{
                'location':{'X':0.,'Y':0.,'Z':0.}}}}}, _arena=NS(grounding=grounding))
            with self.subTest(grounding=grounding), \
                    patch('expedition33.simon_portable.OriginalTriggerFight', return_value=fight), \
                    self.assertRaises(RuntimeError):
                PortableSimon._prepare_battle(r, 'simon-normal')
            self.assertIsNone(r._scene_delta)

    def test_close_deferral_preserves_resources_and_never_continues_scene(self):
        r = self.runner()
        r.spawner = NS(close=Mock(return_value=True))
        r._close_scene.side_effect = (SequenceCleanupDeferred('pending'), None)
        self.assertFalse(r.close())
        self.assertEqual(r.state, 'intro')
        r.spawner.close.assert_not_called()
        r.sequence.completion.return_value = {'state':'endpoint_observed','endpoint_observed':True}
        r.poll()
        r.fight.dispatch_prepared.assert_not_called()
        self.assertTrue(r.close())
        self.assertEqual(r.state, 'closed')
        r.spawner.close.assert_called_once()

    def test_close_scene_retains_sequence_until_close_acknowledges(self):
        r = self.runner()
        sequence = NS(close=Mock(side_effect=SequenceCleanupDeferred('pending')))
        r.sequence = sequence
        r.presentation = NS(close=Mock())
        r.panel = NS(close=Mock())
        with self.assertRaises(SequenceCleanupDeferred):
            PortableSimon._close_scene(r)
        self.assertIs(r.sequence, sequence)
        r.presentation.close.assert_not_called()
        r.panel.close.assert_not_called()

    def test_unknown_scene_close_failure_is_not_silenced_or_released(self):
        r = self.runner()
        r.spawner = NS(close=Mock())
        r._close_scene.side_effect = RuntimeError('unknown close outcome')
        with self.assertRaisesRegex(RuntimeError, 'unknown close'):
            r.close()
        r.spawner.close.assert_not_called()

    def test_context_tree_is_reused_but_input_owner_is_reopened_each_scene(self):
        r = self.runner()
        r.scope = NS(_session=object())
        r._scene_delta = (10.,20.,30.)
        panel = NS(state='built', uncertain=False, build=Mock(), open=Mock(), hide=Mock(return_value=True))
        panel.open.side_effect = lambda:setattr(panel, 'state', 'open')
        def hide():
            panel.state = 'built'
            return True
        panel.hide.side_effect = hide
        first = NS(build=Mock(), prepare_completion=Mock(), play=Mock(), close=Mock())
        second = NS(build=Mock(), prepare_completion=Mock(), play=Mock(), close=Mock())
        with patch('expedition33.simon_portable.CinematicContextPanel', return_value=panel) as constructor, \
                patch('expedition33.simon_portable.OwnedLevelSequence', side_effect=(first,second)):
            PortableSimon._start_scene(r, 'intro')
            PortableSimon._close_scene(r)
            self.assertIs(r.panel, panel)
            self.assertEqual(panel.state, 'built')
            PortableSimon._start_scene(r, 'transition')
        constructor.assert_called_once()
        panel.build.assert_called_once()
        self.assertEqual(panel.open.call_count, 2)
        panel.hide.assert_called_once()
        first.close.assert_called_once()
        self.assertIs(r.sequence, second)

    def test_pending_input_detachment_retains_tree_and_prevents_next_battle(self):
        r = self.runner('intro_cleanup')
        r.panel = NS(hide=Mock(return_value=False))
        r.sequence = NS(close=Mock())
        r._close_scene = lambda:PortableSimon._close_scene(r)
        r.poll()
        self.assertEqual(r.state, 'intro_cleanup')
        self.assertIsNotNone(r.panel)
        self.assertIsNone(r.sequence)
        r.fight.dispatch_prepared.assert_not_called()


if __name__ == '__main__':
    unittest.main()
