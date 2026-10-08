"""Python delivery semantics only: these tests do not stand in for game evidence."""
import gc
import threading
import unittest
import weakref

from expedition33._callbacks import CallbackDispatcher, ObservedIdentity, ObserverContext


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.dispatcher = CallbackDispatcher()
        self.event = ObserverContext(1, 'fixture.getter',
            ObservedIdentity(1, 2, 3, 'fixture', 'Fixture'), 4, False)

    def test_exception_disables_only_faulty_callback(self):
        seen = []
        def bad(_):
            raise SystemExit('mod asked to exit')
        bad_handle = self.dispatcher.subscribe(self.event.target, bad)
        good_handle = self.dispatcher.subscribe(self.event.target, seen.append)
        self.assertEqual(self.dispatcher.deliver(self.event), 2)
        self.assertFalse(bad_handle.active)
        self.assertTrue(good_handle.active)
        self.assertEqual(self.dispatcher.deliver(self.event), 1)
        self.assertEqual(seen, [self.event, self.event])
        self.assertEqual(self.dispatcher.failures()[0].exception_type, 'SystemExit')

    def test_removal_and_registration_during_delivery(self):
        seen = []
        def first(event):
            second.remove()
            first_handle.remove()
            self.dispatcher.subscribe(event.target, seen.append)
        first_handle = self.dispatcher.subscribe(self.event.target, first)
        second = self.dispatcher.subscribe(self.event.target, seen.append)
        self.assertEqual(self.dispatcher.deliver(self.event), 1)
        self.assertEqual(seen, [])
        self.assertEqual(self.dispatcher.deliver(self.event), 1)
        self.assertEqual(seen, [self.event])
        second.remove()

    def test_recursive_delivery_is_contained(self):
        handle = self.dispatcher.subscribe(self.event.target, self.dispatcher.deliver)
        self.assertEqual(self.dispatcher.deliver(self.event), 1)
        self.assertFalse(handle.active)
        self.assertIn('Recursive', self.dispatcher.failures()[0].message)

    def test_close_releases_callback_and_stops_current_batch(self):
        class Mod:
            def callback(self, _):
                self.fail = True
        mod = Mod()
        reference = weakref.ref(mod)
        self.dispatcher.subscribe(self.event.target, lambda _: self.dispatcher.close())
        handle = self.dispatcher.subscribe(self.event.target, mod.callback)
        del mod
        self.assertIsNotNone(reference())
        self.assertEqual(self.dispatcher.deliver(self.event), 1)
        gc.collect()
        self.assertIsNone(reference())
        self.assertFalse(handle.active)
        self.assertEqual(self.dispatcher.deliver(self.event), 0)
        self.dispatcher.close()
        with self.assertRaises(RuntimeError):
            self.dispatcher.subscribe(self.event.target, print)

    def test_repeated_enable_disable_no_duplicate_delivery(self):
        seen = []
        for _ in range(1000):
            with self.dispatcher.subscribe(self.event.target, seen.append):
                self.assertEqual(self.dispatcher.deliver(self.event), 1)
            self.assertEqual(self.dispatcher.deliver(self.event), 0)
        self.assertEqual(len(seen), 1000)

    def test_wrong_thread_rejected(self):
        errors = []
        def worker():
            try:
                self.dispatcher.deliver(self.event)
            except RuntimeError as error:
                errors.append(str(error))
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        self.assertEqual(len(errors), 1)

    def test_diagnostics_bounded_and_hostile_exception_formatting(self):
        class BadError(Exception):
            def __str__(self):
                raise RuntimeError('bad formatter')
        def bad(_):
            raise BadError()
        for _ in range(70):
            self.dispatcher.subscribe(self.event.target, bad)
            self.dispatcher.deliver(self.event)
        self.assertEqual(self.dispatcher.failure_count, 70)
        self.assertEqual(len(self.dispatcher.failures()), 64)
        self.assertEqual(self.dispatcher.failures()[0].message, '<exception formatting failed>')


if __name__ == '__main__':
    unittest.main()
