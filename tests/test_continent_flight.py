import importlib.util
from pathlib import Path
from contextlib import nullcontext
from concurrent.futures import Future
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from expedition33.invocation import InvocationError

spec = importlib.util.spec_from_file_location('flight_mod_test', Path(__file__).resolve().parents[1] / 'mods/ContinentFlight/mod.py')
flight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flight)


class FlightCleanupTests(unittest.TestCase):
    def setUp(self):
        operation=patch.object(flight.Mod,'operation',side_effect=lambda:nullcontext())
        operation.start();self.addCleanup(operation.stop)
    def test_enable_waits_for_supported_pawn_but_propagates_other_errors(self):
        for error, deferred in ((flight.ExplorationNotReady('mounted'), True),
                                (RuntimeError('unknown dispatch'), False)):
            mod=flight.Mod();mod._prepare=Mock(side_effect=error)
            session=Mock(supports_vector_values=True)
            with patch.object(flight.ctypes,'WinDLL',return_value=Mock()):
                if deferred:
                    mod.enable(session)
                    self.assertFalse(mod.flying)
                    self.assertEqual(mod.error,'mounted')
                    session.console.expose.assert_called_once()
                else:
                    with self.assertRaisesRegex(RuntimeError,'unknown dispatch'):
                        mod.enable(session)
                    session.console.expose.assert_not_called()

    def test_toggle_restores_observed_area_movement_mode(self):
        for mode, custom in ((1, 0), (3, 0), (6, 2)):
            mod = flight.Mod()
            mod.planner = Mock()
            mod.movement = object()
            mod.movement_class = 42
            mod.pawn = 'area'
            exit_call = Mock()
            mod.calls = {'exit': exit_call}
            mod.invoke = Mock(return_value=True)
            mod.status = Mock()
            with patch.object(flight, 'read_values', return_value=Mock(values={
                    (42, 'MovementMode'): mode, (42, 'CustomMovementMode'): custom})):
                mod.toggle()
            exit_call.bind.assert_called_once_with(NewMovementMode=mode, NewCustomMode=custom)
            self.assertEqual(mod.restore_mode, (mode, custom))
            self.assertTrue(mod.flying)

    def test_destroyed_target_revokes_without_cleanup_calls(self):
        mod = flight.Mod()
        mod.flying = True
        mod.cached_observations = object()
        planner = mod.planner = Mock()
        call = Mock()
        call.invoke.side_effect = InvocationError('dead', outcome='not_dispatched', native_error=202)
        mod.calls = {'input': call}
        with self.assertRaises(InvocationError): mod.invoke('input')
        self.assertFalse(mod.flying)
        self.assertEqual(mod.calls, {})
        self.assertIsNone(mod.cached_observations)
        planner.close.assert_called_once()
        call.invoke.assert_called_once()

    def test_ambiguous_failure_does_not_discard_cleanup_owner(self):
        mod = flight.Mod()
        mod.flying = True
        planner = mod.planner = Mock()
        call = Mock()
        call.invoke.side_effect = InvocationError('unknown', outcome='unknown', native_error=202)
        mod.calls = {'input': call}
        with self.assertRaises(InvocationError): mod.invoke('input')
        self.assertTrue(mod.flying)

        planner.close.assert_not_called()

    def test_flight_binding_is_separate_from_jump(self):
        self.assertEqual(flight.Mod().management().keybinds[0].default, 'F6')

    def test_rediscovery_does_not_resume_flight(self):
        mod = flight.Mod()
        mod.session = SimpleNamespace(pid=123)
        future=Future();snapshot=object()
        mod.discovery_worker=Mock();mod.discovery_worker.submit.return_value=future
        def attach(*_):
            mod.pawn = 'new-area-pawn'
            mod.calls = {'controlled': Mock()}
        mod._prepare_calls = Mock(side_effect=attach)
        mod.poll()
        mod._prepare_calls.assert_not_called()
        future.set_result(snapshot);mod.poll()
        mod._prepare_calls.assert_called_once_with(None,snapshot)
        self.assertFalse(mod.flying)
        self.assertIsNone(mod.error)
        self.assertTrue(mod.calls)

    def test_unsupported_runtime_rejects_before_engine_setup(self):
        mod = flight.Mod()
        with self.assertRaisesRegex(RuntimeError, 'native Mods launcher'):
            mod.enable(object())
        mod.invoke = Mock(side_effect=AssertionError('Unexpected engine call'))
        mod.disable()
        mod.invoke.assert_not_called()

    def test_cleanup_does_not_query_vectors(self):
        mod = flight.Mod()
        mod.flying = True
        mod.invoke = Mock()
        planner = mod.planner = Mock()
        mod.status = Mock(side_effect=RuntimeError('Rejected diagnostic read'))
        mod.disable()
        self.assertEqual([c.args[0] for c in mod.invoke.call_args_list], ['stop', 'exit'])
        planner.close.assert_called_once()
        mod.status.assert_not_called()
        self.assertFalse(mod.flying)

    def test_actual_cleanup_failure_propagates_without_retry(self):
        mod = flight.Mod()
        mod.flying = True
        mod.invoke = Mock(side_effect=RuntimeError('Mutation failed'))
        planner = mod.planner = Mock()
        with self.assertRaisesRegex(RuntimeError, 'Mutation failed'):
            mod.disable()
        mod.invoke.assert_called_once_with('stop')
        planner.close.assert_called_once()
        self.assertTrue(mod.flying)


class FlightReaderTests(unittest.TestCase):
    def test_pending_discovery_never_blocks_or_stacks_jobs(self):
        mod=flight.Mod();mod.session=SimpleNamespace(pid=123)
        pending=Future();mod.discovery_worker=Mock();mod.discovery_worker.submit.return_value=pending
        mod._prepare_calls=Mock()
        mod.poll();mod.next_discovery=0;mod.poll();mod.poll()
        mod.discovery_worker.submit.assert_called_once_with(flight.discover_worker,123)
        mod._prepare_calls.assert_not_called();self.assertFalse(pending.done())
        mod.disable();self.assertTrue(pending.cancelled())

    def test_disable_discards_running_discovery_and_prevents_late_adoption(self):
        mod=flight.Mod();mod.session=SimpleNamespace(pid=123)
        future=Future();future.set_running_or_notify_cancel()
        worker=mod.discovery_worker=Mock();worker.submit.return_value=future
        mod._prepare_calls=Mock();mod.poll();mod.disable()
        future.set_result(object());mod.poll()
        mod._prepare_calls.assert_not_called();self.assertIsNone(mod.discovery_future)
        worker.shutdown.assert_called_once_with(wait=False,cancel_futures=True)

    def test_explicit_refresh_generation_discards_old_discovery(self):
        mod=flight.Mod();mod.session=SimpleNamespace(pid=123)
        mod.discovery_future=Future();mod.discovery_future.set_result(object())
        mod.discovery_pending_generation=0;mod.discovery_generation=1
        mod._prepare_calls=Mock();mod.poll()
        mod._prepare_calls.assert_not_called();self.assertIsNone(mod.discovery_future)

    def test_read_worker_closes_its_context_on_unavailable_pawn(self):
        reader=Mock();reader.__enter__=Mock();reader.__exit__=Mock(return_value=False)
        with patch.object(flight,'ReadBatch',return_value=reader),patch.object(flight,'discover_snapshot',side_effect=flight.ExplorationNotReady('mounted')):
            with self.assertRaises(flight.ExplorationNotReady):flight.discover_worker(123)
        reader.__enter__.assert_called_once();reader.__exit__.assert_called_once()

    def test_supported_pawn_absence_keeps_reader_for_next_fresh_discovery(self):
        mod,call=self.editor();reader=Mock();reader.bind.side_effect=lambda:nullcontext()
        mod._prepare_calls=Mock(side_effect=flight.ExplorationNotReady('mounted'))
        with patch.object(flight,'active_reader',return_value=None),patch.object(flight,'ReadBatch',return_value=reader) as create:
            for _ in range(2):
                with self.assertRaises(flight.ExplorationNotReady):mod._prepare(use_cache=False)
        create.assert_called_once_with(123,share=True)
        self.assertEqual(mod._prepare_calls.call_count,2)
        reader.close.assert_not_called();self.assertIs(mod.reader,reader)
        mod.disable();reader.close.assert_called_once()

    def editor(self):
        mod=flight.Mod();mod.session=SimpleNamespace(pid=123)
        call=Mock();call.invoke.side_effect=lambda:nullcontext(SimpleNamespace(return_value=True))
        mod.calls={'controlled':call}
        return mod,call

    def test_repeated_invocations_reuse_worker_but_invoke_fresh_guards(self):
        mod,call=self.editor();reader=Mock();reader.bind.side_effect=lambda:nullcontext()
        with patch.object(flight,'active_reader',return_value=None),patch.object(flight,'ReadBatch',return_value=reader) as create:
            self.assertTrue(mod.invoke('controlled'));self.assertTrue(mod.invoke('controlled'))
        create.assert_called_once_with(123,share=True)
        self.assertEqual(reader.bind.call_count,2);self.assertEqual(call.invoke.call_count,2)
        reader.close.assert_not_called()
        mod.disable();reader.close.assert_called_once();self.assertIsNone(mod.reader)

    def test_failed_invocation_disposes_worker_without_retry(self):
        mod,call=self.editor();reader=Mock();reader.bind.side_effect=lambda:nullcontext()
        call.invoke.side_effect=InvocationError('uncertain',outcome='unknown',native_error=202)
        with patch.object(flight,'active_reader',return_value=None),patch.object(flight,'ReadBatch',return_value=reader):
            with self.assertRaises(InvocationError):mod.invoke('controlled')
        call.invoke.assert_called_once();reader.close.assert_called_once();self.assertIsNone(mod.reader)
        self.assertTrue(mod.calls)  # Preserve the engine cleanup owner on ambiguous dispatch.

    def test_active_shared_reader_is_borrowed_without_retaining_or_closing_it(self):
        mod,call=self.editor();parent=Mock()
        with patch.object(flight,'active_reader',return_value=parent),patch.object(flight,'ReadBatch',return_value=nullcontext()) as create:
            mod.invoke('controlled')
        create.assert_called_once_with(123)
        self.assertIsNone(mod.reader);parent.close.assert_not_called();call.invoke.assert_called_once()

    def test_target_revocation_closes_persistent_worker(self):
        mod,call=self.editor();reader=mod.reader=Mock();mod.planner=Mock()
        mod._forget_target('travel')
        reader.close.assert_called_once();self.assertIsNone(mod.reader)
        call.invoke.assert_not_called();self.assertFalse(mod.calls)
