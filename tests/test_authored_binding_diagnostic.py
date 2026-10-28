import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33 import _authored_binding_diagnostic as wire
from expedition33 import _sequence_owner as owner

class AuthoredBindingDiagnosticWire(unittest.TestCase):
    def setUp(self):
        self.objects=[SimpleNamespace(index=i,serial=i+1,address=0x10000+i*0x100) for i in range(5)]
        self.request=wire.encode(self.objects,(1,2,3,4,5),(1,2,3,4))

    def test_request_bounds_and_sequence_envelope(self):
        wire.validate_request(self.request)
        envelope=owner.HEADER.pack(1,16,7,0,0,0)+self.request+bytes(owner.SIZE-32-wire.SIZE)
        owner.validate_request(envelope)
        owner.validate_request(owner.HEADER.pack(1,17,7,0,0,0)+bytes(owner.SIZE-32))
        with self.assertRaises(ValueError):wire.encode(self.objects,(1,2,0,4,5),(1,2,3,4))
        with self.assertRaises(ValueError):wire.encode(self.objects,(1,2,3,4,5),(0,0,0,0))
        bad=bytearray(envelope);bad[-1]=1
        with self.assertRaises(ValueError):owner.validate_request(bytes(bad))

    def test_result_is_correlated_and_bounded(self):
        response=bytearray(self.request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,152,1)
        wire.IDENTITY.pack_into(response,160,9,3,0x20000)
        self.assertEqual(wire.decode(self.request,bytes(response)),dict(outcome=1,objects=((9,3,0x20000),)))
        response[16]^=1
        with self.assertRaises(ValueError):wire.decode(self.request,bytes(response))
        response[16]^=1;struct.pack_into('<I',response,152,9)
        with self.assertRaises(ValueError):wire.decode(self.request,bytes(response))

    def test_empty_and_unknown_results_are_distinct(self):
        for outcome in (0,1,2):
            response=bytearray(self.request);struct.pack_into('<I',response,12,outcome)
            self.assertEqual(wire.decode(self.request,bytes(response)),dict(outcome=outcome,objects=()))
        response=bytearray(self.request);struct.pack_into('<I',response,12,2);struct.pack_into('<I',response,152,1)
        with self.assertRaises(ValueError):wire.decode(self.request,bytes(response))

    def native(self, replies):
        def command(_,data):
            op=owner.HEADER.unpack_from(data)[1]
            error,state,outcome=replies.pop(0)
            response=bytearray(data);struct.pack_into('<II',response,24,error,state)
            if op==16:struct.pack_into('<I',response,44,outcome)
            return {'sequence_owner_packet':bytes(response).hex()}
        session=SimpleNamespace(_check=lambda:None,_abort_ownership=Mock(),
            _transport=SimpleNamespace(sequence_authored_binding_diagnostic_protocol=1,command=Mock(side_effect=command)))
        native=owner.NativeSequenceOwner(SimpleNamespace(_session=session));native.state='armed'
        return native,session

    def test_success_retains_query_until_explicit_release(self):
        native,session=self.native([(0,1,1),(0,1,0)])
        self.assertEqual(native.query_authored_component(self.request),dict(outcome=1,objects=()))
        with self.assertRaisesRegex(RuntimeError,'Release the retained'):
            native.query_authored_component(self.request)
        self.assertTrue(native.release_authored_component());self.assertEqual(native.state,'armed')
        self.assertEqual(session._transport.command.call_count,2)

    def test_rejection_requires_release_and_deferred_release_can_retry(self):
        for code in (1581,407,1601,1602,1603,1604,1611,1612,1613,1614,1615,1616,1617,*range(1701,1724)):
            native,session=self.native([(code,1,0),(407,1,0),(0,1,0)])
            self.assertIsNone(native.query_authored_component(self.request))
            self.assertEqual(native.authored_binding_error,code)
            self.assertEqual(native.state,'armed')
            self.assertTrue(native._authored_query_active)
            with self.assertRaisesRegex(RuntimeError,'Release the retained'):
                native.query_authored_component(self.request)
            self.assertFalse(native.release_authored_component());self.assertEqual(native.state,'cleanup_pending')
            self.assertTrue(native.release_authored_component());self.assertEqual(native.state,'armed')
            session._abort_ownership.assert_not_called()

    def test_unknown_is_not_replayed_and_aborts(self):
        native,session=self.native([(1583,2,2)])
        with self.assertRaisesRegex(RuntimeError,'Unknown native authored'):
            native.query_authored_component(self.request)
        self.assertEqual(native.state,'unknown');session._abort_ownership.assert_called_once()
        with self.assertRaises(RuntimeError):native.query_authored_component(self.request)
        self.assertEqual(session._transport.command.call_count,1)

    def test_malformed_reply_aborts_owner(self):
        native,session=self.native([])
        session._transport.command.return_value={'sequence_owner_packet':'00'}
        session._transport.command.side_effect=None
        with self.assertRaises(ValueError):native.query_authored_component(self.request)
        self.assertEqual(native.state,'unknown');session._abort_ownership.assert_called_once()

if __name__=='__main__':unittest.main()
