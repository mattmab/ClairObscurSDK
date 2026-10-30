import math,struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _sequence_origin as origin,_sequence_owner as owner,_invocation_wire as call
from test_sequence_origin_update import status_plan


class OriginTransformTests(unittest.TestCase):
    def make_owner(self,*,error=0,state=1,outcome=1,playing=False,corrupt=False):
        def command(name,data):
            owner.validate_request(data)
            response=bytearray(data);struct.pack_into('<II',response,24,error,state)
            if struct.unpack_from('<I',data,4)[0]==15:
                struct.pack_into('<II',response,32+32,outcome,0 if outcome==1 else 209)
                response[32+call.DATA_AT]=int(playing)
            if corrupt:response[-1]=1
            return dict(sequence_owner_packet=response.hex())
        transport=N(sequence_origin_transform_protocol=1,command=Mock(side_effect=command))
        session=N(_check=lambda:None,_transport=transport,_abort_ownership=Mock())
        native=owner.NativeSequenceOwner(N(_session=session));native.state='armed'
        return native,session

    def test_packet_bounds_and_validation(self):
        data=origin.encode_transform((100,-20,3),90)
        self.assertEqual(len(data),40);origin.validate_transform_request(data)
        for yaw in (float('nan'),float('inf'),181,-181,True):
            with self.assertRaises(ValueError):origin.encode_transform((1,2,3),yaw)
        with self.assertRaises(ValueError):origin.validate_transform_request(data[:-1])

    def test_configure_and_idle_update(self):
        native,session=self.make_owner()
        self.assertTrue(native.configure_origin_transform((10,20,30),90))
        self.assertTrue(native.update_origin_transform((40,50,60),-90,status_plan()))
        self.assertEqual(native.state,'armed');self.assertEqual(session._transport.command.call_count,2)
        session._abort_ownership.assert_not_called()

    def test_rejection_capability_and_uncertain_ack(self):
        native,session=self.make_owner(error=1591,playing=True)
        with self.assertRaisesRegex(RuntimeError,'idle'):native.update_origin_transform((1,2,3),0,status_plan())
        self.assertEqual(native.state,'armed');session._abort_ownership.assert_not_called()
        native,session=self.make_owner();session._transport.sequence_origin_transform_protocol=0
        with self.assertRaisesRegex(RuntimeError,'capability'):native.configure_origin_transform((1,2,3),0)
        session._transport.command.assert_not_called()
        native,session=self.make_owner(error=1593,state=2)
        with self.assertRaises(RuntimeError):native.update_origin_transform((1,2,3),0,status_plan())
        session._transport.command.assert_called_once();session._abort_ownership.assert_called_once()
        native,session=self.make_owner(corrupt=True)
        with self.assertRaises(ValueError):native.configure_origin_transform((1,2,3),0)
        session._abort_ownership.assert_called_once()

if __name__=='__main__':unittest.main()
