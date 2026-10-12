import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from expedition33.invocation import InvocationError

spec = importlib.util.spec_from_file_location('flight_mod_test', Path(__file__).resolve().parents[1] / 'mods/ContinentFlight/mod.py')
flight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flight)


class FlightCleanupTests(unittest.TestCase):
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
        mod.session = object()
        def attach(**_):
            mod.pawn = 'new-area-pawn'
            mod.calls = {'controlled': Mock()}
        mod._prepare = Mock(side_effect=attach)
        mod.poll()
        mod._prepare.assert_called_once_with(use_cache=False)
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
