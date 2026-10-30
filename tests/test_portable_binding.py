import struct,unittest
from contextlib import nullcontext
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from expedition33._portable_binding import encode,decode,validate_request
from expedition33.invocation import InvocationError

def packet():
    ids=tuple(N(index=i,serial=i+1,address=0x10000*(i+1)) for i in range(5))
    return encode(ids,(1,2,3,4,5),dict(A=42,B=-2,C=3,D=-4))

class PortableBindingTests(unittest.TestCase):
    def test_combined_binding_metadata_feeds_native_query_without_second_registry_scan(self):
        from expedition33._portable_binding import resolve
        from expedition33.cinematics.binding_overrides import _prepare_binding_metadata
        objects=tuple(N(index=i+1,serial=i+2,address=0x10000*(i+1)) for i in range(5))
        held={o.index:N(object=o,_token=o.index,active=True) for o in objects}
        catalog=N(find_path=Mock(side_effect=lambda path:objects[0] if 'Default__' in path else objects[1]))
        def command(name,request):
            response=bytearray(request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,192,1)
            response[168:184]=request[152:168]
            return dict(mesh_packet=response.hex())
        transport=N(sequence_portable_binding_protocol=1,_executable='test',command=Mock(side_effect=command))
        scope=N(pid=123,_check=Mock(),_session=N(_transport=transport,_abort_ownership=Mock()),_lease_context=lambda:nullcontext())
        with patch('expedition33.cinematics.binding_overrides.capture_matching',return_value=catalog) as scan, \
             patch('expedition33.cinematics.binding_overrides._hold',side_effect=lambda scope,obj:held[obj.index]), \
             patch('expedition33._portable_binding.shared_operation',return_value=nullcontext()), \
             patch('expedition33._portable_binding.capture_matching') as redundant_scan, \
             patch('expedition33._portable_binding._hold',side_effect=lambda scope,obj:held[obj.index]):
            _prepare_binding_metadata(scope)
            result=resolve(scope,objects[2],objects[3],dict(A=42,B=0,C=0,D=0))
            self.assertEqual(result['Guid']['A'],42)
            scan.assert_called_once();redundant_scan.assert_not_called();transport.command.assert_called_once()
    def test_metadata_is_retained_once_but_each_query_uses_native_frame_validation(self):
        from expedition33._portable_binding import resolve
        objects=tuple(N(index=i+1,serial=i+2,address=0x10000*(i+1)) for i in range(5))
        held={o.index:N(object=o,_token=o.index,active=True) for o in objects}
        catalog=N(find_path=Mock(side_effect=lambda path:objects[0] if 'Default__' in path else objects[1]))
        def command(name,request):
            response=bytearray(request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,192,1)
            response[168:184]=request[152:168]
            return dict(mesh_packet=response.hex())
        transport=N(sequence_portable_binding_protocol=1,_executable='test',command=Mock(side_effect=command))
        scope=N(pid=123,_check=Mock(),_session=N(_transport=transport,_abort_ownership=Mock()),_lease_context=lambda:nullcontext())
        with patch('expedition33._portable_binding.shared_operation',return_value=nullcontext()),\
             patch('expedition33._portable_binding.capture_matching',return_value=catalog) as scan,\
             patch('expedition33._portable_binding._hold',side_effect=lambda scope,obj:held[obj.index]):
            for a in (42,43):self.assertEqual(resolve(scope,objects[2],objects[3],dict(A=a,B=0,C=0,D=0))['Guid']['A'],a)
            scan.assert_called_once();self.assertEqual(transport.command.call_count,2)
            held[1].active=False
            with self.assertRaisesRegex(RuntimeError,'inactive'):resolve(scope,objects[2],objects[3],dict(A=44,B=0,C=0,D=0))
            self.assertEqual(transport.command.call_count,2)
    def test_copied_engine_value_preserves_guid_and_signed_sequence_id(self):
        request=packet();response=bytearray(request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,192,1)
        response[168:184]=request[152:168];struct.pack_into('<ii',response,184,-12345,-1)
        result=decode(request,bytes(response));self.assertEqual(result['SequenceID'],-12345);self.assertEqual(result['Guid']['A'],42)
        response[168:184]=bytes(16);self.assertIsNone(decode(request,bytes(response)))
    def test_request_padding_and_retention_required(self):
        request=packet();validate_request(request)
        for at in (24,168,192,196,20983):
            bad=bytearray(request);bad[at]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))
        for start,end in ((112,120),(152,168)):
            bad=bytearray(request);bad[start:end]=bytes(end-start)
            with self.assertRaises(ValueError):validate_request(bytes(bad))
    def test_rejection_unknown_and_malformed_receipts_remain_distinct(self):
        request=packet()
        for error,state,outcome,expected in ((3760,0,0,'not_dispatched'),(3763,2,2,'unknown')):
            response=bytearray(request);struct.pack_into('<II',response,8,error,state);struct.pack_into('<I',response,192,outcome)
            with self.assertRaises(InvocationError) as raised:decode(request,bytes(response))
            self.assertEqual(raised.exception.outcome,expected)
        response=bytearray(request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,192,1)
        response[168:184]=request[152:168];response[168]^=1
        with self.assertRaisesRegex(ValueError,'GUID'):decode(request,bytes(response))
        response=bytearray(request);response[32]^=1
        with self.assertRaisesRegex(ValueError,'correlation'):decode(request,bytes(response))
