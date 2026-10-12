import struct
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import test_invocation
from expedition33.invocation import prepare_call, decode_result, UnsupportedInvocation
from expedition33 import _string_wire as wire

class StringInputTests(unittest.TestCase):
    def setUp(self):
        self.p=test_invocation.InvocationTests(); self.p.setUp()
        self.row=self.p.field('Path','StrProperty',0,16,0x18000000000280)
        self.descriptor=SimpleNamespace(owners=[dict(index=7,size=16)],properties=[self.row],
            function=dict(params_size=16,return_offset=65535,flags=0x4020403,entry_rva='0x320b2d0'))
        m=patch('expedition33.invocation.describe',return_value={7:self.descriptor})
        m.start(); self.addCleanup(m.stop)
    def plan(self,value='',enabled=True):
        return prepare_call(self.p.catalog,self.p.target,self.p.function,{'Path':value},string_values=enabled)
    def test_encoding_and_copied_acknowledgement(self):
        for value in ('','movie.mp4','folder/\U0001f680.mp4','x'*4095):
            plan=self.plan(value); sent=wire.encode_plan(plan,dict(plan.texts))
            self.assertEqual(plan.wire_version,5)
            reply=bytearray(sent); struct.pack_into('<II',reply,32,1,0)
            decoded=wire.decode_reply(sent,reply.hex())
            result=decode_result(plan,decoded.call,self.p.catalog,texts=decoded.texts)
            self.assertIsNone(result.return_value)
            self.assertEqual(decoded.texts,((0,value),))
            self.assertEqual(decoded.call.data,bytes(16))
    def test_invalid_inputs_and_opt_in(self):
        with self.assertRaises(UnsupportedInvocation): self.plan(enabled=False)
        for value in ('x\0y','\ud800','\udc00','x'*4096,'\U0001f680'*2048,None,b'x'):
            with self.assertRaises(ValueError): self.plan(value)
    def test_ref_output_array_and_unaudited_rejection(self):
        for flags in (0x18000000000380,0x480,0x8000080):
            self.row['flags']=flags
            with self.assertRaises(ValueError): self.plan()
        self.row['flags']=0x18000000000280; self.row['dimension']=2
        with self.assertRaises(ValueError): self.plan()
        self.row['dimension']=1; self.descriptor.function['entry_rva']='0x1234'
        with self.assertRaises(UnsupportedInvocation): self.plan()
    def test_no_modified_echo(self):
        plan=self.plan('movie.mp4'); sent=wire.encode_plan(plan,dict(plan.texts))
        reply=bytearray(sent); struct.pack_into('<II',reply,32,1,0)
        reply[wire.SLOTS_AT+8]=ord('z')
        with self.assertRaises(ValueError): wire.decode_reply(sent,reply.hex())
