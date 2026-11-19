import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_original import _Owner

class NarrativeHoldTests(unittest.TestCase):
    def test_reuses_only_active_exact_identity_in_its_open_scope(self):
        owner=_Owner.__new__(_Owner);owner.resources=None;owner.scope=N(_check=Mock());owner.held=[];owner._held_by_identity={}
        obj=N(pid=10,index=1,serial=2,address=0x10000)
        first=N(object=obj,active=True);second=N(object=obj,active=True)
        with patch('expedition33._stable_lease.acquire_stable',side_effect=((first,None),(second,None))) as acquire:
            self.assertIs(owner.hold(obj),first);self.assertIs(owner.hold(obj),first)
            self.assertEqual(acquire.call_count,1)
            first.active=False;self.assertIs(owner.hold(obj),second);self.assertEqual(acquire.call_count,2)
        owner.scope._check.side_effect=RuntimeError('closed')
        with self.assertRaisesRegex(RuntimeError,'closed'):owner.hold(obj)
    def test_different_generation_or_process_is_not_reused(self):
        owner=_Owner.__new__(_Owner);owner.resources=None;owner.scope=N(_check=Mock());owner.held=[];owner._held_by_identity={}
        a=N(pid=10,index=1,serial=2,address=0x10000);b=N(pid=10,index=1,serial=3,address=0x10000);c=N(pid=11,index=1,serial=2,address=0x10000)
        with patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,obj:(N(object=obj,active=True),None)) as acquire:
            for obj in (a,b,c):owner.hold(obj)
            self.assertEqual(acquire.call_count,3)
