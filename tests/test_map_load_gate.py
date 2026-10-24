import struct
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.map_load_gate import MapLoadGate,validate_request,SIZE


class GateWireTests(unittest.TestCase):
    def owner(self,change=None):
        gate=MapLoadGate.__new__(MapLoadGate);gate.owner=123;gate.closed=False;gate.overlay=None
        self.sent=[]
        def command(name,packet):
            self.assertEqual(name,'mesh');validate_request(packet);self.sent.append(packet)
            response=bytearray(packet);struct.pack_into('<I',response,12,1)
            if change:change(response)
            return {'mesh_packet':response.hex()}
        gate.session=N(_transport=N(command=command));return gate

    def test_arm_explicit_world_inventory_and_reject_overflow(self):
        gate=self.owner();ids=((1,1001,16),(2,1002,32),(3,1003,48))
        gate._send(99,ids=ids,worlds=('/Game/Test.Test',))
        self.assertEqual(struct.unpack_from('<I',self.sent[0],2000)[0],1)
        for paths in ((),('/Game/Test.Test',)*0,tuple(f'/Game/Test{i}.Test{i}' for i in range(33)),('/Game/../Invalid.Invalid',)):
            with self.assertRaises((ValueError,struct.error)):gate._send(99,ids=ids,worlds=paths)

    def test_status_only_accepts_bounded_copied_identities_and_state(self):
        def copy(packet):
            struct.pack_into('<I',packet,12,2);struct.pack_into('<iiQ',packet,4096,1,1001,16)
            struct.pack_into('<iiQ',packet,4112,2,1002,32)
        result=self.owner(copy).status()
        self.assertEqual(result,{'state':2,'world':[1,1001,16],'pawn':[2,1002,32]})

    def test_reply_cannot_change_owner_or_unrelated_packet_bytes(self):
        for offset in (16,88,2000,4146,SIZE-1):
            with self.subTest(offset=offset):
                gate=self.owner(lambda packet:packet.__setitem__(offset,packet[offset]^1))
                with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):gate.status()

    def test_release_includes_exact_world_and_pawn_and_close_is_once(self):
        gate=self.owner();gate.release({'visit':[1,1001,16],'pawn':[2,1002,32]})
        self.assertEqual(struct.unpack_from('<iiQ',self.sent[0],104),(2,1002,32))
        gate.close();gate.close();self.assertEqual(len(self.sent),2)

    def test_assignment_updates_keep_same_native_owner_and_skip_unchanged_inventory(self):
        gate=self.owner();gate.ids=((1,1001,16),(2,1002,32),(3,1003,48));gate.worlds=('/Game/A.A',)
        gate.update_worlds(('/Game/A.A',));self.assertFalse(self.sent)
        gate.update_worlds(('/Game/A.A','/Game/B.B'))
        self.assertEqual(struct.unpack_from('<Q',self.sent[0],16)[0],123)
        self.assertEqual(struct.unpack_from('<I',self.sent[0],2000)[0],2)

    def test_cover_lifetime_is_retained_through_uncertain_native_attachment(self):
        ids=tuple((i,1000+i,16*i) for i in range(1,6))
        overlay=Mock();overlay.native_bindings.return_value=ids
        gate=self.owner();gate.session._transport.map_loading_presentation_protocol=1
        gate.attach_cover(overlay)
        self.assertEqual(struct.unpack_from('<I',self.sent[0],4)[0],103)
        self.assertEqual(struct.unpack_from('<iiQ',self.sent[0],152),ids[4])
        overlay.adopt_native.assert_called_once()
        overlay.reset_mock();gate=self.owner(lambda packet:packet.__setitem__(1999,1))
        gate.session._transport.map_loading_presentation_protocol=1
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):gate.attach_cover(overlay)
        overlay.adopt_native.assert_called_once()
        self.assertIs(gate.overlay,overlay)

    def test_cover_requires_capability_and_valid_binding_padding(self):
        gate=self.owner();gate.session._transport.map_loading_presentation_protocol=0
        overlay=Mock()
        with self.assertRaisesRegex(RuntimeError,'unavailable'):gate.attach_cover(overlay)
        self.assertFalse(self.sent);overlay.adopt_native.assert_not_called()
        ids=tuple((i,1000+i,16*i) for i in range(1,6))
        gate._send(103,ids=ids);packet=bytearray(self.sent[0]);packet[168]=1
        with self.assertRaises(ValueError):validate_request(bytes(packet))

    def test_padding_and_invalid_header_are_rejected_before_dispatch(self):
        gate=self.owner();gate.status();packet=self.sent[0]
        for offset in (0,8,24,88,1999,2000,4096):
            with self.subTest(offset=offset):
                bad=bytearray(packet);bad[offset]^=255
                with self.assertRaises(ValueError):validate_request(bytes(bad))
