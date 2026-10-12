import struct
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _sequence_binding_query as query
from expedition33 import _sequence_owner as owner_wire


class BindingQueryTests(unittest.TestCase):
    def request(self, profile=1):
        return query.encode(profile,N(index=42,serial=17,address=0x123400))

    def response(self, request, fields=(1,1,5,5,1,0,0,0)):
        return request[:32]+struct.pack('<8I',*fields)

    def test_profile_and_identity_bounds(self):
        for profile in (0,3,True,'1'):
            with self.assertRaises(ValueError): self.request(profile)
        for identity in ((-1,1,1),(1,-1,1),(1,1,0),(1,1,2**64)):
            with self.assertRaises(ValueError):query.encode(1,N(index=identity[0],serial=identity[1],address=identity[2]))

    def test_zero_serial_observation_is_valid_before_native_stabilization(self):
        packet=query.encode(1,N(index=15205,serial=0,address=0x123400))
        query.validate_request(packet)

    def test_bounded_diagnostics(self):
        request=self.request()
        result=query.decode(request,self.response(request))
        self.assertEqual(result['matched_bindings'],1)
        self.assertNotIn('objects',result)
        for fields in ((2,1,3,3,1,0,0,0),(1,2,3,3,1,0,0,0),
                       (1,1,4,3,1,0,0,0),(1,1,3,18,1,0,0,0),
                       (1,1,3,3,3,0,0,0),(1,1,3,3,1,1,0,0)):
            with self.assertRaises(ValueError):query.decode(request,self.response(request,fields))
        with self.assertRaises(ValueError):query.decode(request,self.response(self.request(2)))

    def owner(self, capability=1):
        session=N(_transport=N(sequence_binding_query_protocol=capability,command=Mock()),
                  _check=lambda:None,_abort_ownership=Mock())
        owner=owner_wire.NativeSequenceOwner(N(_session=session));owner.state='armed'
        return owner,session

    def test_capability_and_lifecycle_gate_before_dispatch(self):
        for state in ('new','prepared','unknown','closed','cleanup_pending'):
            owner,session=self.owner();owner.state=state
            with self.assertRaises(RuntimeError):owner.query_authored_bindings(1,N())
            session._transport.command.assert_not_called()
        owner,session=self.owner(0)
        with self.assertRaises(RuntimeError):owner.query_authored_bindings(1,N())
        session._transport.command.assert_not_called()

    def test_wire_and_known_return(self):
        owner,session=self.owner()
        def command(name,data):
            owner_wire.validate_request(data)
            self.assertEqual(owner_wire.HEADER.unpack_from(data)[1],5)
            self.assertFalse(any(data[96:]))
            return {'sequence_owner_packet':(data[:28]+struct.pack('<I',1)+
                self.response(data[32:96])+data[96:]).hex()}
        session._transport.command.side_effect=command
        result=owner.query_authored_bindings(1,N(index=42,serial=17,address=0x123400))
        self.assertEqual(result['outcome'],1);self.assertEqual(owner.state,'armed')
        session._abort_ownership.assert_not_called()

    def test_uncertain_result_aborts_without_retry(self):
        for outcome in (0,1,2):
            owner,session=self.owner()
            def command(name,data):
                return {'sequence_owner_packet':(data[:28]+struct.pack('<I',1)+
                    self.response(data[32:96],(0,0,0,0,outcome,0,0,0))+data[96:]).hex()}
            session._transport.command.side_effect=command
            with self.assertRaises((RuntimeError,ValueError)):
                owner.query_authored_bindings(1,N(index=42,serial=17,address=0x123400))
            self.assertEqual(owner.state,'unknown')
            session._abort_ownership.assert_called_once()
            session._transport.command.assert_called_once()

    def test_packet_rejects_hidden_tail(self):
        data=owner_wire.HEADER.pack(1,5,1,0,0,0)+self.request()+bytes(owner_wire.SIZE-96)
        owner_wire.validate_request(data)
        with self.assertRaises(ValueError):owner_wire.validate_request(data[:-1]+b'\1')

    def test_known_rejection_and_defer_preserve_explicit_close(self):
        for error in (1581,407):
            owner,session=self.owner()
            def command(name,data):
                if owner_wire.HEADER.unpack_from(data)[1]==2:
                    return {'sequence_owner_packet':data.hex()}
                return {'sequence_owner_packet':(data[:24]+struct.pack('<II',error,1)+
                    self.response(data[32:96],(0,0,4,4,0,0,0,0))+data[96:]).hex()}
            session._transport.command.side_effect=command
            with self.assertRaisesRegex(RuntimeError,'close required'):
                owner.query_authored_bindings(1,N(index=42,serial=17,address=0x123400))
            self.assertEqual(owner.state,'cleanup_pending');self.assertEqual(owner.binding_error,error)
            session._abort_ownership.assert_not_called()
            self.assertTrue(owner.close());self.assertEqual(owner.state,'closed')


if __name__=='__main__':unittest.main()
