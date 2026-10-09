import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from expedition33 import RuntimeQueryError
from expedition33.sdk import Session
from expedition33.assignment import assign
from expedition33 import _assignment_wire as wire
from expedition33.invocation import InvocationError
from expedition33.catalog import Catalog
from test_catalog import fixture
from test_ownership import Transport


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        objects, classes = fixture()
        self.catalog = Catalog(123, objects, classes)
        self.obj, self.owner = self.catalog.by_index[5], self.catalog.by_index[2]
        self.prop = dict(name='Child', owner_index=2, type='ObjectProperty', element_size=8,
                         vtable_rva='0x6e11d38', dimension=1, offset=48, flags=0, property_class_index=2)

    def request(self):
        return wire.request(self.obj, self.owner, self.owner, None, self.obj, self.prop, 0, (11, 0, 12))

    def response(self, sent, error=0, outcome=1):
        data = bytearray(sent)
        struct.pack_into('<I', data, 4, error)
        struct.pack_into('<I', data, 228, outcome)
        return data.hex()

    def test_wire_rejects_forged_success_and_changed_identity(self):
        sent = self.request()
        self.assertEqual(wire.decode(sent, self.response(sent)), (0, 'dispatch_returned'))
        for error, outcome in ((0, 0), (0, 2), (4, 1), (5, 0), (99, 0)):
            with self.assertRaises(ValueError): wire.decode(sent, self.response(sent, error, outcome))
        changed = bytearray.fromhex(self.response(sent)); changed[40] ^= 1
        with self.assertRaises(ValueError): wire.decode(sent, changed.hex())

    def test_capability_required_and_old_backend_unchanged(self):
        transport = Transport()
        transport.retained_protocol = transport.stable_identity_protocol = 1
        with patch('expedition33.sdk.SessionTransport', return_value=transport):
            with self.assertRaisesRegex(RuntimeQueryError, 'handshake'): Session(object_assignment=True)
        self.assertTrue(transport._closed)
        transport = Transport()
        transport.retained_protocol = transport.stable_identity_protocol = transport.object_assignment_protocol = 1
        with patch('expedition33.sdk.SessionTransport', return_value=transport) as factory:
            with Session(object_assignment=True) as session:
                self.assertTrue(session.supports_object_assignment)
                self.assertIn('research-probe-v10', str(factory.call_args.kwargs['_executable']))

    def exercise(self, mode, *, cached=False):
        session = Mock(pid=123, supports_object_assignment=True)
        leases = [Mock(active=True, _token=11), Mock(active=True, _token=12)]
        session.retain.side_effect = leases
        def abort():
            for lease in leases: lease.active = False
        session._abort_ownership.side_effect = abort
        def command(_name, sent):
            return {'assignment_packet': self.response(sent, 4, 0) if mode == 'stale' else
                    'bad' if mode == 'bad' else self.response(sent)}
        session._transport.command.side_effect = command
        with patch('expedition33.assignment.capture', return_value=self.catalog) as capture, \
             patch('expedition33.assignment.describe', return_value={2:SimpleNamespace(properties=[self.prop])}):
            if mode == 'ok':
                result = assign(session, self.obj, self.owner, 'Child', self.obj,
                                expected=None, element=0, allow_mutation=True,
                                catalog=self.catalog if cached else None)
                self.assertEqual(result.after, self.obj)
            else:
                with self.assertRaises(InvocationError) as caught:
                    assign(session, self.obj, self.owner, 'Child', self.obj,
                           expected=None, element=0, allow_mutation=True,
                           catalog=self.catalog if cached else None)
                self.assertEqual(caught.exception.outcome, 'unknown' if mode == 'bad' else 'not_dispatched')
        self.assertEqual(capture.call_count, 0 if cached else 1)
        self.assertEqual(session._transport.command.call_count, 1)
        if mode == 'bad':
            session._abort_ownership.assert_called_once()
            for lease in leases: lease.release.assert_not_called()
        else:
            session._abort_ownership.assert_not_called()
            for lease in leases: lease.release.assert_called_once()

    def test_success_releases_temporary_owners(self): self.exercise('ok')
    def test_planning_catalog_preserves_success_rejection_and_unknown_outcome(self):
        for mode in ('ok', 'stale', 'bad'): self.exercise(mode, cached=True)

    def test_foreign_catalog_cannot_acquire_or_dispatch(self):
        session = Mock(pid=123, supports_object_assignment=True)
        with self.assertRaisesRegex(ValueError, 'catalog from this process'):
            assign(session, self.obj, self.owner, 'Child', self.obj, expected=None,
                   element=0, allow_mutation=True, catalog=Catalog(124, (), ()))
        session.retain.assert_not_called()
        session._transport.command.assert_not_called()
    def test_changed_old_value_is_not_retried(self): self.exercise('stale')
    def test_malformed_ack_aborts_ownership_without_retry(self): self.exercise('bad')
    def test_explicit_mutation_required_before_io(self):
        session = Mock()
        for flag in (False, 1, 'true'):
            with self.assertRaises(ValueError):
                assign(session, self.obj, self.owner, 'Child', self.obj,
                       expected=None, element=0, allow_mutation=flag)
        session.retain.assert_not_called()
