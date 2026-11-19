from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33.story_facial import DialogueFacialPerformance, NPC, FACE


def obj(index, serial=1):
    return N(index=index, serial=serial, address=0x10000 + 16 * index, class_index=90)


class FacialPlannerReuseTests(unittest.TestCase):
    def setUp(self):
        self.paths = tuple(NPC + name for name in ('SetFacialExpression', 'SetIsTalking',
                          'SetIsInDialogue', 'UpdateEnvelopeVolume'))
        self.target = obj(1)
        self.functions = {path: obj(20 + i) for i, path in enumerate(self.paths)}
        self.plans = []
        self.warm = N(paths=set(self.paths), planner=Mock(side_effect=self.new_planner))
        self.owner = DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        self.owner.scope = N(pid=7, _session=N(_story_performance_preflight=self.warm))
        self.owner.calls = {}; self.owner.planners = []; self.owner._warm_planners = {}
        self.owner.closed = self.owner.unknown = self.owner.prepared = False

    def new_planner(self, scope, target, path, arguments, **kwargs):
        catalog = N(by_index={o.index: o for o in (target, *self.functions.values())},
                    find_path=self.functions.__getitem__)
        planner = N(_catalog=catalog, close=Mock(), _check=Mock(), _generation=1)
        def prepare(target, function, **arguments):
            call = N(_planner=lambda: planner, _plan=N(function=function), _generation=planner._generation, invoke=Mock(), bind=Mock())
            self.plans.append(call)
            return call
        planner.prepare_blueprint = Mock(side_effect=prepare)
        planner.prepare = Mock(side_effect=prepare)
        planner.prepare_dialogue_slot = Mock(side_effect=prepare)
        planner.adopt_observations = Mock(side_effect=lambda observed: catalog.by_index.update(observed))
        return planner

    def test_four_component_functions_share_one_qualified_target_planner(self):
        for path in self.paths:
            self.owner._prepare_call(self.target, path, Value=True)
        self.warm.planner.assert_called_once_with(self.owner.scope, self.target, self.paths[0],
                                                 {'Value': True}, defer_reads=False)
        self.assertEqual(len(self.owner.planners), 1)
        self.assertEqual(self.owner.planners[0].prepare_blueprint.call_count, 4)
        self.assertEqual(len(self.owner.calls), 4)
        for call in self.plans:
            call.invoke.assert_not_called()

    def test_new_argument_generation_is_observed_before_planning(self):
        self.owner._prepare_call(self.target, self.paths[0])
        planner = self.owner.planners[0]
        old, replacement = obj(9), obj(9, serial=2)
        planner._catalog.by_index[9] = old
        with patch('expedition33.story_facial.capture_selected', return_value={9: replacement}) as capture:
            self.owner._prepare_call(self.target, self.paths[1], Asset=replacement)
        capture.assert_called_once_with(7, ((9, 2, replacement.address),))
        planner.adopt_observations.assert_called_once_with({9: replacement})
        self.assertIs(planner._catalog.by_index[9], replacement)
        self.assertEqual(self.warm.planner.call_count, 1)

    def test_argument_read_failure_prevents_planning_or_dispatch(self):
        from expedition33 import RuntimeQueryError
        self.owner._prepare_call(self.target, self.paths[0])
        planner = self.owner.planners[0]
        with patch('expedition33.story_facial.capture_selected', side_effect=RuntimeQueryError('stale')):
            with self.assertRaises(RuntimeQueryError):
                self.owner._prepare_call(self.target, self.paths[1], Asset=obj(9))
        self.assertEqual(planner.prepare_blueprint.call_count, 1)
        self.assertEqual(len(self.owner.calls), 1)
        self.assertFalse(self.owner.unknown)
        self.plans[0].invoke.assert_not_called()

    def test_changed_target_generation_cannot_reuse_old_planner(self):
        self.owner._prepare_call(self.target, self.paths[0])
        replacement = obj(1, serial=2)
        self.owner._prepare_call(replacement, self.paths[1])
        self.assertEqual(self.warm.planner.call_count, 2)
        self.assertEqual(len(self.owner.planners), 2)
        self.assertIs(self.owner.planners[1]._catalog.by_index[1], replacement)

    def test_new_schema_owner_does_not_reuse_old_schema_planner(self):
        self.owner._prepare_call(self.target, self.paths[0])
        other = N(paths=set(self.paths), planner=Mock(side_effect=self.new_planner))
        self.owner.scope._session._story_performance_preflight = other
        self.owner._prepare_call(self.target, self.paths[1])
        other.planner.assert_called_once()
        self.assertEqual(len(self.owner.planners), 2)

    def test_cleanup_closes_shared_planner_exactly_once(self):
        for path in self.paths:
            self.owner._prepare_call(self.target, path)
        with patch('expedition33._retired_tracking.close_lease_only_scope', return_value=True):
            self.assertTrue(self.owner.close(world_retired=True))
        self.owner.planners[0].close.assert_called_once_with()
        self.assertTrue(self.owner.closed)

    def test_unacknowledged_mutation_keeps_shared_planner_owned(self):
        call = self.owner._prepare_call(self.target, self.paths[0])
        call.bind.return_value = call
        call.invoke.side_effect = RuntimeError('ACK lost')
        with self.assertRaisesRegex(RuntimeError, 'ACK lost'):
            self.owner._call(self.target, self.paths[0])
        self.assertTrue(self.owner.unknown)
        self.assertFalse(self.owner.close())
        self.owner.planners[0].close.assert_not_called()


if __name__ == '__main__':
    unittest.main()
