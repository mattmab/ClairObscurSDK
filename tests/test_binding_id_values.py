import copy,struct,unittest
from types import SimpleNamespace as N
from expedition33._pod_values import BINDING_ID,GUID,PROFILES,encode,decode,validate_profile


def fixture():
    guid=N(index=1,serial=10,class_name='ScriptStruct');binding=N(index=2,serial=11,class_name='ScriptStruct')
    catalog=N(resolve=lambda o:o,by_index={1:guid,2:binding},path_name=lambda o:GUID if o.index==1 else BINDING_ID)
    guid_rows=[dict(owner_index=1,name=n,offset=i*4,element_size=4,dimension=1,type='IntProperty',
                    flags=6755469251052033,vtable_rva='0x6e10a98') for i,n in enumerate('ABCD')]
    rows=[dict(owner_index=2,name=n,offset=o,element_size=16 if i==0 else 4,dimension=1,
               type='StructProperty' if i==0 else 'IntProperty',flags=20266268116386305 if i==0 else 20266268116386304,
               vtable_rva='0x6e136a0' if i==0 else '0x6e10a98') for i,(n,o,_) in enumerate(PROFILES[BINDING_ID].fields)]
    rows[0].update(struct_index=1,struct_serial=10,struct_name='Guid')
    guid.name='Guid';binding.name='MovieSceneObjectBindingID'
    descriptors={1:N(object=guid,owners=[dict(index=1,size=16,super='0x0')],properties=guid_rows),
                 2:N(object=binding,owners=[dict(index=2,size=24,super='0x0')],properties=rows)}
    return catalog,descriptors


class BindingIdValuesTests(unittest.TestCase):
    def test_wire_kind_and_runtime_gate_are_separate_from_frame_timing(self):
        from expedition33 import _invocation_wire as wire
        from expedition33.sdk import Session
        from expedition33.invocation import UnsupportedInvocation
        identity=N(index=1,serial=2,address=0x10000)
        value=dict(Guid=dict(A=1,B=2,C=3,D=4),SequenceID=0,ResolveParentIndex=-1)
        parameter=N(kind='StructProperty',pod_profile=BINDING_ID,name='Binding',offset=0,width=24,
                    dimension=1,flags=0x80,boolean_encoding=0,constraint=identity)
        plan=N(parameter_size=24,allocation_extent=24,parameters=(parameter,),objects=(),data=encode(BINDING_ID,value),
               wire_version=2,return_offset=65535,function_flags=0x400,entry_rva=1,target=identity,function=identity)
        self.assertEqual(wire.FIELD.unpack_from(wire.encode_plan(plan),wire.FIELDS_AT)[0],26)
        class Gate:supports_sequence_binding_values=False
        with self.assertRaises(UnsupportedInvocation):Session._check_frame_time_plan(Gate(),plan)
        Gate.supports_sequence_binding_values=True;Session._check_frame_time_plan(Gate(),plan)
    def test_exact_24_byte_value_roundtrip_without_runtime_pointers(self):
        value=dict(Guid=dict(A=1,B=-2,C=3,D=-4),SequenceID=-2147483648,ResolveParentIndex=-1)
        raw=encode(BINDING_ID,value)
        self.assertEqual(raw,struct.pack('<6i',1,-2,3,-4,-2147483648,-1))
        copied=decode(BINDING_ID,raw);self.assertEqual(copied,value)
        with self.assertRaises(TypeError):copied['Guid']['A']=0
        for bad in (True,1.5,2**31,-2**31-1):
            with self.assertRaises(ValueError):encode(BINDING_ID,dict(value,SequenceID=bad))
        with self.assertRaises(ValueError):encode(BINDING_ID,dict(value,Address=123))
    def test_binding_schema_checks_package_fields_flags_and_nested_guid(self):
        catalog,descriptors=fixture()
        self.assertEqual(validate_profile(catalog,descriptors[2],descriptors),PROFILES[BINDING_ID])
        changes=(lambda ds:ds[2].properties[1].update(offset=20),
                 lambda ds:ds[2].properties[0].update(flags=0),
                 lambda ds:ds[2].properties[2].update(vtable_rva='0x6e11d38'),
                 lambda ds:ds[2].properties[0].update(struct_serial=99),
                 lambda ds:ds[1].properties[0].update(flags=0),
                 lambda ds:ds[2].owners[0].update(size=32))
        for change in changes:
            altered=copy.deepcopy(descriptors);change(altered)
            with self.assertRaises(ValueError):validate_profile(catalog,altered[2],altered)
