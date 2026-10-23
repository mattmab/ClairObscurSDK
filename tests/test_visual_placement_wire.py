import io
import struct
import threading
import unittest
from types import SimpleNamespace
from expedition33._enemy_spawn_wire import build_request,validate_response
from expedition33._session import SessionTransport


class VisualPlacementWireTests(unittest.TestCase):
    def request(self):
        ids=tuple(SimpleNamespace(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(7))
        return build_request(123,115,ids)

    def transport(self,capability):
        transport=object.__new__(SessionTransport)
        transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=capability
        transport._process=SimpleNamespace(stdin=io.StringIO())
        transport._read=lambda:dict(event='session_response',command='mesh',closed=False)
        return transport

    def test_capability_is_required_before_dispatch(self):
        for capability in (0,1,2,True):
            transport=self.transport(capability)
            with self.assertRaises(ValueError):transport._command('mesh',self.request())
            self.assertEqual(transport._process.stdin.getvalue(),'')
        transport=self.transport(3);transport._command('mesh',self.request())
        self.assertTrue(transport._process.stdin.getvalue().startswith('mesh '))

    def test_only_finite_copied_result_region_can_change(self):
        request=self.request();response=bytearray(request)
        struct.pack_into('<I',response,12,1)
        struct.pack_into('<24d',response,4096,*range(24))
        self.assertTrue(validate_response(request,bytes(response)))
        for offset in (88,4288,len(response)-1):
            corrupt=bytearray(response);corrupt[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(corrupt))
        for value in (float('nan'),float('inf'),1e9):
            corrupt=bytearray(response);struct.pack_into('<d',corrupt,4096,value)
            with self.assertRaises(RuntimeError):validate_response(request,bytes(corrupt))

    def test_trace_rejection_is_not_success(self):
        request=self.request();response=bytearray(request)
        struct.pack_into('<I',response,8,2933)
        with self.assertRaisesRegex(RuntimeError,'2933'):validate_response(request,bytes(response))
