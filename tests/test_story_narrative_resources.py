import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from expedition33.story_narrative_resources import NarrativeResources
from expedition33 import _story_item_wire as wire

class NarrativeResourceTests(unittest.TestCase):
    def fixture(self):
        r=NarrativeResources.__new__(NarrativeResources);r.scope=N(_check=Mock());r.held={};r.assets={}
        return r
    def test_loaded_asset_lease_is_borrowed_without_another_acquisition(self):
        r=self.fixture();obj=N(pid=1,index=2,serial=3,address=0x10000,class_name='SoundWave')
        lease=N(active=True,object=obj);r.held[(1,2,3,0x10000)]=lease
        with patch('expedition33.story_narrative_resources.acquire_stable') as acquire:
            self.assertIs(r.hold(obj),lease);acquire.assert_not_called()
            lease.active=False
            with self.assertRaisesRegex(RuntimeError,'expired'):r.hold(obj)
    def test_process_resource_pool_refuses_transient_world_context(self):
        r=self.fixture()
        for kind in ('World','BP_DialogueSystemComponent_C','PlayerController'):
            obj=N(pid=1,index=2,serial=3,address=0x10000,class_name=kind)
            with self.assertRaisesRegex(ValueError,'world objects'):r.hold(obj)
    def test_explicit_original_asset_names_keep_private_api_restricted(self):
        obj=N(index=2,serial=3,address=0x10000);held=N(object=obj,_token=4)
        path='/Game/Audio/Test.Test'
        with self.assertRaises(ValueError):wire.names(1,held,held,path)
        packet=wire.names(1,held,held,path,original=True);wire.validate(packet)
        self.assertEqual(int.from_bytes(packet[4:8],'little'),243)
        for bad in ('/Game/../Test.Test','/Game/Test.Other','/Game//Test.Test','/Script/Engine.Test','/Game/Test.Test:Subobject'):
            with self.assertRaises(ValueError):wire.names(1,held,held,bad,original=True)
