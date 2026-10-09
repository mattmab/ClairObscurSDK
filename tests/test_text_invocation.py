import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33 import _text_wire as wire, _invocation_wire as call
from expedition33.invocation import prepare_call, decode_result, InvocationError, UnsupportedInvocation
from expedition33.sdk import Session
from expedition33._scope import SessionScope
import test_invocation
from test_ownership import Transport


class TextInvocationTests(unittest.TestCase):
    def setUp(self):
        self.p = test_invocation.InvocationTests(); self.p.setUp()
        self.rows = [self.p.field('Input', 'TextProperty', 0, 16),
                     self.p.field('ReturnValue', 'TextProperty', 16, 16, 0x480)]
        self.descriptor = SimpleNamespace(owners=[dict(index=7, size=32)], properties=self.rows,
            function=dict(params_size=32, return_offset=16, flags=0x400, entry_rva='0x1234'))
        mock = patch('expedition33.invocation.describe', return_value={7:self.descriptor})
        mock.start(); self.addCleanup(mock.stop)

    def plan(self, value='Hello 🚀', enabled=True):
        return prepare_call(self.p.catalog, self.p.target, self.p.function, {'Input':value}, text_values=enabled)

    def response(self, request):
        reply = bytearray(request)
        struct.pack_into('<II', reply, 32, 1, 0)
        encoded = wire.encode_units('Returned 🚀')
        at = wire.SLOTS_AT + wire.SLOT_SIZE
        wire.SLOT_HEADER.pack_into(reply, at, 1, len(encoded)//2)
        reply[at+8:at+8+len(encoded)] = encoded
        return reply

    def test_opt_in_inputs_and_scalar_ownership_layout(self):
        with self.assertRaises(UnsupportedInvocation): self.plan(enabled=False)
        plan = self.plan()
        self.assertEqual(plan.wire_version, 3)
        self.assertEqual(plan.texts, (('Input','Hello 🚀'),))
        self.assertEqual(plan.data, bytes(32))
        self.assertEqual(call.HEADER.unpack_from(wire.encode_plan(plan, dict(plan.texts)))[0], 3)
        for value in (None, b'a', 123, 'x\0y', '\ud800', 'x'*4096):
            with self.assertRaises(ValueError): self.plan(value)
        for field, value in (('dimension',2), ('element_size',8)):
            old = self.rows[0][field]; self.rows[0][field] = value
            with self.assertRaises(ValueError): self.plan()
            self.rows[0][field] = old

    def test_return_copy_requires_exact_correlated_texts_and_zero_native_bytes(self):
        plan = self.plan('')
        sent = wire.encode_plan(plan, dict(plan.texts))
        decoded = wire.decode_reply(sent, self.response(sent).hex())
        result = decode_result(plan, decoded.call, self.p.catalog, texts=decoded.texts)
        self.assertEqual(result.return_value, 'Returned 🚀')
        for texts in ((), ((1,'a'),), ((0,''),(1,'a'),(1,'b')), ((0,''),(1,'\ud800'))):
            with self.assertRaises(InvocationError):
                decode_result(plan, decoded.call, self.p.catalog, texts=texts)
        from dataclasses import replace
        with self.assertRaises(InvocationError):
            decode_result(plan, replace(decoded.call, data=b'X'+bytes(31)), self.p.catalog, texts=decoded.texts)

    def test_output_texts_and_nontext_calls_use_correct_versions(self):
        self.rows[0]['flags'] = 0x180
        plan = prepare_call(self.p.catalog, self.p.target, self.p.function, {}, text_values=True)
        self.assertEqual(plan.texts, ())
        self.assertEqual(wire.SLOT_HEADER.unpack_from(wire.encode_plan(plan, {}), wire.SLOTS_AT), (0,0))
        self.rows[:] = [self.p.field('Value', 'IntProperty', 0, 4)]
        self.descriptor.function['return_offset'] = 65535
        plan = prepare_call(self.p.catalog, self.p.target, self.p.function, {'Value':42}, text_values=True)
        self.assertEqual(plan.wire_version, 2)
        self.assertEqual(plan.texts, ())

    def session(self):
        transport = Transport()
        transport.start['pid'] = self.p.target.pid
        for name in ('retained_protocol','stable_identity_protocol','object_assignment_protocol',
                     'pod_value_protocol','text_value_protocol'):
            setattr(transport,name,1)
        original = transport.command
        def command(name, packet=None):
            if name != 'text-invoke': return original(name, packet)
            transport.calls.append(name)
            return {'text_packet': self.response(packet).hex()}
        transport.command = command
        mock = patch('expedition33.sdk.SessionTransport', return_value=transport)
        factory = mock.start(); self.addCleanup(mock.stop)
        mock = patch('expedition33.catalog.capture', return_value=self.p.catalog)
        mock.start(); self.addCleanup(mock.stop)
        session = Session(text_values=True)
        self.addCleanup(session.close)
        return session, transport, factory

    def test_public_session_and_scope_use_text_transport_and_release_copies(self):
        session, transport, factory = self.session()
        self.assertIn('research-probe-v12', str(factory.call_args.kwargs['_executable']))
        scope = SessionScope(session)
        self.assertTrue(scope.supports_text_values)
        with scope.invoke_retained(self.p.target,self.p.function,Input='') as result:
            copied = result.return_value
            self.assertEqual(copied,'Returned 🚀')
        self.assertEqual(transport.calls,['text-invoke'])
        self.assertEqual(copied,'Returned 🚀')
        self.assertFalse(session._leases)
        scope.close()

    def test_unknown_text_outcome_aborts_once_without_retry(self):
        session, transport, _ = self.session()
        def fault(request):
            reply = bytearray(request)
            struct.pack_into('<II',reply,32,2,708)
            return reply
        self.response = fault
        with self.assertRaises(InvocationError) as caught:
            session.invoke_retained(self.p.target,self.p.function,Input='x')
        self.assertEqual(caught.exception.outcome,'unknown')
        self.assertEqual(transport.calls,['text-invoke'])
        self.assertEqual(transport.abort_count,1)

    def test_missing_text_handshake_closes_candidate(self):
        _, transport, _ = self.session()
        transport.text_value_protocol = 0
        with self.assertRaisesRegex(RuntimeQueryError,'Text value backend handshake'):
            Session(text_values=True)
        self.assertTrue(transport._closed)
