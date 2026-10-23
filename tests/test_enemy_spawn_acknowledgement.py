"""Focused acknowledgement validation before integrating the shared SDK helper."""
import runpy
from pathlib import Path
import struct
import unittest

from expedition33 import _enemy_spawn_wire
wire=vars(_enemy_spawn_wire)

def packet(op):
    data=bytearray(wire['SIZE'])
    struct.pack_into('<4IQ',data,0,3,op,0,0,123)
    for i in range(wire['OPERATIONS'][op]):
        struct.pack_into('<iiQ',data,88+16*i,i+1,i+2,0x10000+i*256)
    if op in (110,120,133):struct.pack_into('<12d',data,2000,0,0,0,1,100,200,300,0,1,1,1,0)
    if op==119:struct.pack_into('<6d',data,2000,0,0,100,50,50,50)
    if op==122:struct.pack_into('<I',data,32,10)
    if op==133:struct.pack_into('<I',data,32,1)
    return bytes(data)

def response(request):
    data=bytearray(request)
    op=struct.unpack_from('<I',data,4)[0]
    struct.pack_into('<I',data,12,0 if op==111 else 1)
    if op in (110,112,120,131,133):struct.pack_into('<iiQ',data,4096,11,12,0x20000)
    if op==122:struct.pack_into('<Q',data,4096,1023)
    if op==121:struct.pack_into('<2d',data,4096+28*8,9,1)
    if op==117:struct.pack_into('<2Q4I',data,4096,15,7,7,0,17,0)
    if op==118:
        struct.pack_into('<iiQ',data,4096,11,12,0x20000)
        struct.pack_into('<iiQ',data,4112,21,22,0x30000)
    return bytes(data)

class AcknowledgementTests(unittest.TestCase):
    def test_all_operations_accept_only_documented_outputs(self):
        for op in wire['OPERATIONS']:
            with self.subTest(operation=op):
                request=packet(op)
                self.assertTrue(wire['validate_response'](request,response(request)))

    def test_altered_inputs_owner_reserved_bytes_and_state_fail(self):
        request=packet(110)
        for offset in (0,4,12,16,24,88,2000,4112,wire['SIZE']-1):
            with self.subTest(offset=offset):
                data=bytearray(response(request));data[offset]^=1
                with self.assertRaises(RuntimeError):wire['validate_response'](request,bytes(data))

    def test_missing_actor_and_unexpected_actor_fail(self):
        for op in (110,112):
            data=bytearray(response(packet(op)));data[4096:4112]=bytes(16)
            with self.assertRaises(RuntimeError):wire['validate_response'](packet(op),bytes(data))
        data=bytearray(response(packet(113)));data[4096]=1
        with self.assertRaises(RuntimeError):wire['validate_response'](packet(113),bytes(data))

    def test_native_failure_is_never_replayed(self):
        class Transport:
            calls=0
            def command(self, command, request):
                self.calls+=1
                data=bytearray(response(request));struct.pack_into('<I',data,8,2916)
                return {'mesh_packet':data.hex()}
        transport=Transport()
        with self.assertRaisesRegex(RuntimeError,'2916'):
            wire['exchange'](transport,packet(112))
        self.assertEqual(transport.calls,1)

    def test_truncated_and_malformed_acknowledgements_fail(self):
        request=packet(111)
        with self.assertRaises(RuntimeError):wire['validate_response'](request,response(request)[:-1])
        for reply in ({},{'mesh_packet':'invalid hex'},{'mesh_packet':None}):
            class Transport:
                def command(self, *_):return reply
            with self.assertRaises(RuntimeError):wire['exchange'](Transport(),request)

if __name__=='__main__':unittest.main()
