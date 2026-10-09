"""Argument planning boundaries; these tests do not prove engine execution."""
from dataclasses import replace
from types import SimpleNamespace
import struct
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.invocation import prepare_call, UnsupportedInvocation, PARM, OUT, RETURN, REFERENCE
from test_catalog import fixture


class InvocationTests(unittest.TestCase):
    def setUp(self):
        objects, classes = fixture()
        classes.append(ClassRelation(6, 1, 'Function', 0, 256))
        objects.append(CatalogObject(123, 6, 1, 0x3000, 'Function', 'Class', 'Class', 1, -1, 0, 0, 0))
        objects.append(CatalogObject(123, 7, 1, 0x4000, 'Specimen', 'Function', 'Class', 6, 2, 1, 0, 0))
        self.catalog = Catalog(123, objects, classes)
        self.target, self.function = self.catalog.by_index[5], self.catalog.by_index[7]

    def field(self, name, kind, offset, width, flags=PARM, dimension=1, **extra):
        return dict(name=name, type=kind, offset=offset, element_size=width, dimension=dimension,
                    flags=flags, owner_index=7, **extra)

    def plan(self, rows, arguments, size, returned=65535, extent=None):
        descriptor = SimpleNamespace(owners=({'index':7, 'size':size if extent is None else extent},),
            properties=rows, function={'params_size':size, 'return_offset':returned, 'flags':0x400, 'entry_rva':'0x1234'})
        with patch('expedition33.invocation.describe', return_value={7:descriptor}):
            return prepare_call(self.catalog, self.target, self.function, arguments)

    def test_layout_distinguishes_parameter_bytes_from_allocation_extent(self):
        rows = [self.field('Value','IntProperty',0,4),
                self.field('Result','BoolProperty',4,1,PARM|RETURN, bool_encoding='0xff010001'),
                self.field('Local','StrProperty',8,16,0)]
        plan = self.plan(rows, {'Value':7}, 5, 4, 24)
        self.assertEqual(plan.data, struct.pack('<iB',7,0))
        self.assertEqual((plan.parameter_size,plan.allocation_extent), (5,24))
        self.assertEqual(len(plan.parameters),2)

    def test_packed_booleans_share_byte_but_cannot_overlap_bits(self):
        rows = [self.field('A','BoolProperty',0,1,bool_encoding='0x01010001'),
                self.field('B','BoolProperty',0,1,bool_encoding='0x02020001')]
        self.assertEqual(self.plan(rows, {'A':True,'B':True},1).data,b'\x03')
        rows[1]['bool_encoding']='0x01010001'
        with self.assertRaises(ValueError): self.plan(rows, {'A':True,'B':True},1)

    def test_object_patches_preserve_identity_without_copying_addresses(self):
        cls = self.catalog.by_index[2]
        row = self.field('Object','ObjectProperty',0,8,property_class_index=2,
            property_class_serial=cls.serial,property_class_name=cls.name,property_class_address=hex(cls.address))
        plan = self.plan([row], {'Object':self.target},8)
        self.assertEqual(plan.data,bytes(8))
        self.assertEqual(plan.objects[0].object,self.target)
        for bad, error in ((self.target.address, ValueError), (replace(self.target,serial=999), RuntimeQueryError),
                           (self.catalog.by_index[1], ValueError)):
            with self.assertRaises(error): self.plan([row], {'Object':bad},8)

    def test_class_constraint_checks_the_class_object_itself(self):
        cls = self.catalog.by_index[2]
        row = self.field('Class','ClassProperty',0,8,meta_class_index=2,
            meta_class_serial=cls.serial,meta_class_name=cls.name,meta_class_address=hex(cls.address))
        plan = self.plan([row], {'Class':self.catalog.by_index[3]},8)
        self.assertEqual(plan.objects[0].object.index,3)
        with self.assertRaises(ValueError): self.plan([row], {'Class':self.catalog.by_index[0]},8)

    def test_explicit_inputs_ref_outputs_and_scalar_validation(self):
        rows = [self.field('InOut','IntProperty',0,4,PARM|OUT|REFERENCE),
                self.field('Output','IntProperty',4,4,PARM|OUT)]
        self.assertEqual(self.plan(rows,{'InOut':-9},8).data,struct.pack('<ii',-9,0))
        for args in ({},{'InOut':True},{'InOut':2**31},{'InOut':0,'Output':1}):
            with self.assertRaises(ValueError): self.plan(rows,args,8)
        row = self.field('Numbers','FloatProperty',0,4,dimension=2)
        self.assertEqual(self.plan([row],{'Numbers':[1,2]},8).data,struct.pack('<ff',1,2))
        for value in ([1], [1,float('inf')], [1,1e100], [1,10**1000]):
            with self.assertRaises(ValueError): self.plan([row],{'Numbers':value},8)

    def test_rejects_unsupported_return_even_without_inputs(self):
        row = self.field('Result','StructProperty',0,24,PARM|RETURN)
        with self.assertRaises(UnsupportedInvocation): self.plan([row],{},24,0)

    def test_invalid_layout_and_return_contracts(self):
        row = self.field('Result','IntProperty',0,4,PARM|RETURN)
        for size, ret, extent in ((4,65535,4),(4,2,4),(3,0,4),(4,0,3)):
            with self.assertRaises(ValueError): self.plan([row],{},size,ret,extent)
        row = self.field('Value','IntProperty',0,4)
        with self.assertRaises(ValueError): self.plan([row,row],{'Value':0},4)

    def test_target_owner_and_function_kind_rejected_before_describing(self):
        with patch('expedition33.invocation.describe') as read:
            with self.assertRaises(ValueError):
                prepare_call(self.catalog,self.catalog.by_index[1],self.function,{})
            with self.assertRaises(ValueError):
                prepare_call(self.catalog,self.target,self.target,{})
            read.assert_not_called()


if __name__ == '__main__': unittest.main()
