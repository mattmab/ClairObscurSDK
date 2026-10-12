import unittest
from dataclasses import replace
from types import SimpleNamespace
from expedition33.invocation import CallPlan, Parameter, ObjectPatch
from expedition33._sequence_wire import settings, encode_plan
from expedition33._sequence_owner import validate_request, HEADER, SIZE

class SequenceCreationTests(unittest.TestCase):
    def plan(self):
        obj=SimpleNamespace(index=1,serial=2,address=0x10000)
        names=('WorldContextObject','LevelSequence','Settings','OutActor','ReturnValue')
        offsets=(0,8,16,56,64)
        flags=(6755468160533120,6755468160533120,4503668346847360,6755468160533376,6755468160534400)
        params=tuple(Parameter(n,'SequencePlaybackSettings' if i==2 else 'ObjectProperty',offsets[i],
            40 if i==2 else 8,1,flags[i],constraint=obj) for i,n in enumerate(names))
        return CallPlan(obj,obj,71443459,0x321b6a0,72,72,64,params,bytes(16)+settings()+bytes(16),
            (ObjectPatch(0,obj),ObjectPatch(8,obj)),7)

    def test_exact_contract(self):
        self.assertEqual(len(encode_plan(self.plan())),26192)

    def test_reject_autoplay_looping_and_hidden_bits(self):
        plan=self.plan()
        for i in range(40):
            if 20<=i<24: continue
            data=bytearray(plan.data); data[16+i]^=128
            with self.subTest(offset=i),self.assertRaises(ValueError):
                encode_plan(replace(plan,data=bytes(data)))

    def test_reject_rates_and_contract_changes(self):
        for rate in (True,0,.249,2.001,float('nan'),float('inf')):
            with self.subTest(rate=rate),self.assertRaises(ValueError): settings(rate)
        plan=self.plan()
        for change in (dict(entry_rva=0),dict(return_offset=56),dict(wire_version=2),
                       dict(objects=tuple(reversed(plan.objects))),dict(parameter_size=64)):
            with self.subTest(change=change),self.assertRaises(ValueError): encode_plan(replace(plan,**change))

    def test_owner_close_never_accepts_cleanup_payload(self):
        request=HEADER.pack(1,2,1,0,0,0)+bytes(SIZE-HEADER.size)
        validate_request(request)
        with self.assertRaises(ValueError): validate_request(request[:-1]+b'\1')

if __name__=='__main__': unittest.main()
