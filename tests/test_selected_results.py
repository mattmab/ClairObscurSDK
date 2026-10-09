from dataclasses import replace
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33._scope import SessionScope
from expedition33.invocation import InvocationError
import test_retained_results


class SelectedResultTests(unittest.TestCase):
    setUp = test_retained_results.RetainedResultTests.setUp

    def planner(self, scope=None):
        planner = (scope or self.session).invocation_planner(selected_results=True)
        self.addCleanup(planner.close)
        return planner, planner.prepare(self.p.target, self.p.function)

    def test_new_result_extends_observations_without_recapturing_untouched_rows(self):
        old = self.p.catalog
        created = replace(self.p.target, index=8, address=0x20000, name='NewWidget')
        closure = Catalog(old.pid, [o for o in old.objects if o.index not in (5,7)] + [created],
                          tuple(old.classes.values()))
        self.transport.obj = created
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', side_effect=AssertionError('full scan forbidden')), \
                patch('expedition33.catalog.capture_selected', return_value=closure) as selected:
            result = prepared.invoke(refresh_from_result=True)
        selected.assert_called_once_with(old.pid, ((8, created.serial, created.address),))
        self.assertEqual(result.return_value, created)
        self.assertNotIn(8, old.by_index)
        self.assertIs(planner._catalog.by_index[7], old.by_index[7])
        self.assertIs(planner._catalog.by_index[8], created)
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        result.release(); self.assertFalse(self.transport.tokens)

    def test_selected_capture_failure_releases_new_lease_and_revokes_refresh(self):
        planner, prepared = self.planner()
        existing = self.session.retain(self.p.target)
        with patch('expedition33.catalog.capture_selected', side_effect=RuntimeQueryError('changed')), \
                patch('expedition33.catalog.capture', side_effect=AssertionError('fallback forbidden')):
            with self.assertRaises(InvocationError) as caught: prepared.invoke(refresh_from_result=True)
        self.assertEqual(caught.exception.outcome, 'dispatch_returned')
        self.assertIsNone(planner._catalog)
        self.assertTrue(existing.active)
        self.assertEqual(len(self.transport.tokens), 1)
        self.assertEqual(self.transport.calls.count('retained-invoke'), 1)

    def test_recycled_overlap_fails_combination_and_releases_output(self):
        old = self.p.catalog
        recycled = replace(self.p.target, serial=self.p.target.serial + 1)
        closure = Catalog(old.pid, [recycled if o.index == recycled.index else o for o in old.objects],
                          tuple(old.classes.values()))
        self.transport.obj = recycled
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture_selected', return_value=closure):
            with self.assertRaises(InvocationError): prepared.invoke(refresh_from_result=True)
        self.assertFalse(self.transport.tokens)
        self.assertIsNone(planner._catalog)

    def test_changed_class_relation_requires_full_refresh(self):
        old = self.p.catalog
        changed = Catalog(old.pid, old.objects,
            [replace(cls, size=cls.size + 8) if cls.index == 2 else cls for cls in old.classes.values()])
        with self.assertRaisesRegex(RuntimeQueryError, 'class relation changed'):
            old.with_observations(changed)
        self.assertNotEqual(old.classes[2], changed.classes[2])

    def test_selected_scope_cleanup_and_null_return_no_query(self):
        scope = SessionScope(self.session)
        planner, prepared = self.planner(scope)
        with patch('expedition33.catalog.capture_selected', return_value=self.p.catalog) as selected:
            result = prepared.invoke()
            self.transport.null = True
            null = prepared.invoke()
        self.assertEqual(selected.call_count, 1)
        self.assertIsNone(null.return_value)
        scope.close()
        self.assertFalse(result.active)
        self.assertFalse(null.active)
        self.assertFalse(self.transport.tokens)

    def test_non_boolean_opt_in_rejected_before_capture(self):
        with patch('expedition33.catalog.capture') as capture:
            with self.assertRaises(ValueError): self.session.invocation_planner(selected_results=1)
            capture.assert_not_called()

    def test_explicit_observation_adoption_revokes_plans_without_another_read(self):
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', side_effect=AssertionError('extra scan')):
            planner.refresh_from(self.p.catalog)
        self.assertIs(planner._catalog, self.p.catalog)
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        replacement = planner.prepare(self.p.target, self.p.function)
        with self.assertRaises(ValueError): planner.refresh_from(object())
        self.assertIsNone(planner._catalog)
        with self.assertRaisesRegex(RuntimeError, 'revoked'): replacement.invoke()
        self.assertFalse(self.transport.calls)


if __name__ == '__main__': unittest.main()
