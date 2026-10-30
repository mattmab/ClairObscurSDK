import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.invocation import CallPlan,Parameter
from expedition33 import _sequence_owner as owner,_invocation_wire as call


def status_plan():
    target=N(index=10,serial=20,address=0x10000)
    function=N(index=11,serial=21,address=0x20000,name='IsPlaying')
    field=Parameter('ReturnValue','BoolProperty',0,1,1,6755468160534400,0xff010001)
    return CallPlan(target,function,1417806849,0x1234,1,1,0,(field,),b'\0',())


class OriginUpdateTests(unittest.TestCase):
    def make_owner(self,*,error=0,state=1,outcome=1,playing=False,corrupt=False):
        def command(name,data):
            owner.validate_request(data)
            response=bytearray(data);struct.pack_into('<II',response,24,error,state)
            struct.pack_into('<II',response,32+32,outcome,0 if outcome==1 else 209)
            response[32+call.DATA_AT]=int(playing)
            if corrupt:response[-1]=1
            return dict(sequence_owner_packet=response.hex())
        transport=N(sequence_origin_update_protocol=1,command=Mock(side_effect=command))
        session=N(_check=lambda:None,_transport=transport,_abort_ownership=Mock())
        native=owner.NativeSequenceOwner(N(_session=session));native.state='armed'
        return native,session

    def test_idle_update_and_playing_rejection_preserve_owner(self):
        native,session=self.make_owner()
        self.assertTrue(native.update_origin((100,200,300),status_plan()))
        self.assertEqual(native.state,'armed');session._abort_ownership.assert_not_called()
        native,session=self.make_owner(error=1591,playing=True)
        with self.assertRaisesRegex(RuntimeError,'idle'):native.update_origin((1,2,3),status_plan())
        self.assertEqual(native.state,'armed');session._abort_ownership.assert_not_called()

    def test_lost_write_proof_or_corrupt_reply_is_not_replayed(self):
        for args in (dict(error=1593,state=2),dict(corrupt=True),dict(state=3)):
            native,session=self.make_owner(**args)
            with self.assertRaises((ValueError,RuntimeError)):native.update_origin((1,2,3),status_plan())
            session._transport.command.assert_called_once();session._abort_ownership.assert_called_once()

    def test_missing_capability_and_bad_coordinates_reject_before_sending(self):
        native,session=self.make_owner();session._transport.sequence_origin_update_protocol=0
        with self.assertRaisesRegex(RuntimeError,'capability'):native.update_origin((1,2,3),status_plan())
        session._transport.command.assert_not_called()
        session._transport.sequence_origin_update_protocol=1
        with self.assertRaises(ValueError):native.update_origin((float('nan'),2,3),status_plan())
        session._transport.command.assert_not_called();self.assertEqual(native.state,'armed')
