import sys, pathlib, unittest, struct, math, ast, tempfile, json
from types import SimpleNamespace
ROOT=pathlib.Path(__file__).resolve().parents[1]
STAGE=ROOT
from expedition33 import _pod_values as p

class TimingTests(unittest.TestCase):
    def test_exact_copy(self):
        raw=struct.pack('<ifii',-2147483648,.75,2147483647,-2147483648)
        value=p.decode(p.QUALIFIED_FRAME_TIME,raw)
        self.assertEqual(value['Time']['FrameNumber']['Value'],-2147483648)
        self.assertEqual(value['Time']['SubFrame'],.75)
        self.assertEqual(value['Rate']['Numerator'],2147483647)
        self.assertEqual(p.encode(p.QUALIFIED_FRAME_TIME,value),raw)
        with self.assertRaises(TypeError): value['Rate']['Numerator']=0

    def test_zero_output_and_invalid(self):
        self.assertEqual(p.encode(p.QUALIFIED_FRAME_TIME,p.decode(p.QUALIFIED_FRAME_TIME,bytes(16))),bytes(16))
        for x in (math.inf,-math.inf,math.nan):
            with self.assertRaises(ValueError): p.decode(p.QUALIFIED_FRAME_TIME,struct.pack('<ifii',1,x,24,1))
        for x in (True,1.0,2**31,-2**31-1):
            with self.assertRaises(ValueError): p.encode(p.FRAME_NUMBER,{'Value':x})
        with self.assertRaises(ValueError): p.decode(p.QUALIFIED_FRAME_TIME,bytes(15))

    def test_recorded_schema_and_rejection(self):
        def norm(v):
            if isinstance(v,dict):
                if 'entries' in v: return {z['key']:norm(z['value']) for z in v['entries']}
                if 'items' in v: return [norm(x) for x in v['items']]
                return {k:norm(x) for k,x in v.items()}
            return v
        raw=norm(json.loads((ROOT/'evidence/v53-frame-time-schema.json').read_text()))
        objects={path:SimpleNamespace(**raw[path]['object']) for path in p.FRAME_PROFILES}
        descriptors={obj.index:SimpleNamespace(object=obj,owners=raw[path]['owners'],properties=raw[path]['properties']) for path,obj in objects.items()}
        catalog=SimpleNamespace(by_index={o.index:o for o in objects.values()},resolve=lambda o:o,path_name=lambda o:next(k for k,v in objects.items() if v is o))
        qualified=descriptors[objects[p.QUALIFIED_FRAME_TIME].index]
        self.assertEqual(p.validate_profile(catalog,qualified,descriptors).width,16)
        from unittest.mock import patch
        from expedition33.invocation import _observed_pod_profile
        root=qualified.object
        row={'struct_index':root.index,'struct_serial':root.serial,'struct_name':root.name}
        gathered={}
        def describe_rows(_catalog, requested, _metadata):
            return {o.index:descriptors[o.index] for o in requested}
        with patch('expedition33.invocation._describe_observed',side_effect=describe_rows):
            _, profile=_observed_pod_profile(catalog,row,gathered)
        self.assertEqual(profile.width,16)
        self.assertEqual(set(gathered),set(descriptors))
        sub=descriptors[objects[p.FRAME_TIME].index].properties[1]
        sub['flags']=0
        with self.assertRaises(ValueError):p.validate_profile(catalog,qualified,descriptors)

    def test_wire_and_capability(self):
        from expedition33 import _invocation_wire as wire
        from expedition33.sdk import Session
        from expedition33.invocation import UnsupportedInvocation
        identity=SimpleNamespace(index=1,serial=2,address=0x1234)
        parameter=SimpleNamespace(kind='StructProperty',pod_profile=p.QUALIFIED_FRAME_TIME,name='ReturnValue',offset=0,width=16,dimension=1,flags=0x580,boolean_encoding=0,constraint=identity)
        plan=SimpleNamespace(parameter_size=16,allocation_extent=16,parameters=(parameter,),objects=(),data=bytes(16),wire_version=2,return_offset=0,function_flags=0x400,entry_rva=1,target=identity,function=identity)
        packet=wire.encode_plan(plan)
        self.assertEqual(struct.unpack_from('<I',packet,wire.FIELDS_AT)[0],19)
        class Gate:
            supports_frame_time_values=False
        with self.assertRaises(UnsupportedInvocation):Session._check_frame_time_plan(Gate(),plan)
        Gate.supports_frame_time_values=True
        Session._check_frame_time_plan(Gate(),plan)

    def test_source_parses(self):
        for file in (STAGE/'src').rglob('*.py'): ast.parse(file.read_text(encoding='utf-8'))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TimingTests)
    for name in ('test_pod_values','test_pod_invocation'):
        sys.path.insert(0,str(ROOT/'tests'))
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())

