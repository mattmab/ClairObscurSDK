import struct
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import patch,Mock
from expedition33.native_dialogue import NativeDialogueText,NativeDialogueError,decode
import test_native_dialogue_wire as fixtures

class NativeDialogueTests(unittest.TestCase):
    def function_owner(self):
        function=N(index=7,serial=8,address=0x70000,class_name='Function')
        held=N(object=function,active=True)
        session=N();prepared=N(session=session,scope=N(_check=Mock()),metadata=(function,),resources=N(hold=Mock(return_value=held)))
        session._story_construction_resources=prepared
        owner=NativeDialogueText.__new__(NativeDialogueText);owner.scope=N(_session=session)
        return owner,function,held,prepared

    def test_exact_warmed_functions_share_process_lease_without_new_acquisition(self):
        owner,function,held,prepared=self.function_owner()
        with patch('expedition33._stable_lease.acquire_stable') as acquire:
            self.assertIs(owner._hold_function(function),held)
        acquire.assert_not_called();prepared.resources.hold.assert_called_once_with(function)
        self.assertIs(owner._function_resources,prepared)
        owner._check_functions();self.assertEqual(prepared.scope._check.call_count,2)

    def test_actor_and_changed_function_generations_keep_per_dialogue_ownership(self):
        for changed in (dict(serial=9),dict(class_name='BP_Dialogue_C')):
            owner,function,held,prepared=self.function_owner();other=N(**dict(vars(function),**changed))
            private=object()
            with patch('expedition33._stable_lease.acquire_stable',return_value=(private,None)) as acquire:
                self.assertIs(owner._hold_function(other),private)
            acquire.assert_called_once_with(owner.scope,other);prepared.resources.hold.assert_not_called()

    def test_shared_function_resources_must_remain_live_and_in_same_session(self):
        owner,function,held,prepared=self.function_owner()
        owner._hold_function(function)
        prepared.scope._check.side_effect=RuntimeError('process scope retired')
        with self.assertRaisesRegex(RuntimeError,'retired'):owner._check_functions()
        prepared.scope._check.side_effect=None;prepared.session=object()
        with self.assertRaisesRegex(RuntimeError,'session changed'):owner._check_functions()
        owner,function,held,prepared=self.function_owner();held.active=False
        with self.assertRaisesRegex(RuntimeError,'lease expired'):owner._hold_function(function)
    def camera_owner(self,error=0):
        from expedition33 import _story_camera_wire as camera
        owner=object.__new__(NativeDialogueText);owner.unknown=False
        actors=[N(index=i,serial=i+20,address=0x10000+i*0x1000) for i in range(6)]
        owner.camera_packet=camera.encode(1,2,3,4,*actors)
        def command(name,packet):
            self.assertEqual(name,'mesh');self.assertEqual(struct.unpack_from('<I',packet,208)[0],1)
            result=bytearray(packet);struct.pack_into('<II',result,8,error,0 if error else 1)
            return {'mesh_packet':bytes(result).hex()}
        owner.scope=N(_session=N(_transport=N(story_dialogue_camera_protocol=4,command=command)),_lease_context=nullcontext)
        return owner

    def test_camera_retirement_pending_keeps_packet_and_does_not_quarantine(self):
        owner=self.camera_owner(3910);packet=owner.camera_packet
        self.assertFalse(owner.retire_camera_world())
        self.assertEqual(owner.camera_packet,packet);self.assertFalse(owner.unknown)
        owner.scope._session._transport.story_dialogue_camera_protocol=3
        self.assertFalse(owner.retire_camera_world());self.assertEqual(owner.camera_packet,packet)

    def test_camera_retirement_acknowledgement_releases_only_its_journal(self):
        owner=self.camera_owner()
        self.assertTrue(owner.retire_camera_world());self.assertIsNone(owner.camera_packet)
        self.assertTrue(owner.retire_camera_world());self.assertFalse(owner.unknown)
        owner=self.camera_owner(3911)
        with self.assertRaisesRegex(RuntimeError,'retirement failed'):owner.retire_camera_world()
        self.assertTrue(owner.unknown);self.assertIsNotNone(owner.camera_packet)

    def test_active_camera_prevents_scope_close_until_end_or_retirement(self):
        owner=self.camera_owner();owner.closed=False;owner.scope.close=Mock()
        self.assertFalse(owner.close());owner.scope.close.assert_not_called()
        self.assertIsNotNone(owner.camera_packet)

    def test_missing_or_boolean_capability_refuses_before_acquiring_any_owner(self):
        for capability in (0,True,2):
            parent=N(_check=lambda:None,_session=N(_transport=N(native_dialogue_text_protocol=capability)))
            with patch('expedition33._scope.SessionScope') as scope:
                with self.assertRaises(RuntimeError):NativeDialogueText(parent,None,None)
                scope.assert_not_called()
    def test_acknowledgement_cannot_change_identity_or_text(self):
        sent=fixtures.NativeDialogueWireTests().packet();reply=bytearray(sent);struct.pack_into('<I',reply,12,1)
        decode(sent,bytes(reply))
        for at in (16,24,112,240,len(reply)-1):
            changed=bytearray(reply);changed[at]^=1
            with self.assertRaises(RuntimeError):decode(sent,bytes(changed))
    def test_unknown_native_outcome_keeps_ownership_until_recovery(self):
        sent=fixtures.NativeDialogueWireTests().packet();reply=bytearray(sent);struct.pack_into('<I',reply,8,3862)
        with self.assertRaises(NativeDialogueError) as result:decode(sent,bytes(reply))
        self.assertEqual(result.exception.code,3862)
        owner=object.__new__(NativeDialogueText);owner.closed=False;owner.unknown=True
        with patch('expedition33._scope.SessionScope') as scope:
            self.assertFalse(owner.close());scope.assert_not_called()

    def test_native_end_precedes_participant_removal_and_failed_cleanup_keeps_leases(self):
        owner=object.__new__(NativeDialogueText);owner.participants_active=True
        order=[];owner._send=lambda *a,**k:order.append('end') or 123
        owner._send_participants=lambda **k:order.append('remove')
        self.assertEqual(owner.end(),123)
        self.assertEqual(order,['end','remove']);self.assertFalse(owner.participants_active)
        owner.closed=False;owner.unknown=False;owner.participants_active=True;owner.scope=Mock()
        owner._send_participants=Mock(side_effect=RuntimeError('cleanup pending'))
        self.assertFalse(owner.close());owner.scope.close.assert_not_called()
        self.assertTrue(owner.participants_active)
        owner._send_participants=Mock()
        self.assertTrue(owner.close());owner.scope.close.assert_called_once()
