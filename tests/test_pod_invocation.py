from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import struct
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33 import _invocation_wire as wire
from expedition33 import _pod_values as pod
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.invocation import prepare_call, decode_result, InvocationError, UnsupportedInvocation
from expedition33.sdk import Session
from expedition33._session import SessionTransport
import test_invocation
from test_ownership import Transport


class PodInvocationTests(unittest.TestCase):
    def setUp(self):
        planner = test_invocation.InvocationTests(); planner.setUp()
        objects = list(planner.catalog.objects)
        classes = list(planner.catalog.classes.values())
        # Catalog.classes contains ClassRelation records.
        classes += [ClassRelation(8,1,'Package',0,40), ClassRelation(9,1,'ScriptStruct',0,128)]
        def obj(index,name,cls,outer=-1):
            cname = next(c.name for c in classes if c.index == cls)
            return CatalogObject(123,index,1,0x10000+index*0x1000,name,cname,'Class',cls,outer,1 if outer>=0 else 0,0,0)
        objects += [obj(8,'Package',1),obj(9,'ScriptStruct',1),obj(10,'/Script/CoreUObject',8),
                    obj(11,'/Script/SlateCore',8),obj(12,'/Script/Slate',8),
                    obj(13,'Vector2D',9,10),obj(14,'LinearColor',9,10),obj(15,'Margin',9,11),obj(16,'Anchors',9,12)]
        self.catalog = Catalog(123,objects,classes)
        self.target,self.function=self.catalog.by_index[5],self.catalog.by_index[7]
        self.descriptors={}
        for index,path in enumerate((pod.VECTOR,pod.COLOR,pod.MARGIN,pod.ANCHORS),13):
            profile=pod.PROFILES[path]
            rows=[]
            for name,offset,kind in profile.fields:
                nested=kind in pod.PROFILES
                row=dict(owner_index=index,name=name,offset=offset,element_size=16 if nested else 8 if kind=='DoubleProperty' else 4,
                         dimension=1,type='StructProperty' if nested else kind)
                if nested: row.update(struct_index=13,struct_serial=1,struct_name='Vector2D')
                rows.append(row)
            self.descriptors[index]=SimpleNamespace(object=self.catalog.by_index[index],
                owners=[dict(index=index,size=profile.width,super='0x0')],properties=rows,function=None)

    def plan(self,index=13,value=None,returned=False,enabled=True,dimension=1):
        obj=self.catalog.by_index[index]; width=self.descriptors[index].owners[0]['size']; size=width*dimension
        row=dict(owner_index=7,name='Value',type='StructProperty',offset=0,element_size=width,dimension=dimension,
                 flags=0x480 if returned else 0x80,struct_index=index,struct_serial=1,struct_name=obj.name)
        self.descriptors[7]=SimpleNamespace(object=self.function,owners=[dict(index=7,size=size)],properties=[row],
            function=dict(params_size=size,return_offset=0 if returned else 65535,flags=0x400,entry_rva='0x1234'))
        with patch('expedition33.invocation.describe', side_effect=lambda c, targets:{o.index:self.descriptors[o.index] for o in targets}):
            return prepare_call(self.catalog,self.target,self.function,{} if returned else {'Value':value},pod_values=enabled)

    def test_opt_in_and_nested_wire_encoding(self):
        fields={'Minimum':{'X':0,'Y':0},'Maximum':{'X':1,'Y':1}}
        with self.assertRaises(UnsupportedInvocation): self.plan(16,fields,enabled=False)
        plan=self.plan(16,fields)
        sent=wire.encode_plan(plan)
        self.assertEqual(wire.HEADER.unpack_from(sent)[0],2)
        self.assertEqual(wire.FIELD.unpack_from(sent,wire.FIELDS_AT)[0],12)
        self.assertEqual(plan.data,struct.pack('<dddd',0,0,1,1))
        self.assertEqual(plan.objects,())
        with self.assertRaises(UnsupportedInvocation): wire.encode_plan(replace(plan,wire_version=1))

    def test_return_is_copied_and_invalid_values_report_dispatch_returned(self):
        plan=self.plan(returned=True)
        sent=wire.encode_plan(plan); response=bytearray(sent)
        struct.pack_into('<II',response,32,1,0)
        struct.pack_into('<dd',response,wire.DATA_AT,160.25,-32.5)
        result=decode_result(plan,wire.decode_reply(sent,response.hex()),self.catalog)
        self.assertEqual(result.return_value,{'X':160.25,'Y':-32.5})
        with self.assertRaises(TypeError): result.return_value['X']=0
        struct.pack_into('<d',response,wire.DATA_AT,float('nan'))
        with self.assertRaises(InvocationError) as caught:
            decode_result(plan,wire.decode_reply(sent,response.hex()),self.catalog)
        self.assertEqual(caught.exception.outcome,'dispatch_returned')

    def test_schema_change_arrays_and_invalid_components(self):
        plan=self.plan(value=[{'X':1,'Y':2},{'X':3,'Y':4}],dimension=2)
        self.assertEqual(plan.data,struct.pack('<dddd',1,2,3,4))
        self.descriptors[13].properties[0]['type']='ObjectProperty'
        with self.assertRaises(ValueError): self.plan(value={'X':1,'Y':2})

    def test_capability_handshake_and_transport_reject_before_write(self):
        transport=Transport()
        transport.retained_protocol=transport.stable_identity_protocol=transport.object_assignment_protocol=1
        with patch('expedition33.sdk.SessionTransport',return_value=transport):
            with self.assertRaisesRegex(RuntimeQueryError,'POD value backend handshake'): Session(pod_values=True)
        self.assertTrue(transport._closed)
        transport=Transport()
        transport.retained_protocol=transport.stable_identity_protocol=transport.object_assignment_protocol=transport.pod_value_protocol=1
        with patch('expedition33.sdk.SessionTransport',return_value=transport) as factory:
            with Session(pod_values=True) as session:
                self.assertTrue(session.supports_pod_values)
                self.assertIn('research-probe-v11',str(factory.call_args.kwargs['_executable']))
        native=object.__new__(SessionTransport)
        native._closed=False; native._owner=threading.get_ident(); native.reflected_protocol=1
        stream=StringIO(); native._process=SimpleNamespace(stdin=stream)
        with self.assertRaisesRegex(ValueError,'POD value'): native.command('reflected-invoke',wire.encode_plan(self.plan(returned=True)))
        self.assertEqual(stream.getvalue(),'')

    def test_python_packets_match_native_profiles(self):
        executable=Path(__file__).resolve().parents[1]/'build/invocation-fixture/invocation_fixture.exe'
        if not executable.exists(): self.skipTest('Native invocation fixture not built')
        values=({'X':1,'Y':2},{'R':1,'G':0,'B':0,'A':1},{'Left':0,'Top':0,'Right':5,'Bottom':5},
                {'Minimum':{'X':0,'Y':0},'Maximum':{'X':1,'Y':1}})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'packet.bin'
            for index,value in enumerate(values,13):
                path.write_bytes(wire.encode_plan(self.plan(index,value)))
                result=subprocess.run([str(executable),str(path),'--pod'],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout.strip()),(0,'0'))
                result=subprocess.run([str(executable),str(path)],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout.strip()),(1,'300'))
