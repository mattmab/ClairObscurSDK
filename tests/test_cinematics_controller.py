import threading
import unittest
from unittest.mock import Mock
from expedition33.cinematics.controller import (
    ReplayController, ReplayBusy, ReplayObservation, BackendState,
    ControllerState, StartResult, StopResult,
)


EPOCH = ((1, 2, 0x10000), (3, 4, 0x20000))
OTHER = ((9, 8, 0x90000), (7, 6, 0x80000))


class Adapter:
    def __init__(self):
        self.start_result = StartResult.STARTED
        self.observation = ReplayObservation(BackendState.ACTIVE)
        self.stop_result = StopResult.STOPPED
        self.cleanup = [True]
        self.events = []
        self.requests = []
        self.start_hook = None

    def event(self, name):
        self.events.append((name, threading.get_ident()))

    def start(self):
        self.event('start')
        if self.start_hook:
            self.start_hook()
        return self.start_result

    def poll(self):
        self.event('poll')
        if isinstance(self.observation, Exception):
            raise self.observation
        return self.observation

    def status(self):
        return self.observation

    def stop(self):
        self.event('stop')
        return self.stop_result

    def close(self, request):
        self.event('close')
        self.requests.append(request)
        result = self.cleanup.pop(0) if len(self.cleanup) > 1 else self.cleanup[0]
        if isinstance(result, Exception):
            raise result
        return result

    def calls(self, name):
        return sum(event == name for event, _ in self.events)


class ReplayControllerTests(unittest.TestCase):
    def started(self, *, engine_owned=False):
        c, a = ReplayController(), Adapter()
        c.queue('selected', lambda: a, EPOCH, engine_owned=engine_owned)
        c.poll(EPOCH)
        return c, a

    def test_queued_preparation_waits_for_ui_ack_and_is_one_shot(self):
        c, a = ReplayController(), Adapter()
        factory = Mock(return_value=a)
        self.assertEqual(c.queue('scene', factory, EPOCH, intent_id=44), 1)
        c.poll(EPOCH, presentation_ready=False)
        factory.assert_not_called()
        self.assertFalse(a.events)
        c.poll(EPOCH)
        for _ in range(3):
            c.poll(EPOCH)
        factory.assert_called_once()
        self.assertEqual(a.calls('start'), 1)
        self.assertEqual(c.status().intent_id, 44)

    def test_cancel_queue_performs_no_native_operation(self):
        c = ReplayController()
        factory = Mock()
        c.queue('scene', factory, EPOCH)
        self.assertTrue(c.request_stop(EPOCH))
        c.poll(EPOCH)
        factory.assert_not_called()
        self.assertFalse(c.status().busy)

    def test_queued_epoch_replacement_never_constructs(self):
        c = ReplayController()
        factory = Mock()
        c.queue('scene', factory, EPOCH)
        c.poll(OTHER)
        factory.assert_not_called()
        self.assertFalse(c.status().busy)

    def test_cleanup_false_retains_owner_and_blocks_replace_disable(self):
        c, a = self.started()
        a.cleanup = [False, False, True]
        self.assertFalse(c.close(EPOCH))
        with self.assertRaises(ReplayBusy):
            c.queue('replacement', Adapter, EPOCH)
        self.assertTrue(c.status().enabled)
        c.poll(EPOCH)
        self.assertTrue(c.status().busy)
        c.poll(EPOCH)
        self.assertEqual(c.status().state, ControllerState.DISABLED)
        self.assertEqual(a.calls('stop'), 1)

    def test_unknown_start_is_never_retried(self):
        c, a = ReplayController(), Adapter()
        a.start_result = StartResult.UNKNOWN
        c.queue('scene', lambda: a, EPOCH)
        for _ in range(4):
            c.poll(EPOCH)
        self.assertEqual(a.calls('start'), 1)
        self.assertEqual(a.calls('poll'), 0)
        self.assertEqual(c.status().state, ControllerState.UNCERTAIN)
        with self.assertRaises(ReplayBusy):
            c.queue('replacement', Adapter, EPOCH)

    def test_rejected_start_preserves_deferred_cleanup(self):
        c, a = ReplayController(), Adapter()
        a.start_result = StartResult.REJECTED
        a.cleanup = [False, True]
        c.queue('scene', lambda: a, EPOCH)
        c.poll(EPOCH)
        self.assertTrue(c.status().busy)
        c.poll(EPOCH)
        self.assertFalse(c.status().busy)
        self.assertEqual(a.calls('start'), 1)

    def test_unknown_cleanup_never_retries_even_after_epoch_change(self):
        c, a = self.started()
        a.cleanup = [RuntimeError('lost acknowledgement')]
        self.assertFalse(c.close(EPOCH))
        for epoch in (EPOCH, OTHER, EPOCH):
            c.poll(epoch)
        self.assertEqual(a.calls('close'), 1)
        self.assertTrue(c.status().busy)

    def test_original_engine_playback_is_observed_not_stopped(self):
        c, a = self.started(engine_owned=True)
        self.assertFalse(c.request_stop(EPOCH))
        self.assertEqual(c.status().state, ControllerState.OBSERVING)
        c.poll(EPOCH)
        self.assertEqual(a.calls('stop'), 0)
        self.assertEqual(a.calls('close'), 0)
        a.observation = ReplayObservation(BackendState.COMPLETE)
        c.poll(EPOCH)
        self.assertFalse(c.status().busy)
        self.assertEqual(a.calls('stop'), 0)

    def test_engine_disable_waits_for_original_completion(self):
        c, a = self.started(engine_owned=True)
        self.assertFalse(c.close(EPOCH))
        a.observation = ReplayObservation(BackendState.COMPLETE)
        c.poll(EPOCH)
        self.assertFalse(c.status().enabled)
        self.assertEqual(a.calls('stop'), 0)

    def test_epoch_revocation_never_compensates_old_world(self):
        c, a = self.started(engine_owned=True)
        a.cleanup = [False, False, True]
        c.poll(OTHER)
        c.poll(EPOCH)  # Even the old token reappearing cannot resurrect admission.
        self.assertTrue(c.status().busy)
        c.poll(EPOCH)
        self.assertFalse(c.status().busy)
        self.assertEqual(a.calls('stop'), 0)
        self.assertTrue(all(request.epoch_valid is False for request in a.requests))

    def test_ordinary_poll_failure_retains_until_explicit_cleanup_ack(self):
        c, a = self.started()
        a.observation = ValueError('backend failed')
        a.cleanup = [False, True]
        c.poll(EPOCH)
        self.assertTrue(c.status().busy)
        c.poll(EPOCH)
        self.assertFalse(c.status().busy)

    def test_original_poll_failure_does_not_detach_running_campaign(self):
        c, a = self.started(engine_owned=True)
        a.observation = ValueError('status unavailable')
        c.poll(EPOCH)
        self.assertEqual(c.status().state, ControllerState.UNCERTAIN)
        self.assertEqual(a.calls('close'), 0)
        self.assertFalse(c.close(EPOCH))
        self.assertEqual(a.calls('stop'), 0)

    def test_uncertain_original_can_finish_by_readonly_terminal_observation(self):
        c, a = self.started(engine_owned=True)
        a.observation = ReplayObservation(BackendState.UNKNOWN)
        c.poll(EPOCH)
        self.assertFalse(c.close(EPOCH))
        a.observation = ReplayObservation(BackendState.COMPLETE)
        c.poll(EPOCH)
        self.assertFalse(c.status().busy)
        self.assertFalse(c.status().enabled)
        self.assertEqual(a.calls('start'), 1)
        self.assertEqual(a.calls('stop'), 0)

    def test_untyped_outcomes_never_count_as_confirmation(self):
        c, a = self.started()
        a.cleanup = [Mock()]
        self.assertFalse(c.close(EPOCH))
        self.assertEqual(c.status().state, ControllerState.UNCERTAIN)
        self.assertTrue(c.status().busy)

    def test_selection_intent_cannot_replay_after_cleanup(self):
        c, a = ReplayController(), Adapter()
        c.queue('one', lambda: a, EPOCH, intent_id=20)
        c.request_stop(EPOCH)
        with self.assertRaises(ValueError):
            c.queue('same intent', Adapter, EPOCH, intent_id=20)
        self.assertEqual(c.queue('new intent', Adapter, EPOCH, intent_id=21), 2)

    def test_all_callbacks_are_owner_thread_and_foreign_calls_do_nothing(self):
        c, a = self.started()
        failures = []
        def foreign():
            try:
                c.poll(EPOCH)
            except RuntimeError as error:
                failures.append(str(error))
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join()
        self.assertEqual(len(failures), 1)
        self.assertEqual(a.calls('poll'), 0)
        self.assertTrue(all(ident == threading.get_ident() for _, ident in a.events))

    def test_reentrant_start_cannot_replace_its_owner(self):
        c, a = ReplayController(), Adapter()
        a.start_hook = lambda: c.queue('reentrant', Adapter, EPOCH)
        c.queue('scene', lambda: a, EPOCH)
        c.poll(EPOCH)
        self.assertEqual(c.status().state, ControllerState.UNCERTAIN)
        self.assertEqual(c.status().selection_id, 'scene')
        self.assertEqual(a.calls('start'), 1)
