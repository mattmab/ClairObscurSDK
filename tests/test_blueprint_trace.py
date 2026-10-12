from dataclasses import replace
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
import struct
from expedition33.tracing import prepare_trace, decode_trace, ObservedObject


class BlueprintTraceTests(TestCase):
    def plan(self, enabled=True, entry='0x13937a0', out=False):
        fn=NS(pid=123,index=2,class_index=3,outer_index=1,name='OnCharacterReceivedDamages')
        catalog=NS(resolve=lambda _:fn,find_class=lambda _:NS(index=3),ancestors=lambda _:(3,),
                   by_index={1:NS(name='BP_BattleSummaryStatsManager_C')})
        names=('TargetCharacter','SourceCharacter','ReceivedDamages','BattleDamages')
        parameters=tuple(NS(name=n,kind='DoubleProperty' if i==2 else 'ObjectProperty',offset=i*8,
                            width=8,dimension=1,flags=0x180 if out else 0x80) for i,n in enumerate(names))
        descriptor=NS(function={'flags':0x0c020000,'entry_rva':entry})
        with patch('expedition33.tracing.describe',return_value={2:descriptor}), \
             patch('expedition33.tracing._parameter_schema',return_value=(32,128,65535,parameters)):
            return prepare_trace(catalog,fn,blueprint=enabled)

    def test_capability_signature_and_out_guards(self):
        for args in ({'enabled':False},{'entry':'0x1234'},{'out':True}):
            with self.assertRaises(ValueError): self.plan(**args)
        p=self.plan()
        self.assertEqual(p.phase,'entry')
        self.assertEqual(p.capture_size,56)
        self.assertEqual([f.destination_offset for f in p.fields],[0,16,32,40])

    def test_copied_identity_session_null_and_damage(self):
        p=self.plan()
        data=struct.pack('<iiQiiQdiiQ',10,0,0x10000,11,7,0x20000,123.5,-1,0,0)
        values=decode_trace(p,data,session=456).arguments
        self.assertEqual(values['TargetCharacter'],ObservedObject(456,123,10,0,0x10000))
        self.assertEqual(values['SourceCharacter'].serial,7)
        self.assertEqual(values['ReceivedDamages'],123.5)
        self.assertIsNone(values['BattleDamages'])
        with self.assertRaises(ValueError): decode_trace(p,data)
        for invalid in ((-1,0,0x10000),(1,-1,0x10000),(1,0,0x10001)):
            with self.assertRaises(ValueError): decode_trace(p,struct.pack('<iiQ',*invalid)+data[16:],session=456)
