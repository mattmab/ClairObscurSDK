import unittest
from dataclasses import replace
from types import SimpleNamespace
from expedition33.invocation import CallPlan,Parameter
from expedition33._asset_wire import encode_plan
import struct


class AssetWireTests(unittest.TestCase):
    def plan(self):
        identity=SimpleNamespace(index=1,serial=2,address=0x10000)
        a=Parameter('Asset','SoftObjectProperty',0,40,1,7881299347898496,constraint=identity)
        r=Parameter('ReturnValue','ObjectProperty',40,8,1,6755468160534400,constraint=identity)
        data=bytearray(48); struct.pack_into('<I',data,8,123); struct.pack_into('<I',data,16,456)
        return CallPlan(identity,identity,67249155,0x3860130,48,48,40,(a,r),bytes(data),(),6)

    def test_exact_contract(self):
        wire=encode_plan(self.plan())
        self.assertEqual(len(wire),26192)
        self.assertEqual(struct.unpack_from('<I',wire)[0],6)

    def test_reject_native_owned_storage(self):
        plan=self.plan()
        for at in (*range(8),*range(24,48)):
            data=bytearray(plan.data); data[at]=1
            with self.subTest(at=at),self.assertRaises(ValueError):
                encode_plan(replace(plan,data=bytes(data)))
    def test_numbered_names_are_bounded_and_do_not_admit_class_or_native_storage(self):
        plan=self.plan();data=bytearray(plan.data)
        struct.pack_into('<I',data,12,3);struct.pack_into('<I',data,20,3)
        self.assertTrue(encode_plan(replace(plan,data=bytes(data))))
        for at in (12,20):
            bad=bytearray(data);struct.pack_into('<I',bad,at,0x80000000)
            with self.assertRaises(ValueError):encode_plan(replace(plan,data=bytes(bad)))
        cls=replace(plan,entry_rva=0x3860250,data=bytes(data),parameters=(
            replace(plan.parameters[0],name='AssetClass',kind='SoftClassProperty'),
            replace(plan.parameters[1],kind='ClassProperty')))
        with self.assertRaises(ValueError):encode_plan(cls)

    def test_reject_other_functions_and_signatures(self):
        p=self.plan()
        for changes in (dict(entry_rva=0),dict(function_flags=0),dict(allocation_extent=64),
                        dict(parameter_size=40),dict(wire_version=2),dict(return_offset=0)):
            with self.subTest(changes=changes),self.assertRaises(ValueError): encode_plan(replace(p,**changes))
        for changes in (dict(flags=p.parameters[0].flags|0x100),dict(dimension=2),dict(width=32),
                        dict(kind='StructProperty'),dict(offset=8),dict(name='AssetClass')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                encode_plan(replace(p,parameters=(replace(p.parameters[0],**changes),p.parameters[1])))

if __name__=='__main__': unittest.main()
