import json, struct, pathlib, unittest, copy
from types import SimpleNamespace as NS
from unittest.mock import patch
from expedition33 import _pod_values as p, _invocation_wire as wire
from expedition33.invocation import _parameter_schema, UnsupportedInvocation

ROOT=pathlib.Path(__file__).resolve().parents[1]

class TimespanTests(unittest.TestCase):
    def test_signed_exact_return(self):
        for n in (-(1<<63),-1,0,1,(1<<63)-1):
            value=p.decode(p.TIMESPAN,struct.pack('<q',n))
            self.assertEqual(value.ticks,n)
            with self.assertRaises(Exception):value.ticks=1
            if 0<=n<=864000000000:self.assertEqual(p.encode(p.TIMESPAN,value),struct.pack('<q',n))
            else:
                with self.assertRaises(ValueError):p.encode(p.TIMESPAN,value)
        for size in (0,7,9):
            with self.assertRaises(ValueError):p.decode(p.TIMESPAN,bytes(size))
        for n in (True,1.0,1<<63,-(1<<63)-1):
            with self.assertRaises(ValueError):p.TimespanValue(n)
        self.assertEqual(p.TimespanValue(25_000_000).seconds,2.5)
        self.assertEqual(p.TimespanValue(-25_000_000).seconds,-2.5)

    def test_empty_exact_schema(self):
        raw=json.loads((ROOT/'evidence/coverage-compiled-data-schema.json').read_text())['5759']
        obj=NS(index=5759,class_name='ScriptStruct')
        d=NS(object=obj,owners=raw['owners'],properties=raw['properties'])
        catalog=NS(resolve=lambda x:x,path_name=lambda x:p.TIMESPAN)
        self.assertEqual(p.validate_profile(catalog,d,{}).width,8)
        for key,value in (('size',16),('super','0x1234')):
            bad=copy.deepcopy(d);bad.owners[0][key]=value
            with self.assertRaises(ValueError):p.validate_profile(catalog,bad,{})
        bad=copy.deepcopy(d);bad.properties=[{}]
        with self.assertRaises(ValueError):p.validate_profile(catalog,bad,{})

    def test_only_two_exact_getters(self):
        rows=json.loads((ROOT/'evidence/coverage-compiled-data-schema.json').read_text())
        for index,name in ((16302,'GetDuration'),(16315,'GetTime')):
            raw=rows[str(index)];fn=NS(index=index);constraint=NS(index=5759)
            catalog=NS(path_name=lambda x:'/Script/MediaAssets.MediaPlayer:'+name)
            d=NS(function=raw['function'],owners=raw['owners'],properties=raw['properties'])
            with patch('expedition33.invocation._observed_pod_profile',return_value=(constraint,p.PROFILES[p.TIMESPAN])):
                self.assertEqual(_parameter_schema(catalog,fn,d,pod_values=True)[3][0].pod_profile,p.TIMESPAN)
                for key,value in (('entry_rva','0x1'),('flags',0),('params_size',16)):
                    bad=copy.deepcopy(d);bad.function[key]=value
                    with self.assertRaises((ValueError,UnsupportedInvocation)):_parameter_schema(catalog,fn,bad,pod_values=True)
                bad=copy.deepcopy(d);bad.properties[0]['flags']=0x80
                with self.assertRaises(UnsupportedInvocation):_parameter_schema(catalog,fn,bad,pod_values=True)

    def test_seek_schema_is_exact_and_rejects_layout_substitutions(self):
        rows=json.loads((ROOT/'evidence/media-seek-schema.json').read_text())
        fn=NS(index=16352);constraint=NS(index=5759)
        catalog=NS(path_name=lambda x:'/Script/MediaAssets.MediaPlayer:Seek')
        d=NS(function=rows['function'],owners=rows['owners'],properties=rows['properties'])
        with patch('expedition33.invocation._observed_pod_profile',return_value=(constraint,p.PROFILES[p.TIMESPAN])):
            self.assertEqual(_parameter_schema(catalog,fn,d,pod_values=True)[3][0].pod_profile,p.TIMESPAN)
            for key,value in (('entry_rva','0x1'),('params_size',16),('return_offset',0),('flags',0)):
                bad=copy.deepcopy(d);bad.function[key]=value
                with self.assertRaises((ValueError,UnsupportedInvocation)):_parameter_schema(catalog,fn,bad,pod_values=True)
            for key,value in (('offset',0),('flags',0x80),('bool_encoding','0x1010001')):
                bad=copy.deepcopy(d);bad.properties[1][key]=value
                with self.assertRaises((ValueError,UnsupportedInvocation)):_parameter_schema(catalog,fn,bad,pod_values=True)

    def test_wire_and_capability(self):
        from expedition33.sdk import Session
        identity=NS(index=1,serial=2,address=0x1234)
        parameter=NS(kind='StructProperty',pod_profile=p.TIMESPAN,name='ReturnValue',offset=0,width=8,dimension=1,flags=6755468160534400,boolean_encoding=0,constraint=identity)
        plan=NS(parameter_size=8,allocation_extent=8,parameters=(parameter,),objects=(),data=bytes(8),wire_version=2,return_offset=0,function_flags=1417806851,entry_rva=0x3208990,target=identity,function=identity)
        packet=wire.encode_plan(plan)
        self.assertEqual(struct.unpack_from('<I',packet,wire.FIELDS_AT)[0],20)
        gate=NS(supports_frame_time_values=True,supports_timespan_values=False)
        with self.assertRaises(UnsupportedInvocation):Session._check_frame_time_plan(gate,plan)
        gate.supports_timespan_values=True;Session._check_frame_time_plan(gate,plan)
        from expedition33._session import SessionTransport
        import io, threading
        for cap in (None,False,True,0,2):
            native=SessionTransport.__new__(SessionTransport)
            native._owner=threading.get_ident();native._closed=False
            native.reflected_protocol=native.pod_value_protocol=1
            native.timespan_values_protocol=cap
            native._process=NS(stdin=io.StringIO())
            with self.assertRaisesRegex(ValueError,'Timespan'):
                native.command('reflected-invoke',packet)
            self.assertEqual(native._process.stdin.getvalue(),'')

if __name__=='__main__':unittest.main()

