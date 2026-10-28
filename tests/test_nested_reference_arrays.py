import copy,subprocess,unittest
from pathlib import Path
from expedition33.values import _struct_value,StoredArray
import test_struct_values

class NestedReferenceArrayTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_struct_values.StructValueTests();self.fixture.setUp()
        self.catalog=self.fixture.base.catalog
        self.obj=next(o for o in self.catalog.objects if o.index not in self.catalog.classes)
        self.reference={'$reference':dict(index=self.obj.index,serial=self.obj.serial,address=hex(self.obj.address),name=self.obj.name)}
    def row(self,length=None,items=None,kind='ObjectProperty'):
        items=[self.reference,None] if items is None else items
        return dict(name='Tracks',type='ArrayProperty',inner_type=kind,
                    value={'$array':dict(length=len(items) if length is None else length,items=items)})
    def decode(self,row):return _struct_value(self.catalog,self.fixture.struct([row])).fields['Tracks']
    def test_identity_checked_object_array_and_explicit_partial_prefix(self):
        result=self.decode(self.row())
        self.assertIsInstance(result,StoredArray);self.assertEqual(result.items,(self.obj,None))
        partial=self.decode(self.row(length=65,items=[None]*64))
        self.assertEqual(partial.length,65);self.assertEqual(len(partial.items),64)
    def test_stale_reference_wrong_schema_extent_and_class_rejected(self):
        bad=self.row();bad['value']['$array']['items'][0]=copy.deepcopy(self.reference)
        bad['value']['$array']['items'][0]['$reference']['serial']+=1
        with self.assertRaisesRegex(ValueError,'changed'):self.decode(bad)
        for row in (self.row(kind='IntProperty'),self.row(length=True),self.row(length=65,items=[None]),self.row(kind='ClassProperty')):
            with self.assertRaises(ValueError):self.decode(row)
    def test_native_stability_fixture(self):
        executable=Path(__file__).resolve().parents[1]/'build/stored-reference-array/stored_reference_array_fixture.exe'
        if not executable.exists():self.skipTest('Build stored reference array fixture first')
        result=subprocess.run([str(executable)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('partial prefix PASS',result.stdout)
    def test_frame_and_numeric_channel_arrays_validate_values_and_declared_type(self):
        from expedition33.values import StoredStruct
        from dataclasses import replace
        from types import SimpleNamespace
        by_index=dict(self.catalog.by_index)
        index=self.fixture.reference['index']
        by_index[index]=replace(by_index[index],class_name='ScriptStruct')
        self.catalog=SimpleNamespace(by_index=by_index,classes=self.catalog.classes)
        frame=self.fixture.struct([dict(name='Value',type='IntProperty',value=24000)])
        row=self.row(items=[frame],kind='StructProperty')
        row['inner_struct']={'$reference':self.fixture.reference}
        result=self.decode(row)
        self.assertIsInstance(result.items[0],StoredStruct)
        self.assertEqual(result.items[0].fields['Value'],24000)
        bad=copy.deepcopy(row);bad['inner_struct']['$reference']['serial']+=1
        with self.assertRaises(ValueError):self.decode(bad)
        self.assertEqual(self.decode(self.row(items=[1,-2],kind='IntProperty')).items,(1,-2))
        self.assertEqual(self.decode(self.row(items=[1,2.5],kind='DoubleProperty')).items,(1.,2.5))
        self.assertEqual(self.decode(self.row(items=[True,False],kind='BoolProperty')).items,(True,False))
        for kind,items in (('IntProperty',[True]),('ByteProperty',[256]),('UInt16Property',[-1]),
                           ('FloatProperty',[False]),('NameProperty',[None]),('BoolProperty',[1])):
            with self.assertRaises(ValueError):self.decode(self.row(items=items,kind=kind))
    def test_reference_closure_walk_accepts_array_wrapped_typed_depth(self):
        from expedition33.values import _missing_references
        value=self.fixture.struct([dict(name='Value',type='IntProperty',value=24000)])
        for _ in range(3):
            value=self.fixture.struct([dict(name='Times',type='ArrayProperty',inner_type='StructProperty',
                inner_struct={'$reference':self.fixture.reference},value={'$array':dict(length=1,items=[value])})])
        self.assertEqual(_missing_references(self.catalog,[dict(event='stored_value',value=value)]),set())

    def test_large_shallow_batch_keeps_reference_identity_checks(self):
        from expedition33.values import _missing_references
        from types import SimpleNamespace
        rows=[dict(event='stored_value',value=[None]*1000) for _ in range(300)]
        rows.append(dict(event='stored_value',value=self.reference))
        identity=(self.obj.index,self.obj.serial,self.obj.address)
        self.assertEqual(_missing_references(SimpleNamespace(by_index={}),rows),{identity})
        self.assertEqual(_missing_references(self.catalog,rows),set())
        malformed=copy.deepcopy(self.reference);malformed['$reference']['extra']=1
        rows.append(dict(event='stored_value',value=malformed))
        with self.assertRaisesRegex(Exception,'Invalid nested stored reference'):
            _missing_references(self.catalog,rows)

    def test_reference_work_and_depth_limits_are_distinct(self):
        from expedition33.values import _missing_references
        rows=[dict(event='stored_value',value=[None]*1023)]*1024
        self.assertEqual(_missing_references(self.catalog,rows),set())
        with self.assertRaisesRegex(Exception,'traversal limit'):
            _missing_references(self.catalog,rows+[dict(event='stored_value',value=None)])
        value=None
        for _ in range(33):value=[value]
        with self.assertRaisesRegex(Exception,'reference depth'):
            _missing_references(self.catalog,[dict(event='stored_value',value=value)])
