import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

from expedition33.spatial_queries import SpatialQueries, Bounds, WorldRay


class SpatialQueryTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Mock()
        self.scope = Mock()
        self.planner = self.scope.invocation_planner.return_value
        self.query = SpatialQueries(self.scope, catalog=self.catalog)
        self.closed = 0

    def result(self, outputs, status=None):
        @contextmanager
        def invoke():
            try:
                yield SimpleNamespace(outputs=outputs, return_value=status)
            finally:
                self.closed += 1
        self.planner.prepare.return_value.invoke.side_effect = invoke

    def test_explicit_catalog_and_exact_engine_function(self):
        self.scope.invocation_planner.assert_called_once_with(catalog=self.catalog, selected_results=True)
        self.result({'Origin': dict(X=1, Y=2, Z=3), 'BoxExtent': dict(X=4, Y=5, Z=6)})
        self.assertEqual(self.query.actor_bounds('actor'), Bounds((1., 2., 3.), (4., 5., 6.)))
        self.catalog.find_path.assert_called_once_with('/Script/Engine.Actor:GetActorBounds', 'Function')
        self.assertEqual(self.closed, 1)

    def test_projection_and_ray_copy_only_numbers(self):
        self.result({'ScreenLocation': dict(X=12, Y=24)}, True)
        self.assertEqual(self.query.project('controller', [1, 2, 3]), (12., 24.))
        self.assertEqual(self.planner.prepare.call_args.kwargs['WorldLocation'], dict(X=1., Y=2., Z=3.))
        self.result({'WorldLocation': dict(X=1, Y=2, Z=3), 'WorldDirection': dict(X=0, Y=1, Z=0)}, True)
        self.assertEqual(self.query.deproject('controller', (12, 24)), WorldRay((1., 2., 3.), (0., 1., 0.)))

    def test_failure_does_not_read_undefined_output(self):
        self.result({}, False)
        self.assertIsNone(self.query.project('controller', (1, 2, 3)))
        self.assertIsNone(self.query.deproject('controller', (1, 2)))
        self.assertEqual(self.closed, 2)

    def test_invalid_input_never_dispatches(self):
        for value in ((1, 2), (1, 2, float('nan')), (True, 2, 3), '123', (10 ** 1000, 2, 3)):
            with self.assertRaises(ValueError):
                self.query.project('controller', value)
        with self.assertRaises(ValueError):
            self.query.actor_bounds('actor', only_colliding=1)
        self.planner.prepare.assert_not_called()

    def test_invalid_engine_output_still_closes_lease(self):
        self.result({'Origin': dict(X=1, Y=2, Z=3), 'BoxExtent': dict(X=-1, Y=0, Z=1)})
        with self.assertRaises(ValueError):
            self.query.actor_bounds('actor')
        self.assertEqual(self.closed, 1)
        self.result({'ScreenLocation': dict(X=float('inf'), Y=1)}, True)
        with self.assertRaises(ValueError):
            self.query.project('controller', (1, 2, 3))
        self.assertEqual(self.closed, 2)

    def test_viewport_and_context_close(self):
        self.result(dict(SizeX=1920, SizeY=1080))
        with self.query:
            self.assertEqual(self.query.viewport_size('controller'), (1920, 1080))
        self.planner.close.assert_called_once_with()

    def test_native_error_propagates_without_retry(self):
        self.planner.prepare.side_effect = RuntimeError('stale target')
        with self.assertRaisesRegex(RuntimeError, 'stale target'):
            self.query.viewport_size('controller')
        self.assertEqual(self.planner.prepare.call_count, 1)
