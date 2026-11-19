import struct
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _enum_wire,_invocation_wire as callwire
from expedition33 import _story_layer_batch_wire as wire
from expedition33.invocation import CallPlan,Parameter,ObjectPatch
from expedition33.story_layer_batch import execute,available
from expedition33._ui_batch import pack_sparse

def obj(i):return N(index=i,serial=1000+i,address=i*0x10000)
def plan(setter=False):
    fields=[Parameter('InDataLayerInstance','ObjectProperty',0,8,1,0x80,constraint=obj(3))]
    if setter:
        fields.extend((Parameter('InState','EnumProperty',8,1,1,0x80,constraint=obj(5)),
            Parameter('bInIsRecursive','BoolProperty',9,1,1,0x80,boolean_encoding=0xff010001),
            Parameter('ReturnValue','BoolProperty',10,1,1,0x480,boolean_encoding=0xff010001)))
    else:fields.append(Parameter('ReturnValue','EnumProperty',8,1,1,0x480,constraint=obj(5)))
    return CallPlan(obj(1),obj(2),0,0,11 if setter else 9,16,10 if setter else 8,tuple(fields),
        bytes(8)+(b'\x02\0\0' if setter else b'\0'),(ObjectPatch(0,obj(4)),),4)

def response(sent,requests,*,error=0,failed=None,unknown=False,wrong_input=False):
    out=bytearray(wire.SIZE);out[:64]=sent[:64];at=64
    for i,request in enumerate(requests):
        packet=bytearray(request)
        struct.pack_into('<II',packet,32,(2 if unknown else 0) if i==failed else 1,201 if i==failed else 0)
        packet[callwire.DATA_AT+struct.unpack_from('<I',request,12)[0]]=2 if struct.unpack_from('<I',request,24)[0]==2 else 1
        if wrong_input:packet[callwire.OBJECTS_AT+4]^=1
        packed=pack_sparse(packet);struct.pack_into('<I',out,at,len(packed));at+=4;out[at:at+len(packed)]=packed;at+=len(packed)
    struct.pack_into('<2I',out,8,error,len(requests));struct.pack_into('<I',out,52,at)
    return bytes(out).hex()

class LayerWireTests(unittest.TestCase):
    def setUp(self):self.requests=(_enum_wire.encode_plan(plan()),)*3;self.sent=wire.encode((10,1010,0xa0000),(11,1011,0xb0000),self.requests)
    def test_scalar_receipts_preserve_order_and_input_identity_without_new_leases(self):
        receipts=wire.decode(self.sent,self.requests,response(self.sent,self.requests))
        self.assertEqual(len(receipts),3);self.assertEqual([r.data[8] for r in receipts],[2,2,2])
    def test_partial_ack_reports_failed_prefix_and_unknown_is_not_retryable(self):
        for unknown,error in ((False,4331),(True,4332)):
            with self.assertRaises(wire.LayerBatchError) as caught:
                wire.decode(self.sent,self.requests,response(self.sent,self.requests[:2],error=error,failed=1,unknown=unknown))
            self.assertEqual(len(caught.exception.receipts),2);self.assertEqual(caught.exception.unknown,unknown)
            self.assertEqual(caught.exception.receipts[0].outcome,'dispatch_returned')
    def test_world_change_bad_extent_and_changed_input_are_not_accepted(self):
        good=bytearray.fromhex(response(self.sent,self.requests))
        for at in (16,32,48,52):
            bad=bytearray(good);bad[at]^=1
            with self.assertRaises(ValueError):wire.decode(self.sent,self.requests,bad.hex())
        with self.assertRaises(ValueError):wire.decode(self.sent,self.requests,response(self.sent,self.requests,wrong_input=True))
    def test_bounds_and_padding_rejected_before_transport(self):
        for requests in ((),self.requests*6):
            with self.assertRaises(ValueError):wire.encode((10,1010,0xa0000),(11,1011,0xb0000),requests)
        bad=bytearray(self.sent);bad[-1]=1
        with self.assertRaises(ValueError):wire.validate_request(bytes(bad))

class LayerDispatchTests(unittest.TestCase):
    def setup_call(self):
        scope=N(_check=Mock(),_lease_context=nullcontext);session=N(_transport=N(story_layer_batch_protocol=1,command=Mock()))
        scope._session=session;p=plan();catalog=N(path_name=lambda fn:'/Script/Engine.DataLayerManager:GetDataLayerInstanceRuntimeState')
        planner=N(_scope=lambda:scope,_catalog=catalog);call=N(_check=Mock(return_value=(planner,session)),_plan=p)
        def command(name,sent):return {'mesh_packet':response(sent,(_enum_wire.encode_plan(p),)*2)}
        session._transport.command.side_effect=command
        return scope,call,planner
    def test_two_checked_plans_share_one_native_handoff(self):
        scope,call,_=self.setup_call()
        with patch('expedition33.story_layer_batch.decode_result',return_value=N(return_value=2)):
            self.assertEqual(execute(scope,(10,1010,0xa0000),(11,1011,0xb0000),(call,call)),(2,2))
        self.assertEqual(call._check.call_count,2);scope._session._transport.command.assert_called_once()
    def test_stale_plan_wrong_scope_and_arbitrary_function_never_dispatch(self):
        for mode in ('stale','scope','function'):
            scope,call,planner=self.setup_call()
            if mode=='stale':call._check.side_effect=RuntimeError('revoked plan')
            elif mode=='scope':planner._scope=lambda:object()
            else:planner._catalog.path_name=lambda fn:'/Script/Engine.Actor:K2_DestroyActor'
            with self.assertRaises((ValueError,RuntimeError)):execute(scope,(10,1010,0xa0000),(11,1011,0xb0000),(call,))
            scope._session._transport.command.assert_not_called()
    def test_transport_failure_is_unknown_without_retry(self):
        scope,call,_=self.setup_call();scope._session._transport.command.side_effect=RuntimeError('pipe lost')
        with self.assertRaises(wire.LayerBatchError) as caught:execute(scope,(10,1010,0xa0000),(11,1011,0xb0000),(call,))
        self.assertTrue(caught.exception.unknown);scope._session._transport.command.assert_called_once()

if __name__=='__main__':unittest.main()
