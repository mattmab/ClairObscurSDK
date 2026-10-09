from dataclasses import replace
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from expedition33 import _text_wire as text
from expedition33 import _invocation_wire as call
from expedition33 import _retained_wire as retained
from expedition33.invocation import CallPlan, Parameter
import test_invocation


class TextWireTests(unittest.TestCase):
    def setUp(self):
        fixture=test_invocation.InvocationTests(); fixture.setUp()
        self.plan=CallPlan(fixture.target,fixture.function,0x400,0x1234,32,32,16,
                          (Parameter('InText','TextProperty',0,16,1,0x80),
                           Parameter('ReturnValue','TextProperty',16,16,1,0x480)),bytes(32),(),3)

    def reply(self,request,value='Returned'):
        packet=bytearray(request)
        struct.pack_into('<I',packet,32,1)  # CallDispatchReturned
        at=text.SLOTS_AT+text.SLOT_SIZE
        encoded=text.encode_units(value)
        text.SLOT_HEADER.pack_into(packet,at,1,len(encoded)//2)
        packet[at+8:at+8+len(encoded)]=encoded
        return packet

    def test_unicode_and_empty_roundtrip(self):
        for value in ('','Mods — café 🚀','a'*4095):
            request=text.encode_plan(self.plan,{'InText':value})
            reply=text.decode_reply(request,self.reply(request,value).hex())
            self.assertEqual(reply.texts,((0,value),(1,value)))
            self.assertEqual(reply.leases,())
            self.assertEqual(reply.call.outcome,'dispatch_returned')
            self.assertEqual(reply.call.data,bytes(32))

    def test_input_validation_and_version_gate(self):
        for value in (None,123,'a\0b','\ud800','\udc00','a'*4096,'🚀'*2048):
            with self.subTest(value_type=type(value)):
                with self.assertRaises(ValueError): text.encode_plan(self.plan,{'InText':value})
        for values in ({},{'InText':'A','ReturnValue':'B'}):
            with self.assertRaises(ValueError): text.encode_plan(self.plan,values)
        for version in (1,2,3.0,True):
            with self.assertRaises(ValueError): text.encode_plan(replace(self.plan,wire_version=version),{'InText':'A'})
        for changed in (replace(self.plan.parameters[0],width=8),replace(self.plan.parameters[0],dimension=2)):
            with self.assertRaises(ValueError):
                text.encode_plan(replace(self.plan,parameters=(changed,self.plan.parameters[1])),{'InText':'A'})
        with self.assertRaises(ValueError):
            text.encode_plan(replace(self.plan,data=b'\1'+bytes(31)),{'InText':'A'})
        with self.assertRaises(ValueError): call.encode_plan(self.plan)

    def test_reply_rejects_pointer_corruption_and_wrong_correlation(self):
        request=text.encode_plan(self.plan,{'InText':'A'})
        for at,fmt,value in ((call.DATA_AT,'Q',0x123456789),
                             (text.SLOTS_AT+text.SLOT_SIZE,'I',0),
                             (text.SLOTS_AT+text.SLOT_SIZE+4,'I',4097),
                             (text.SLOTS_AT+2*text.SLOT_SIZE,'I',1),
                             (text.SLOTS_AT+8,'H',ord('X')),
                             (call.FIELDS_AT+4,'I',1)):
            packet=self.reply(request)
            struct.pack_into('<'+fmt,packet,at,value)
            with self.subTest(at=at):
                with self.assertRaises(ValueError): text.decode_reply(request,packet.hex())
        packet=self.reply(request)
        at=text.SLOTS_AT+text.SLOT_SIZE
        text.SLOT_HEADER.pack_into(packet,at,1,2)
        packet[at+8:at+text.SLOT_SIZE]=bytes(text.SLOT_SIZE-8)
        struct.pack_into('<H',packet,at+8,0xd800)
        with self.assertRaises(ValueError): text.decode_reply(request,packet.hex())

    def test_failed_outcomes_expose_no_text_or_raw_results(self):
        request=text.encode_plan(self.plan,{'InText':'A'})
        for outcome,name in ((0,'not_dispatched'),(2,'unknown')):
            packet=bytearray(request)
            struct.pack_into('<II',packet,32,outcome,700)
            packet[call.DATA_AT:call.DATA_AT+8]=b'12345678'
            reply=text.decode_reply(request,packet.hex())
            self.assertEqual((reply.call.outcome,reply.call.data,reply.texts),(name,b'',()))

    def test_object_output_requires_its_existing_lease(self):
        obj=self.plan.target
        parameter=Parameter('ObjectOut','ObjectProperty',32,8,1,0x180,constraint=obj)
        plan=replace(self.plan,parameters=self.plan.parameters+(parameter,),
                     parameter_size=40,allocation_extent=40,data=bytes(40))
        request=text.encode_plan(plan,{'InText':'A'})
        packet=self.reply(request)
        struct.pack_into('<I',packet,28,1)
        call.OBJECT.pack_into(packet,call.OBJECTS_AT,32,obj.index,obj.serial,obj.address)
        retained.HEADER.pack_into(packet,call.SIZE,1,1)
        retained.LEASE.pack_into(packet,retained.LEASES_AT,32,101)
        result=text.decode_reply(request,packet.hex())
        self.assertEqual(result.leases,((32,101),))
        self.assertEqual(result.texts,((0,'A'),(1,'Returned')))
        retained.HEADER.pack_into(packet,call.SIZE,1,0)
        retained.LEASE.pack_into(packet,retained.LEASES_AT,0,0)
        with self.assertRaises(ValueError): text.decode_reply(request,packet.hex())

    def test_eight_fields_and_no_silent_overflow(self):
        fields=tuple(Parameter('Text'+str(i),'TextProperty',i*16,16,1,0x80) for i in range(8))
        plan=replace(self.plan,parameters=fields,parameter_size=128,allocation_extent=128,
                     return_offset=65535,data=bytes(128))
        request=text.encode_plan(plan,{p.name:'' for p in fields})
        packet=bytearray(request); struct.pack_into('<I',packet,32,1)
        self.assertEqual(len(text.decode_reply(request,packet.hex()).texts),8)
        extra=Parameter('Overflow','TextProperty',128,16,1,0x80)
        with self.assertRaises(ValueError):
            text.encode_plan(replace(plan,parameters=fields+(extra,),parameter_size=144,
                                     allocation_extent=144,data=bytes(144)),
                             {p.name:'' for p in fields+(extra,)})

    def test_cross_language_request_validation(self):
        executable=Path(__file__).resolve().parents[1]/'build/owned-text-fixture/text_call_fixture.exe'
        if not executable.exists(): self.skipTest('Native text-call fixture executable not bundled')
        for value in ('','Hello 🚀','a'*4095):
            request=text.encode_plan(self.plan,{'InText':value})
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'packet.bin'; path.write_bytes(request)
                result=subprocess.run([str(executable),str(path)],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout.strip()),(0,'0'))
                changed=bytearray(request); changed[call.DATA_AT]=1; path.write_bytes(changed)
                result=subprocess.run([str(executable),str(path)],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout.strip()),(1,'603'))


if __name__=='__main__': unittest.main()
