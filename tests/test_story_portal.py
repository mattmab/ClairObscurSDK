import struct,unittest
from expedition33.story_portal import validate,decode,SIZE,PortalHandoffError
from expedition33.zone_travel import validate_request

class PortalWireTests(unittest.TestCase):
    def test_registration_consumes_same_operation_route_observation_without_duplicate_queries(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock,patch
        from expedition33.story_portal import StoryPortal
        packet=bytearray(432)
        for i in range(6):struct.pack_into('<iiQ',packet,16+16*i,i+1,i+10,0x10000+8*i)
        catalog=object();system=object();owner=StoryPortal.__new__(StoryPortal)
        owner.scope=N(pid=7);owner.route={'spawn_tag':'Level.SpawnPoint.Test'}
        with patch('expedition33.story_portal.prepare_spawn_registration',return_value=(bytes(packet),catalog,system)) as prepare,\
                patch('expedition33.catalog.capture_selected') as duplicate,\
                patch('expedition33.story_dialogue.controller_dialogue_system') as component:
            actual=owner._observe_registration()
        prepare.assert_called_once_with(owner.scope,owner.route,owner.route['spawn_tag'])
        self.assertIs(actual[2],catalog);self.assertIs(actual[3],system)
        duplicate.assert_not_called();component.assert_not_called();self.assertIsNone(actual[4])

    def test_discovery_failure_yields_before_leases_and_native_registration(self):
        from contextlib import nullcontext
        from types import SimpleNamespace as N
        from unittest.mock import Mock,patch
        from expedition33 import RuntimeQueryError
        from expedition33.story_portal import StoryPortal
        from expedition33.story_preflight import PreflightReadDeferred
        owner=StoryPortal.__new__(StoryPortal)
        owner.packet=None;owner.started=False;owner.unknown=False;owner.closed=False
        resources=Mock();temporary=Mock()
        owner.scope=N(pid=123,_session=N(_story_construction_resources=N(resources=resources)))
        owner._observe_registration=Mock(side_effect=RuntimeQueryError('READ_FAILED address=0x123'))
        owner._send=Mock()
        with patch('expedition33.story_portal.SessionScope',return_value=temporary), \
                patch('expedition33.story_portal.shared_operation',return_value=nullcontext()):
            with self.assertRaises(PreflightReadDeferred):owner.prepare()
        owner._send.assert_not_called();resources.hold.assert_not_called()
        temporary.close.assert_called_once();self.assertIsNone(owner.packet)
        self.assertFalse(owner.started);self.assertFalse(owner.unknown)
    def packet(self):
        p=bytearray(SIZE);struct.pack_into('<4I2Q',p,0,3,244,0,0,7,8)
        for at in (32,48,64,80):struct.pack_into('<iiQ',p,at,1,2,0x10000)
        struct.pack_into('<4I',p,96,0xe33c5701,2,3,4)
        struct.pack_into('<4I',p,128,2,0,0,0)
        for i in range(6):struct.pack_into('<iiQ',p,144+i*16,1,2,0x10000)
        for at,value in ((240,b'Lumiere'),(336,b'Level_Lumiere_Main_V2'),(432,b'Level.SpawnPoint.LumiereAct03.Opera')):p[at:at+len(value)]=value
        struct.pack_into('<6Q',p,560,1,2,3,4,5,6)
        validate(bytes(p));return bytes(p)
    def test_setup_cannot_dispatch_travel_and_rejects_wrong_save_or_padding(self):
        p=self.packet()
        for at in (96,132,609):
            q=bytearray(p);q[at]^=1
            with self.assertRaises(ValueError):validate(bytes(q))
    def test_local_transfer_receipt_carries_native_activation_time_without_zone_dispatch(self):
        p=bytearray(self.packet());p[608]=1;p=bytes(p);validate(p)
        reply=bytearray(p);struct.pack_into('<I',reply,12,2);struct.pack_into('<I',reply,116,1)
        struct.pack_into('<Q',reply,616,1234567)
        self.assertEqual(decode(p,bytes(reply))['activation_ms'],1234567)
        reply[624]=1
        with self.assertRaises(PortalHandoffError):decode(p,bytes(reply))
    def test_receipt_is_exact_owner_route_and_one_shot_sequence(self):
        p=self.packet();reply=bytearray(p);struct.pack_into('<2I',reply,8,0,2);struct.pack_into('<3I',reply,116,1,0,12)
        self.assertEqual(decode(p,bytes(reply)),dict(state=2,sequence=1,native_error=0,handoff_ms=12))
        for at in (16,32,96,240,560):
            changed=bytearray(reply);changed[at]^=1
            with self.assertRaises(PortalHandoffError):decode(p,bytes(changed))
        struct.pack_into('<I',reply,116,2)
        with self.assertRaises(PortalHandoffError):decode(p,bytes(reply))
    def test_direct_interaction_requires_local_mode_and_exact_retained_hook(self):
        p=bytearray(self.packet());p[608]=p[609]=1
        struct.pack_into('<iiQQ',p,640,5,6,0x20000,7)
        validate(bytes(p))
        for at in (608,644,656):
            q=bytearray(p)
            if at==644:struct.pack_into('<i',q,at,0)
            else:q[at]=0
            with self.assertRaises(ValueError):validate(bytes(q))
        reply=bytearray(p);struct.pack_into('<I',reply,12,2);struct.pack_into('<I',reply,116,1)
        struct.pack_into('<Q',reply,616,300)
        self.assertEqual(decode(bytes(p),bytes(reply))['activation_ms'],300)
        reply[640]^=1
        with self.assertRaises(PortalHandoffError):decode(bytes(p),bytes(reply))
    def test_failed_handoff_is_reported_without_fabricating_success(self):
        p=self.packet();reply=bytearray(p);struct.pack_into('<I',reply,12,4);struct.pack_into('<3I',reply,116,1,1806,4)
        self.assertEqual(decode(p,bytes(reply))['state'],4)
        self.assertEqual(decode(p,bytes(reply))['native_error'],1806)
