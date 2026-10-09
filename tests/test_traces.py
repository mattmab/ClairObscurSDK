import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33 import _trace_wire as wire
from expedition33._traces import Trace, TraceError
from expedition33.sdk import Session
import test_multi_button_transport as multi
import test_tracing as schemas


class TraceTests(unittest.TestCase):
    def fixture(self):
        schema = schemas.TraceSchemaTests(); schema.setUp()
        plan = schema.plan([schema.fixture.field('Return', 'IntProperty', 0, 4, 0x480)], 4, 0)
        transport = SimpleNamespace(start={'game_thread_id': 8}, _closed=False)
        session = SimpleNamespace(pid=99, _transport=transport, _traces=set(), _check=lambda: None)
        def abort(): transport._closed = True
        transport._abort = abort
        state = dict(sequence=1, payload=struct.pack('<i', 42), error=0, observed=1)
        def command(name, request):
            self.assertEqual(name, 'trace')
            op = wire.HEADER.unpack_from(request)[1]
            reply = bytearray(request)
            error = state['error']
            count = int(op == 3 and not error)
            wire.OUTPUT.pack_into(reply, wire.OUTPUT_AT, error, 5 if op == 5 else 2,
                                  1, count, state['observed'], 0, 0)
            if count:
                wire.EVENT.pack_into(reply, wire.EVENTS_AT, state['sequence'], 100, 8, 99, 4, 0, len(state['payload']))
                at = wire.EVENTS_AT + wire.EVENT.size
                reply[at:at + len(state['payload'])] = state['payload']
            return {'trace_packet': reply.hex()}
        transport.command = command
        handle = Trace(session, 7, plan, wire.TraceReply(9, 0, 1, 0, 0, 0, 0, ()))
        session._traces.add(handle)
        return session, handle, state

    def test_stopped_read_preserves_decoded_values_and_forget_revokes(self):
        session, trace, state = self.fixture()
        trace.stop()
        self.assertEqual(trace.state, 'stopped')
        events = trace.read()
        self.assertEqual(events[0].return_value, 42)
        self.assertEqual((events[0].pid, events[0].index, events[0].serial), (99, 4, 0))
        trace.close(); trace.close()
        self.assertEqual(trace.state, 'forgotten')
        self.assertFalse(session._traces)
        with self.assertRaises(RuntimeQueryError): trace.read()

    def test_duplicate_event_or_bad_payload_aborts_controller(self):
        session, trace, state = self.fixture()
        trace.read()
        with self.assertRaisesRegex(RuntimeQueryError, 'Stale trace event'): trace.read()
        self.assertTrue(session._transport._closed)
        self.assertEqual(trace.state, 'unknown')
        session, trace, state = self.fixture()
        state['payload'] = b'\x01'
        with self.assertRaisesRegex(RuntimeQueryError, 'retained plan'): trace.read()
        self.assertTrue(session._transport._closed)

    def test_deferred_cleanup_keeps_handle_and_does_not_retry(self):
        session, trace, state = self.fixture()
        state['error'] = 934
        with self.assertRaises(TraceError) as caught: trace.close()
        self.assertEqual(caught.exception.code, 934)
        self.assertIn(trace, session._traces)
        self.assertFalse(session._transport._closed)
        state['error'] = 0
        trace.close()

    def test_malformed_acknowledgement_revokes_all_handles(self):
        session, trace, state = self.fixture()
        session._transport.command = lambda *_: {}
        with self.assertRaisesRegex(RuntimeQueryError, 'acknowledgement'): trace.status()
        self.assertTrue(session._transport._closed)
        self.assertEqual(trace.state, 'unknown')

    def test_v18_opt_in_and_failed_handshake(self):
        backend = multi.MultiButtonTransportTests().backend()
        backend.trace_protocol = 1; backend.trace_capacity = 16
        with patch('expedition33.sdk.SessionTransport', return_value=backend) as factory:
            with Session(traces=True) as session:
                self.assertTrue(session.supports_traces)
                self.assertIn('research-probe-v18', str(factory.call_args.kwargs['_executable']))
                marker = SimpleNamespace(_state='active')
                session._traces = [marker]
            self.assertEqual(marker._state, 'session_closed')
        backend = multi.MultiButtonTransportTests().backend()
        backend.trace_protocol = True; backend.trace_capacity = 16
        with patch('expedition33.sdk.SessionTransport', return_value=backend):
            with self.assertRaisesRegex(RuntimeQueryError, 'Trace backend'): Session(traces=True)
        self.assertTrue(backend._closed)

    def test_transport_trace_payload_and_capability_gate(self):
        transport = multi.MultiButtonTransportTests().transport()
        payload = wire.encode_request('status', 7, 9)
        with self.assertRaises(ValueError): transport.command('trace', payload)
        self.assertEqual(transport._process.stdin.getvalue(), '')
        transport.trace_protocol = 1; transport.trace_capacity = 16
        transport._read = lambda: dict(event='session_response', command='trace', closed=False)
        transport.command('trace', payload)
        self.assertEqual(transport._process.stdin.getvalue(), 'trace ' + payload.hex() + '\n')
