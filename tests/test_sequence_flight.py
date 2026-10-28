import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33._sequence_flight import SequenceFlight,CONTROL,MAGIC
from expedition33._sequence_owner import HEADER,validate_request

class FlightTests(unittest.TestCase):
    def make(self,*,error=0,state=1,corrupt=False,stop_still_active=False):
        def command(name,data):
            validate_request(data);reply=bytearray(data)
            struct.pack_into('<II',reply,24,error,state)
            if not error:
                action=CONTROL.unpack_from(data,32)[2]
                CONTROL.pack_into(reply,32,MAGIC,1,action,int(not action or stop_still_active),10.,20.,30.,-5.,90.,0.)
            if corrupt:reply[-1]=1
            return dict(sequence_owner_packet=reply.hex())
        session=N(_transport=N(sequence_flight_protocol=1,command=Mock(side_effect=command)),_abort_ownership=Mock())
        sequence=N(scope=N(_check=lambda:None,_session=session),owner=N(state='armed',owner=123),uncertain=False)
        return SequenceFlight(sequence),session
    def test_status_and_stop_keep_owner_and_return_camera_pose(self):
        flight,session=self.make();flight.active=True
        self.assertEqual(flight.poll(),(10.,20.,30.,-5.,90.,0.));self.assertTrue(flight.active)
        flight.stop();self.assertFalse(flight.active)
        session._abort_ownership.assert_not_called()
    def test_known_rejection_remains_closeable_and_unknown_ack_aborts_once(self):
        flight,session=self.make(error=1791)
        with self.assertRaises(ValueError):flight.poll()
        self.assertFalse(flight.sequence.uncertain);self.assertEqual(flight.sequence.owner.state,'armed')
        session._abort_ownership.assert_not_called()
        for kwargs in (dict(error=1793,state=2),dict(corrupt=True)):
            flight,session=self.make(**kwargs)
            with self.assertRaises(RuntimeError):flight.poll()
            self.assertEqual(flight.sequence.owner.state,'unknown')
            session._transport.command.assert_called_once();session._abort_ownership.assert_called_once()
    def test_invalid_requests_and_missing_capability_never_dispatch(self):
        flight,session=self.make();session._transport.sequence_flight_protocol=0
        with self.assertRaises(ValueError):flight.poll()
        session._transport.command.assert_not_called()
        for at,value in ((32,0),(40,3),(44,1),(48,1)):
            request=bytearray(HEADER.pack(1,11,123,0,0,0)+CONTROL.pack(MAGIC,1,0,0,*([0.]*6))+bytes(49232))
            struct.pack_into('<I',request,at,value)
            with self.assertRaises(ValueError):validate_request(bytes(request))
    def test_placement_input_is_capability_gated_and_acknowledgement_checked(self):
        from expedition33._sequence_flight import INPUT,INPUT_MAGIC
        flight,session=self.make()
        with self.assertRaises(ValueError):flight.inputs()
        session._transport.command.assert_not_called()
        session._transport.sequence_placement_input_protocol=1
        def command(name,data):
            validate_request(data);reply=bytearray(data)
            struct.pack_into('<II',reply,24,0,1)
            INPUT.pack_into(reply,32,INPUT_MAGIC,1,0,1,10.,-20.,.25)
            return dict(sequence_owner_packet=reply.hex())
        session._transport.command.side_effect=command
        self.assertEqual(flight.inputs(),(True,(10.,-20.,.25)))
        session._abort_ownership.assert_not_called()

    def test_teleport_uses_observed_parameter_size_and_aligned_allocation(self):
        from expedition33 import _invocation_wire as call
        from expedition33._sequence_flight import validate
        payload=bytearray(2*call.SIZE)
        call.HEADER.pack_into(payload,0,2,49,56,48,0,0,3,0,0,0)
        call.HEADER.pack_into(payload,call.SIZE,1,1,1,0,0,0,1,0,0,0)
        validate(10,bytes(payload))
        # An aligned C++ sizeof is not UFunction.ParmsSize.
        struct.pack_into('<I',payload,4,56)
        with self.assertRaisesRegex(ValueError,'teleport'):validate(10,bytes(payload))

    def test_stop_must_acknowledge_flight_is_inactive_and_start_is_not_reentrant(self):
        flight,session=self.make(stop_still_active=True);flight.active=True
        with self.assertRaisesRegex(RuntimeError,'status mismatch'):flight.stop()
        session._abort_ownership.assert_called_once()
        flight,session=self.make();flight.active=True
        with self.assertRaisesRegex(ValueError,'Stop'):flight.start(None,None,None,None)
        session._transport.command.assert_not_called()
