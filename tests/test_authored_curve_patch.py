import struct,unittest,weakref
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _authored_curve_patch as wire
from expedition33.invocation import InvocationError
from expedition33.cinematics.authored_copy import seal_copy


class CurvePatchTests(unittest.TestCase):
    def packet(self,kind='MovieSceneFloatChannel',before=1.,after=.5,path=None):
        objects=[N(index=i+1,serial=i+2,address=0x10000+i*0x1000) for i in range(4)]
        return wire.encode(objects,[1,2,3,4],[1,2,3,4],kind,path or ['FloatCurve'],3,
            [dict(index=1,before_time=20,after_time=21,before=before,after=after)])
    def test_packet_matches_native_envelope_and_static_channel_selectors(self):
        data=self.packet(path=['Translation',2]);wire.validate_request(data)
        self.assertEqual(len(data),20984)
        self.assertEqual(struct.unpack_from('<6I',data,136),(4,1,3,1,0,0))
        self.assertEqual(wire.SELECTOR.unpack_from(data,160)[1],2)
        self.assertEqual(wire.EDIT.unpack_from(data,1312),(1,20,21,0,0x3f800000,0x3f000000))
    def test_numeric_families_roundtrip_native_bits_and_reject_wrong_types(self):
        for kind,before,after in [('MovieSceneBoolChannel',True,False),('MovieSceneByteChannel',1,255),
                ('MovieSceneIntegerChannel',-1,-2147483648),('MovieSceneDoubleChannel',1.,.5)]:
            wire.validate_request(self.packet(kind,before,after))
        for kind,before,after in [('MovieSceneBoolChannel',True,1),('MovieSceneByteChannel',1,256),
                ('MovieSceneIntegerChannel',1,1.5),('MovieSceneFloatChannel',1.,float('nan')),
                ('MovieSceneDoubleChannel',1.,float('inf')),('MovieSceneFloatChannel',1.,1.e300)]:
            with self.assertRaises(ValueError):self.packet(kind,before,after)
    def test_padding_aliases_and_duplicate_ordinals_reject_before_transport(self):
        data=self.packet()
        for at in (156,232,1344,3360):
            changed=bytearray(data);changed[at]=1
            with self.assertRaises(ValueError):wire.validate_request(bytes(changed))
        changed=bytearray(data);changed[40:56]=changed[24:40]
        with self.assertRaises(ValueError):wire.validate_request(bytes(changed))
        changed=bytearray(data);struct.pack_into('<I',changed,148,2);changed[1344:1376]=changed[1312:1344]
        with self.assertRaises(ValueError):wire.validate_request(bytes(changed))
    def test_receipts_distinguish_prewrite_rejection_unknown_and_verified_apply(self):
        request=self.packet()
        def reply(error,state,outcome):
            result=bytearray(request);struct.pack_into('<2I',result,8,error,state);struct.pack_into('<I',result,152,outcome);return bytes(result)
        self.assertTrue(wire.decode(request,reply(0,1,1)))
        for error,state,outcome,expected in [(3780,0,0,'not_dispatched'),(3783,2,2,'unknown')]:
            with self.assertRaises(InvocationError) as raised:wire.decode(request,reply(error,state,outcome))
            self.assertEqual(raised.exception.outcome,expected)
        for values in [(0,0,0),(3780,1,1),(3783,0,0)]:
            with self.assertRaises(ValueError):wire.decode(request,reply(*values))
        changed=bytearray(reply(0,1,1));changed[1312]^=1
        with self.assertRaises(ValueError):wire.decode(request,bytes(changed))
    def test_private_copy_edit_window_is_sealed_through_child_scope(self):
        class Scope:pass
        parent=Scope();child=Scope();child._parent=weakref.ref(parent)
        asset=N(index=1,serial=2,address=0x10000)
        parent._authored_copy_states={(1,2,0x10000):dict(state='ready')}
        seal_copy(child,asset);self.assertEqual(parent._authored_copy_states[(1,2,0x10000)]['state'],'sealed')
        with self.assertRaisesRegex(RuntimeError,'no longer'):seal_copy(child,asset)
        seal_copy(child,N(index=9,serial=9,address=0x90000))
    def test_all_nested_copies_are_preflighted_before_group_sealing(self):
        root=N(index=1,serial=1,address=65536)
        child=(2,1,131072);root_key=(1,1,65536)
        scope=N(_authored_copy_states={root_key:dict(state='ready',members=[child]),child:dict(state='rejected')})
        with self.assertRaises(RuntimeError):seal_copy(scope,root)
        self.assertEqual(scope._authored_copy_states[root_key]['state'],'ready')
        scope._authored_copy_states[child]['state']='fresh'
        seal_copy(scope,root)
        self.assertTrue(all(row['state']=='sealed' for row in scope._authored_copy_states.values()))
    def test_missing_or_boolean_capability_rejects_before_retaining_inputs(self):
        for cap in (0,True,2):
            scope=N(_check=Mock(),_session=N(_transport=N(authored_curve_patch_protocol=cap)))
            with self.assertRaisesRegex(RuntimeError,'capability'):wire.patch(scope,[],[],None,[],0,[])

    def test_transport_uncertainty_pins_ownership_but_known_rejection_does_not(self):
        objects=[N(index=i+1,serial=i+2,address=0x10000+i*0x1000) for i in range(4)]
        leases=[N(object=obj,_token=i+1) for i,obj in enumerate(objects)]
        for mode,aborted in [('applied',False),('rejected',False),('unknown',True),('corrupt',True),('timeout',True)]:
            def command(verb,request):
                self.assertEqual(verb,'mesh');wire.validate_request(request)
                if mode=='timeout':raise TimeoutError('Receipt unavailable')
                reply=bytearray(request)
                error,state,outcome={'applied':(0,1,1),'rejected':(3780,0,0),
                    'unknown':(3783,2,2),'corrupt':(0,1,1)}[mode]
                struct.pack_into('<2I',reply,8,error,state);struct.pack_into('<I',reply,152,outcome)
                if mode=='corrupt':reply[16]^=1
                return {'mesh_packet':reply.hex()}
            session=N(_transport=N(authored_curve_patch_protocol=1,command=command),_abort_ownership=Mock())
            scope=N(_check=Mock(),_session=session,_lease_context=nullcontext)
            with patch('expedition33._stable_lease.acquire_stable',side_effect=[(lease,None) for lease in leases]):
                arguments=(scope,objects,[1,2,3,4],'MovieSceneFloatChannel',['FloatCurve'],3,
                    [dict(index=1,before_time=20,after_time=21,before=1.,after=.5)])
                if mode=='applied':self.assertTrue(wire.patch(*arguments))
                else:
                    with self.assertRaises((InvocationError,ValueError,TimeoutError)):wire.patch(*arguments)
            self.assertEqual(session._abort_ownership.called,aborted,mode)


if __name__=='__main__':unittest.main()
