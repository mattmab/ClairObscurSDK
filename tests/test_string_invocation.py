import struct
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import test_invocation
from expedition33.invocation import prepare_call, decode_result, UnsupportedInvocation
from expedition33 import _string_wire as wire
from expedition33.catalog import Catalog, CatalogObject, ClassRelation

class StringInputTests(unittest.TestCase):
    def test_exact_object_timer_signatures_only(self):
        def field(name,kind,offset,width,flags,constraint=None):
            return SimpleNamespace(name=name,kind=kind,offset=offset,width=width,dimension=1,
                flags=flags,constraint=SimpleNamespace(name=constraint) if constraint else None)
        inputs=(field('Object','ObjectProperty',0,8,0x18001000000280,'Object'),
                field('FunctionName','StrProperty',8,16,0x18000000000280))
        self.assertTrue(wire.audited_signature(0x3858580,0x4022403,24,24,65535,inputs))
        active=inputs+(field('ReturnValue','BoolProperty',24,1,0x18001040000780),)
        self.assertTrue(wire.audited_signature(0x3858fc0,0x14022403,25,32,24,active))
        self.assertFalse(wire.audited_signature(0x3858fc1,0x14022403,25,32,24,active))
        self.assertFalse(wire.audited_signature(0x3858fc0,0x14022403,32,32,24,active))
        inputs[1].name='OtherString'
        self.assertFalse(wire.audited_signature(0x3858580,0x4022403,24,24,65535,inputs))
    def test_save_slot_signatures_preserve_input_and_output_types(self):
        def f(name,kind,offset,width,flags,constraint=None):
            return SimpleNamespace(name=name,kind=kind,offset=offset,width=width,dimension=1,
                flags=flags,constraint=SimpleNamespace(name=constraint) if constraint else None)
        load=(f('SlotName','StrProperty',0,16,0x18000000000280),
              f('UserIndex','IntProperty',16,4,0x18001040000282),
              f('ReturnValue','ObjectProperty',24,8,0x18001000000780,'SaveGame'))
        self.assertTrue(wire.audited_signature(0x373c5c0,0x4022403,32,32,24,load))
        load[2].constraint.name='Object'
        self.assertFalse(wire.audited_signature(0x373c5c0,0x4022403,32,32,24,load))
        save=(f('SaveGameObject','ObjectProperty',0,8,0x18001000000280,'SaveGame'),
              f('SlotName','StrProperty',8,16,0x18000000000280),
              f('UserIndex','IntProperty',24,4,0x18001040000282),
              f('ReturnValue','BoolProperty',28,1,0x18001040000780))
        self.assertTrue(wire.audited_signature(0x3740310,0x4022403,29,32,28,save))
        save[2].offset=16
        self.assertFalse(wire.audited_signature(0x3740310,0x4022403,29,32,28,save))
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
    def test_save_path_helper_plans_string_v5_and_copies_owned_return(self):
        self.descriptor.owners=[dict(index=7,size=56)]
        self.descriptor.properties=[self.p.field('SaveName','StrProperty',0,16,2251799813685908),self.p.field('ReturnValue','StrProperty',16,16,2251799813687168)]
        self.descriptor.function=dict(params_size=32,return_offset=16,flags=474218496,entry_rva='0x13937a0')
        plan=prepare_call(self.p.catalog,self.p.target,self.p.function,{'SaveName':'EXPEDITION_9'},string_values=True)
        self.assertEqual(plan.wire_version,5)
        sent=wire.encode_plan(plan,dict(plan.texts));reply=bytearray(sent);struct.pack_into('<II',reply,32,1,0)
        output=wire.encode_units('native/path/EXPEDITION_9');at=wire.SLOTS_AT+wire.SLOT_SIZE
        wire.SLOT_HEADER.pack_into(reply,at,1,len(output)//2);reply[at+8:at+8+len(output)]=output
        decoded=wire.decode_reply(sent,reply.hex())
        result=decode_result(plan,decoded.call,self.p.catalog,texts=decoded.texts)
        self.assertEqual(result.return_value,'native/path/EXPEDITION_9')
        self.descriptor.function['flags']^=1
        with self.assertRaises(UnsupportedInvocation):prepare_call(self.p.catalog,self.p.target,self.p.function,{'SaveName':'EXPEDITION_9'},string_values=True)
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


class TextureImportStringTests(unittest.TestCase):
    def test_save_slot_signatures_preserve_input_and_output_types(self):
        def f(name,kind,offset,width,flags,constraint=None):
            return SimpleNamespace(name=name,kind=kind,offset=offset,width=width,dimension=1,
                flags=flags,constraint=SimpleNamespace(name=constraint) if constraint else None)
        load=(f('SlotName','StrProperty',0,16,0x18000000000280),
              f('UserIndex','IntProperty',16,4,0x18001040000282),
              f('ReturnValue','ObjectProperty',24,8,0x18001000000780,'SaveGame'))
        self.assertTrue(wire.audited_signature(0x373c5c0,0x4022403,32,32,24,load))
        load[2].constraint.name='Object'
        self.assertFalse(wire.audited_signature(0x373c5c0,0x4022403,32,32,24,load))
        save=(f('SaveGameObject','ObjectProperty',0,8,0x18001000000280,'SaveGame'),
              f('SlotName','StrProperty',8,16,0x18000000000280),
              f('UserIndex','IntProperty',24,4,0x18001040000282),
              f('ReturnValue','BoolProperty',28,1,0x18001040000780))
        self.assertTrue(wire.audited_signature(0x3740310,0x4022403,29,32,28,save))
        save[2].offset=16
        self.assertFalse(wire.audited_signature(0x3740310,0x4022403,29,32,28,save))
    def setUp(self):
        self.p = test_invocation.InvocationTests()
        self.p.setUp()
        texture = CatalogObject(123, 8, 1, 0x9000, 'Texture2D', 'Class', 'Class', 1, -1, 0, 0, 0)
        self.catalog = Catalog(123, list(self.p.catalog.objects) + [texture],
            list(self.p.catalog.classes.values()) + [ClassRelation(8, 1, 'Texture2D', 0, 200)])
        obj = self.catalog.by_index[0]
        self.rows = [self.p.field('WorldContextObject', 'ObjectProperty', 0, 8, 0x18001000000280,
            property_class_index=obj.index, property_class_serial=obj.serial,
            property_class_name=obj.name, property_class_address=hex(obj.address)),
            self.p.field('Filename', 'StrProperty', 8, 16, 0x18000000000280),
            self.p.field('ReturnValue', 'ObjectProperty', 24, 8, 0x18001000000780,
                property_class_index=texture.index, property_class_serial=texture.serial,
                property_class_name=texture.name, property_class_address=hex(texture.address))]
        self.descriptor = SimpleNamespace(owners=[dict(index=7, size=32)], properties=self.rows,
            function=dict(params_size=32, return_offset=24, flags=0x4022403, entry_rva='0x3854c30'))

    def plan(self):
        with patch('expedition33.invocation.describe', return_value={7:self.descriptor}):
            return prepare_call(self.catalog, self.p.target, self.p.function,
                dict(WorldContextObject=self.p.target, Filename='loading.png'), string_values=True)

    def test_exact_texture_import_keeps_object_patch_and_string_at_offset_eight(self):
        plan = self.plan()
        sent = wire.encode_plan(plan, dict(plan.texts))
        self.assertEqual((plan.wire_version, plan.return_offset), (5, 24))
        self.assertEqual([(p.offset, p.object) for p in plan.objects], [(0, self.p.target)])
        self.assertEqual(wire.SLOT_HEADER.unpack_from(sent, wire.SLOTS_AT)[0], 1)
        from expedition33 import _invocation_wire as call
        self.assertEqual(call.FIELD.unpack_from(sent, call.FIELDS_AT + call.FIELD.size)[:4],
                         (16, 8, 16, 1))
        self.assertEqual(plan.data, bytes(32))

    def test_nearby_signature_or_return_class_is_rejected(self):
        for key, value in (('entry_rva', '0x3854c31'), ('flags', 0x4022402),
                           ('return_offset', 16), ('params_size', 31)):
            original = self.descriptor.function[key]
            self.descriptor.function[key] = value
            with self.assertRaises(ValueError):
                self.plan()
            self.descriptor.function[key] = original
        plan = self.plan()
        changed = replace(plan.parameters[2], constraint=self.catalog.by_index[0])
        with self.assertRaises(ValueError):
            wire.encode_plan(replace(plan, parameters=plan.parameters[:2] + (changed,)), dict(plan.texts))
