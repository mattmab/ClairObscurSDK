import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.sdk import Session
from expedition33._scope import SessionScope
from expedition33.ownership import LeaseError
from expedition33.invocation import InvocationError, PARM, RETURN
from expedition33 import _invocation_wire as call, _retained_wire as wire
from expedition33.introspection import _Explorer
import test_invocation
from test_ownership import Transport


class RetainedTransport(Transport):
    def __init__(self, obj):
        super().__init__()
        self.start['pid'] = obj.pid
        self.obj = obj
        self.retained_protocol = 1
        self.error = 0
        self.outcome = 1
        self.null = False

    def command(self, command, packet=None):
        if command != 'retained-invoke': return super().command(command, packet)
        self._check_thread()
        self.calls.append(command)
        response = bytearray(packet)
        struct.pack_into('<II', response, 32, self.outcome, self.error)
        if self.outcome != 0 and not self.null:
            token = self.next; self.next += 1; self.tokens.add(token)
            struct.pack_into('<I', response, 28, 1)
            call.OBJECT.pack_into(response, call.OBJECTS_AT, 0, self.obj.index, self.obj.serial, self.obj.address)
            wire.HEADER.pack_into(response, call.SIZE, 1, 1)
            wire.LEASE.pack_into(response, wire.LEASES_AT, 0, token)
        return {'retained_packet': 'bad' if self.malformed else response.hex()}


class RetainedResultTests(unittest.TestCase):
    def setUp(self):
        p = self.p = test_invocation.InvocationTests(); p.setUp()
        cls = p.catalog.by_index[2]
        plan = p.plan([p.field('ReturnValue', 'ObjectProperty', 0, 8, PARM | RETURN,
            property_class_index=2, property_class_serial=cls.serial,
            property_class_name=cls.name, property_class_address=hex(cls.address))], {}, 8, 0)
        self.transport = RetainedTransport(p.target)
        for name, value in (('expedition33.sdk.SessionTransport', self.transport),
                            ('expedition33.catalog.capture', p.catalog),
                            ('expedition33.invocation.prepare_call', plan)):
            mock = patch(name, return_value=value)
            mock.start(); self.addCleanup(mock.stop)
        self.session = Session(retained=True)
        self.addCleanup(self.session.close)

    def invoke(self, session=None):
        return (session or self.session).invoke_retained(self.p.target, self.p.function)

    def test_owned_result_context_release_and_no_second_acquire(self):
        with self.invoke() as result:
            self.assertEqual(result.return_value, self.p.target)
            self.assertEqual(dict(result.outputs), {})
            self.assertEqual(self.transport.calls, ['retained-invoke'])
            self.assertEqual(len(self.session._leases), 1)
        self.assertFalse(result.active)
        self.assertTrue(result.release())
        with self.assertRaises(LeaseError): _ = result.return_value
        self.assertFalse(self.transport.tokens)

    def test_mod_scope_owns_only_its_result_and_revokes_null_result(self):
        a, b = SessionScope(self.session), SessionScope(self.session)
        first, second = self.invoke(a), self.invoke(b)
        self.transport.null = True
        null = self.invoke(a)
        self.assertIsNone(null.return_value)
        a.close()
        self.assertFalse(first.active); self.assertFalse(null.active)
        self.assertTrue(second.active)
        self.assertEqual(len(self.transport.tokens), 1)
        b.close()
        self.assertFalse(self.transport.tokens)

    def test_result_conversion_failure_releases_its_lease(self):
        existing = self.session.retain(self.p.target)
        with patch('expedition33.catalog.capture', side_effect=[self.p.catalog, RuntimeQueryError('catalog failed')]):
            with self.assertRaises(InvocationError) as caught: self.invoke()
        self.assertEqual(caught.exception.outcome, 'dispatch_returned')
        self.assertEqual(len(self.transport.tokens), 1)
        self.assertTrue(existing.active)

    def test_deferred_result_cleanup_is_polled(self):
        result = self.invoke()
        self.transport.defer = True
        self.assertFalse(result.release())
        self.assertFalse(result.active)
        self.assertEqual(len(self.transport.tokens), 1)
        self.transport.defer = False
        self.session.poll()
        self.assertFalse(self.transport.tokens)
        self.assertTrue(result.release())

    def test_unknown_or_malformed_ack_aborts_without_retry(self):
        self.transport.error = 405; self.transport.outcome = 2
        with self.assertRaises(InvocationError) as caught: self.invoke()
        self.assertEqual(caught.exception.outcome, 'unknown')
        self.assertEqual(self.transport.abort_count, 1)
        self.assertEqual(self.transport.calls, ['retained-invoke'])

    def test_malformed_success_aborts_owned_resources(self):
        existing = self.session.retain(self.p.target)
        self.transport.malformed = True
        with self.assertRaises(InvocationError) as caught: self.invoke()
        self.assertEqual(caught.exception.outcome, 'unknown')
        self.assertFalse(existing.active)
        self.assertEqual(self.transport.abort_count, 1)

    def test_predispatch_rejection_preserves_existing_owners(self):
        existing = self.session.retain(self.p.target)
        self.transport.error = 401; self.transport.outcome = 0
        with self.assertRaises(InvocationError) as caught: self.invoke()
        self.assertEqual(caught.exception.outcome, 'not_dispatched')
        self.assertTrue(existing.active)
        self.assertEqual(self.transport.abort_count, 0)

    def test_aliased_session_token_aborts_instead_of_double_owning(self):
        existing = self.session.retain(self.p.target)
        self.transport.next = existing._token
        with self.assertRaises(InvocationError): self.invoke()
        self.assertFalse(existing.active)
        self.assertEqual(self.transport.abort_count, 1)


class ExplorerRetainedTests(unittest.TestCase):
    def setUp(self):
        self.owners = []
        self.backend = SimpleNamespace(pending_owner=None, pending_value=object())
        self.explorer = _Explorer(self.backend)
        self.value = 42
        def invoke(**arguments):
            owner = SimpleNamespace(releases=0)
            def release(): owner.releases += 1; return True
            owner.release = release
            self.owners.append(owner)
            self.backend.pending_owner = owner
            self.backend.pending_value = arguments.get('Input', self.value)
            return self.backend.pending_value
        target = SimpleNamespace(Class=object(), Specimen=invoke)
        self.explorer.resolve = lambda _: target
        self.explorer.functions = lambda _: [SimpleNamespace(Name='Specimen')]
        self.explorer.encode = lambda value, *_: value
        self.addCleanup(self.explorer.close)

    def invoke(self, **extra):
        return self.explorer.dispatch(dict(op='invoke', allow_mutation=True, target='test', member='Specimen', **extra))

    def test_replacement_same_scalar_release_and_unretained(self):
        self.invoke(retain='item'); self.invoke(retain='item')
        self.assertEqual([o.releases for o in self.owners], [1, 0])
        self.explorer.dispatch({'op': 'release_value', 'name': 'item'})
        self.assertEqual([o.releases for o in self.owners], [1, 1])
        self.invoke()
        self.assertEqual(self.owners[-1].releases, 1)

    def test_original_value_argument_and_expiry(self):
        with patch('expedition33.introspection.core.time.monotonic', return_value=100):
            self.invoke(retain='item')
            self.assertEqual(self.invoke(args={'Input': {'$value': {'name': 'item'}}}), 42)
        with patch('expedition33.introspection.core.time.monotonic', return_value=161):
            self.explorer.expire()
        self.assertFalse(self.explorer.values)
        self.assertEqual(self.owners[0].releases, 1)

    def test_original_name_and_count_limits_prevent_dispatch(self):
        for name in ('', 'x' * 65, 3):
            with self.assertRaises(ValueError): self.invoke(retain=name)
        self.assertFalse(self.owners)
        for index in range(16): self.invoke(retain=str(index))
        with self.assertRaises(ValueError): self.invoke(retain='overflow')
        self.assertEqual(len(self.owners), 16)
        self.explorer.close()
        self.assertTrue(all(o.releases == 1 for o in self.owners))

    def test_encoding_error_keeps_explicit_retained_owner(self):
        with patch.object(self.explorer, 'encode', side_effect=ValueError('encode failed')):
            with self.assertRaises(ValueError): self.invoke(retain='item')
        self.assertEqual(self.owners[0].releases, 0)
        self.explorer.dispatch({'op': 'release_value', 'name': 'item'})
        self.assertEqual(self.owners[0].releases, 1)
