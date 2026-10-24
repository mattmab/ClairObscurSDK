import dataclasses
import threading
import unittest
from types import SimpleNamespace
from expedition33.capabilities import _snapshot
from expedition33.sdk import Session
from expedition33._scope import SessionScope


class CapabilityTests(unittest.TestCase):
    def session(self, **values):
        session = object.__new__(Session)
        session._closed = False
        session._transport = SimpleNamespace(_check_thread=lambda: None, **values)
        return session

    def test_exact_versions_missing_disabled_and_invalid(self):
        snap = self.session(mesh_protocol=3, lease_protocol=0,
                            text_value_protocol=True).capabilities
        self.assertTrue(snap.matches('mesh_protocol', 3))
        self.assertFalse(snap.matches('mesh_protocol', 1))
        self.assertEqual(snap.protocol('lease_protocol').state, 'disabled')
        self.assertEqual(snap.protocol('text_value_protocol').state, 'invalid')
        self.assertEqual(snap.protocol('unknown_protocol').state, 'missing')
        self.assertFalse(snap.matches('text_value_protocol', 1))
        for value in (True, 0, -1, 2**32, '1'):
            with self.assertRaises(ValueError):
                snap.matches('mesh_protocol', value)
        for name in ('mesh', '_private_protocol', 'a.protocol', 1):
            with self.assertRaises(ValueError):
                snap.protocol(name)

    def test_snapshot_copies_only_protocols(self):
        session = self.session(mesh_protocol=3, nonce='secret', _private_protocol=1)
        snap = session.capabilities
        session._transport.mesh_protocol = 0
        self.assertEqual(len(snap.protocols), 1)
        self.assertTrue(snap.matches('mesh_protocol', 3))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snap.protocols[0].version = 0

    def test_bad_advertisements_are_sanitized(self):
        for value in (-1, 2**32, 1.0, '1', None, object()):
            snap = _snapshot(SimpleNamespace(mesh_protocol=value))
            self.assertEqual(snap.protocol('mesh_protocol').state, 'invalid')
            self.assertIsNone(snap.protocol('mesh_protocol').version)

    def test_no_properties_are_evaluated(self):
        class Transport:
            mesh_protocol = property(lambda self: self.fail())
            def fail(self):
                raise AssertionError('Descriptor evaluated')
        self.assertEqual(_snapshot(Transport()).protocol('mesh_protocol').state, 'missing')

    def test_scope_lifetime_owner_and_retained_copy(self):
        session = self.session(mesh_protocol=3)
        scope = SessionScope(session)
        snap = scope.capabilities
        errors = []
        def other_thread():
            try:
                scope.capabilities
            except RuntimeError as error:
                errors.append(str(error))
        thread = threading.Thread(target=other_thread)
        thread.start(); thread.join()
        self.assertEqual(len(errors), 1)
        child = SessionScope(scope)
        scope._closed = True
        with self.assertRaises(RuntimeError):
            child.capabilities
        with self.assertRaises(RuntimeError):
            scope.capabilities
        self.assertTrue(snap.matches('mesh_protocol', 3))
        session._closed = True
        with self.assertRaises(RuntimeError):
            session.capabilities
