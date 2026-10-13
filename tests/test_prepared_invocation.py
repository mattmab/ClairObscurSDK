import unittest
from unittest.mock import patch

import test_retained_results
import test_text_invocation
from expedition33 import RuntimeQueryError
from expedition33._scope import SessionScope
from expedition33.invocation import InvocationError


class PreparedRetainedTests(unittest.TestCase):
    setUp = test_retained_results.RetainedResultTests.setUp

    def test_explicit_catalog_avoids_scan_and_rejects_foreign_observation(self):
        from expedition33.catalog import Catalog
        from types import SimpleNamespace
        with patch('expedition33.catalog.capture', side_effect=AssertionError('unexpected scan')):
            with self.session.invocation_planner(catalog=self.p.catalog) as planner:
                planner.prepare(self.p.target, self.p.function)
                self.assertIs(planner._catalog, self.p.catalog)
            foreign = Catalog(self.session.pid + 1, (), ())
            for invalid in (foreign, SimpleNamespace(pid=self.session.pid)):
                with self.assertRaisesRegex(ValueError, 'catalog from this process'):
                    self.session.invocation_planner(catalog=invalid)
        self.assertFalse(self.transport.calls)

    def planner(self):
        with patch('expedition33.catalog.capture', return_value=self.p.catalog):
            planner = self.session.invocation_planner()
        self.addCleanup(planner.close)
        prepared = planner.prepare(self.p.target, self.p.function)
        return planner, prepared

    def test_selected_adoption_revokes_calls_but_preserves_checked_metadata(self):
        planner, prepared = self.planner()
        planner.adopt_observations(self.p.catalog)
        with self.assertRaisesRegex(RuntimeError, 'revoked'):
            prepared.invoke()
        with patch('expedition33.invocation.describe', side_effect=AssertionError('redundant describe')):
            planner.prepare(self.p.target, self.p.function)
        from expedition33.catalog import Catalog
        with self.assertRaises(ValueError):
            planner.adopt_observations(Catalog(self.session.pid+1, (), ()))

    def test_copied_observations_survive_close_without_reusing_old_scope(self):
        planner, prepared = self.planner()
        observations = planner.observations()
        planner.close()
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            prepared.invoke()
        with patch('expedition33.catalog.capture', side_effect=AssertionError('scan')), patch('expedition33.invocation.describe', side_effect=AssertionError('describe')):
            restored = self.session.invocation_planner(observations=observations)
            restored.prepare(self.p.target, self.p.function)
            restored.close()
        observations._session = lambda: object()
        with self.assertRaisesRegex(ValueError, 'same session'):
            self.session.invocation_planner(observations=observations)

    def test_restored_observations_do_not_bypass_native_rejection(self):
        planner, _ = self.planner()
        observations = planner.observations()
        planner.close()
        with self.session.invocation_planner(observations=observations) as restored:
            prepared = restored.prepare(self.p.target, self.p.function)
            self.transport.error, self.transport.outcome = 401, 0
            with self.assertRaises(InvocationError):
                prepared.invoke()
        self.assertEqual(self.transport.calls.count('retained-invoke'), 1)

    def test_object_results_still_capture_fresh_and_own_each_return(self):
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', return_value=self.p.catalog) as capture:
            first, second = prepared.invoke(), prepared.invoke()
        self.assertEqual(capture.call_count, 2)
        self.assertEqual(len(self.transport.tokens), 2)
        first.release(); self.assertTrue(second.active)
        second.release()

    def test_native_rejection_preserves_existing_lease_and_does_not_retry(self):
        planner, prepared = self.planner()
        owner = self.session.retain(self.p.target)
        self.transport.error, self.transport.outcome = 401, 0
        with self.assertRaises(InvocationError) as error: prepared.invoke()
        self.assertEqual(error.exception.outcome, 'not_dispatched')
        self.assertTrue(owner.active)
        self.assertEqual(self.transport.calls.count('retained-invoke'), 1)

    def test_unknown_ack_aborts_once_and_planner_can_close_after_fault(self):
        planner, prepared = self.planner()
        self.transport.malformed = True
        with self.assertRaises(InvocationError): prepared.invoke()
        self.assertEqual(self.transport.abort_count, 1)
        planner.close()
        self.assertIsNone(planner._catalog)
        with self.assertRaisesRegex(RuntimeError, 'closed'): prepared.invoke()

    def test_refresh_failure_revokes_plans_without_fallback(self):
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', side_effect=RuntimeQueryError('failed')):
            with self.assertRaises(RuntimeQueryError): planner.refresh()
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        self.assertEqual(self.transport.calls.count('retained-invoke'), 0)

    def test_successful_refresh_revokes_old_plans_before_transport(self):
        planner, prepared = self.planner()
        planner.refresh()
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        self.assertFalse(self.transport.calls)
        replacement = planner.prepare(self.p.target, self.p.function)
        with replacement.invoke() as result:
            self.assertEqual(result.return_value, self.p.target)

    def test_foreign_catalog_is_rejected_and_revokes_previous_plan(self):
        from types import SimpleNamespace
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', return_value=SimpleNamespace(pid=self.session.pid + 1)):
            with self.assertRaisesRegex(ValueError, 'another process'): planner.refresh()
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        self.assertFalse(self.transport.calls)

    def test_wrong_thread_cannot_dispatch_or_close_planner(self):
        import threading
        planner, prepared = self.planner()
        errors = []
        def worker():
            for operation in (prepared.invoke, planner.refresh, planner.close):
                try: operation()
                except RuntimeError as error: errors.append(str(error))
        thread = threading.Thread(target=worker)
        thread.start(); thread.join()
        self.assertEqual(len(errors), 3)
        self.assertFalse(self.transport.calls)
        self.assertFalse(planner._closed)

    def test_object_decode_failure_releases_only_new_result(self):
        planner, prepared = self.planner()
        existing = self.session.retain(self.p.target)
        with patch('expedition33.catalog.capture', side_effect=RuntimeQueryError('failed')):
            with self.assertRaises(InvocationError) as caught: prepared.invoke()
        self.assertEqual(caught.exception.outcome, 'dispatch_returned')
        self.assertTrue(existing.active)
        self.assertEqual(len(self.transport.tokens), 1)

    def test_creation_catalog_is_reused_without_second_scan_and_old_plans_revoked(self):
        from dataclasses import replace
        from expedition33.catalog import Catalog
        planner, prepared = self.planner()
        original = self.p.catalog
        created = replace(self.p.target, index=max(original.by_index) + 1,
                          address=self.p.target.address + 0x10000, name='Created')
        observed = Catalog(original.pid, (*original.objects, created), tuple(original.classes.values()))
        self.transport.obj = created
        self.assertNotIn(created.index, original.by_index)
        with patch('expedition33.catalog.capture', return_value=observed) as capture:
            result = prepared.invoke(refresh_from_result=True)
            self.assertEqual(result.return_value, created)
            self.assertIs(planner._catalog, observed)
            with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
            with patch('expedition33.invocation.prepare_call', return_value=prepared._plan) as prepare:
                planner.prepare(created, self.p.function)
                self.assertIs(prepare.call_args.args[0], observed)
                self.assertEqual(prepare.call_args.args[1], created)
            self.assertEqual(capture.call_count, 1)
        self.assertTrue(result.active)
        result.release()
        self.assertFalse(self.transport.tokens)

    def test_failed_result_refresh_leaves_no_catalog_and_does_not_repeat_dispatch(self):
        planner, prepared = self.planner()
        with patch('expedition33.catalog.capture', side_effect=RuntimeQueryError('capture failed')):
            with self.assertRaises(InvocationError): prepared.invoke(refresh_from_result=True)
        self.assertIsNone(planner._catalog)
        with self.assertRaisesRegex(RuntimeError, 'Refresh the planner'):
            planner.prepare(self.p.target, self.p.function)
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        self.assertEqual(self.transport.calls.count('retained-invoke'), 1)
        self.assertFalse(self.transport.tokens)

    def test_rejected_result_refresh_preserves_existing_owner_but_revokes_plans(self):
        planner, prepared = self.planner()
        owner = self.session.retain(self.p.target)
        self.transport.error, self.transport.outcome = 401, 0
        with self.assertRaises(InvocationError): prepared.invoke(refresh_from_result=True)
        self.assertTrue(owner.active)
        self.assertIsNone(planner._catalog)
        with self.assertRaisesRegex(RuntimeError, 'revoked'): prepared.invoke()
        self.assertEqual(self.transport.calls.count('retained-invoke'), 1)

    def test_scoped_prepared_results_share_existing_cleanup(self):
        scope = SessionScope(self.session)
        with patch('expedition33.catalog.capture', return_value=self.p.catalog):
            planner = scope.invocation_planner()
        self.addCleanup(planner.close)
        prepared = planner.prepare(self.p.target, self.p.function)
        result = prepared.invoke()
        scope.close()
        self.assertFalse(result.active)
        self.assertFalse(self.transport.tokens)
        with self.assertRaisesRegex(RuntimeError, 'scope is closed'): prepared.invoke()


class PreparedTextTests(unittest.TestCase):
    setUp = test_text_invocation.TextInvocationTests.setUp
    session = test_text_invocation.TextInvocationTests.session
    response = test_text_invocation.TextInvocationTests.response

    def test_rebind_text_reuses_one_catalog_and_preserves_original_arguments(self):
        session, transport, _ = self.session()
        with patch('expedition33.catalog.capture', return_value=self.p.catalog) as capture:
            with session.invocation_planner() as planner:
                original = planner.prepare(self.p.target, self.p.function, Input='first')
                updated = original.bind(Input='second')
                with patch('expedition33.catalog.capture', side_effect=AssertionError('unexpected full scan')):
                    with original.invoke() as result: self.assertEqual(result.return_value, 'Returned 🚀')
                    with updated.invoke() as result: self.assertEqual(result.return_value, 'Returned 🚀')
                self.assertEqual(original._plan.texts, (('Input', 'first'),))
                self.assertEqual(updated._plan.texts, (('Input', 'second'),))
            self.assertEqual(capture.call_count, 1)
        self.assertEqual(transport.calls, ['text-invoke', 'text-invoke'])

    def test_invalid_rebind_fails_before_dispatch(self):
        session, transport, _ = self.session()
        with patch('expedition33.catalog.capture', return_value=self.p.catalog):
            with session.invocation_planner() as planner:
                prepared = planner.prepare(self.p.target, self.p.function, Input='valid')
                with self.assertRaises(ValueError): prepared.bind(Input='bad\0text')
                self.assertFalse(transport.calls)


if __name__ == '__main__':
    unittest.main()
