from dataclasses import replace
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from expedition33.invocation import decode_result, InvocationError, OUT, RETURN, PARM
from expedition33._invocation_wire import CallReply
from expedition33.sdk import Session
from expedition33.introspection import Harness, UnsupportedCapability
from expedition33 import RuntimeQueryError
from expedition33._invocation_wire import encode_plan
import test_invocation


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.p = test_invocation.InvocationTests()
        self.p.setUp()

    def test_named_outputs_and_scalar_return(self):
        p = self.p
        plan = p.plan([p.field('Out', 'IntProperty', 0, 4, PARM | OUT, dimension=2),
                       p.field('ReturnValue', 'BoolProperty', 8, 1, PARM | RETURN,
                               bool_encoding='0xff010001')], {}, 9, 8)
        reply = CallReply('dispatch_returned', 0, struct.pack('<iiB', 12, -4, 1), ())
        result = decode_result(plan, reply, p.catalog)
        self.assertIs(result.return_value, True)
        self.assertEqual(dict(result.outputs), {'Out': (12, -4)})
        with self.assertRaises(TypeError): result.outputs['Out'] = 2
        with self.assertRaises(InvocationError) as caught:
            decode_result(plan, replace(reply, data=reply.data[:-1] + b'\x02'), p.catalog)
        self.assertEqual(caught.exception.outcome, 'dispatch_returned')

    def test_returned_object_revalidated_and_not_owned(self):
        p = self.p
        cls = p.catalog.by_index[2]
        plan = p.plan([p.field('ReturnValue', 'ObjectProperty', 0, 8, PARM | RETURN,
            property_class_index=2, property_class_serial=cls.serial,
            property_class_name=cls.name, property_class_address=hex(cls.address))], {}, 8, 0)
        observed = (0, p.target.index, p.target.serial, p.target.address)
        reply = CallReply('dispatch_returned', 0, bytes(8), (observed,))
        self.assertEqual(decode_result(plan, reply, p.catalog).return_value, p.target)
        self.assertIsNone(decode_result(plan, replace(reply, objects=()), p.catalog).return_value)
        for slots in (((0, p.target.index, 999, p.target.address),),
                      ((4, p.target.index, p.target.serial, p.target.address),), (observed, observed)):
            with self.assertRaises(InvocationError): decode_result(plan, replace(reply, objects=slots), p.catalog)

    def test_rejected_and_unknown_have_no_decoded_results(self):
        p = self.p
        plan = p.plan([], {}, 0)
        for outcome, code in (('not_dispatched', 202), ('unknown', 223)):
            with self.assertRaises(InvocationError) as caught:
                decode_result(plan, CallReply(outcome, code, b'', ()), p.catalog)
            self.assertEqual((caught.exception.outcome, caught.exception.native_error), (outcome, code))
            self.assertIn('do not retry automatically', str(caught.exception))

    def test_harness_capabilities_retain_gate_and_no_ownership_of_session(self):
        session = SimpleNamespace(supports_reflected_invocation=True)
        with Harness(session=session) as h:
            self.assertIn('invoke', h.request({'op': 'status'})['operations'])
            with patch.object(h._backend, 'refresh') as refresh:
                with self.assertRaises(UnsupportedCapability):
                    h.request({'op': 'invoke', 'allow_mutation': True, 'retain': 'x'})
                refresh.assert_not_called()
                with self.assertRaises(ValueError): h.request({'op': 'invoke'})
            self.assertFalse(h._running)
        self.assertFalse(hasattr(session, 'closed'))

    def test_v5_session_rejects_before_capture(self):
        session = object.__new__(Session)
        session._closed = False
        session._transport = SimpleNamespace(_check_thread=lambda: None, reflected_protocol=0)
        with patch('expedition33.catalog.capture') as capture:
            with self.assertRaises(ValueError): session.invoke(self.p.target, self.p.function)
            capture.assert_not_called()

    def test_sdk_dispatch_errors_do_not_retry(self):
        p = self.p
        plan = p.plan([], {}, 0)
        session = object.__new__(Session)
        session._closed, session._object = False, p.target
        command = Mock()
        session._transport = SimpleNamespace(_check_thread=lambda: None, reflected_protocol=1, command=command)
        packet = bytearray(encode_plan(plan))
        struct.pack_into('<II', packet, 32, 0, 202)
        for response, expected in (({'call_packet': packet.hex()}, 'not_dispatched'),
                                   (RuntimeQueryError('timeout'), 'unknown')):
            command.reset_mock()
            command.side_effect = response if isinstance(response, Exception) else None
            command.return_value = response
            with patch('expedition33.catalog.capture', return_value=p.catalog), \
                    patch('expedition33.invocation.prepare_call', return_value=plan):
                with self.assertRaises(InvocationError) as caught:
                    session.invoke(p.target, p.function)
            self.assertEqual(caught.exception.outcome, expected)
            self.assertEqual(command.call_count, 1)


if __name__ == '__main__': unittest.main()
