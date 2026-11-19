import struct
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.map_load_gate import MapLoadGate,validate_request,SIZE


class GateWireTests(unittest.TestCase):
    def test_only_preflight_release_rejection_is_not_ready(self):
        from expedition33.map_load_gate import MapLoadGateNotReady
        def reject(packet):struct.pack_into('<I',packet,8,2143)
        gate=self.owner(reject)
        with self.assertRaises(MapLoadGateNotReady) as caught:
            gate.release({'visit':[1,2,16],'pawn':[3,4,32]})
        self.assertEqual(caught.exception.outcome,'not_dispatched')
        self.assertEqual(len(self.sent),1)
        with self.assertRaises(RuntimeError) as caught:gate.close()
        self.assertNotIsInstance(caught.exception,MapLoadGateNotReady)
        self.assertFalse(gate.closed)
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

    def test_native_hold_timing_requires_an_explicit_capability(self):
        def copy(packet):struct.pack_into('<3Q',packet,4160,1000,875,1)
        gate=self.owner(copy)
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):gate.status()
        gate=self.owner(copy);gate.session._transport.map_load_timing_protocol=1
        result=gate.status()
        self.assertEqual((result['hold_started_ms'],result['hold_duration_ms'],result['hold_sequence']),(1000,875,1))

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

    def test_priority_configuration_requires_capability_and_two_stable_identities(self):
        ids=((1,1001,0x10000),(2,1002,0x20000))
        for capability in (None,0,True,2):
            gate=self.owner();gate.session._transport.map_loading_priority_protocol=capability
            with self.assertRaisesRegex(RuntimeError,'unavailable'):gate._send(267,ids=ids)
            self.assertFalse(self.sent)
        gate=self.owner();gate.session._transport.map_loading_priority_protocol=1
        gate._send(267,ids=ids)
        self.assertEqual(struct.unpack_from('<iiQ',self.sent[0],104),ids[1])
        for offset,fmt,value in ((92,'<i',0),(96,'<Q',0x10001),(112,'<Q',0x800000000000),(120,'<B',1),(4096,'<B',1)):
            bad=bytearray(self.sent[0]);struct.pack_into(fmt,bad,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):validate_request(bytes(bad))

    def test_priority_status_requires_capability_and_valid_diagnostic_values(self):
        def copy(packet):struct.pack_into('<5I',packet,4184,4,0,1,1,0)
        gate=self.owner(copy)
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):gate.status()
        gate=self.owner(copy);gate.session._transport.map_loading_priority_protocol=1
        self.assertEqual(gate.status()['priority'],dict(state='closed',error=0,enable_returned=True,restore_returned=True,retired=False))
        for values in ((6,0,0,0,0),(2,0,2,0,0),(4,0,1,2,0),(4,0,1,1,2)):
            gate=self.owner(lambda packet:struct.pack_into('<5I',packet,4184,*values))
            gate.session._transport.map_loading_priority_protocol=1
            with self.subTest(values=values),self.assertRaisesRegex(RuntimeError,'diagnostics'):gate.status()

    def test_priority_status_cannot_modify_adjacent_payload_or_configuration(self):
        for offset in (88,4183,4204,SIZE-1):
            gate=self.owner(lambda packet:packet.__setitem__(offset,1));gate.session._transport.map_loading_priority_protocol=1
            with self.subTest(offset=offset),self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):gate.status()

    def test_unknown_priority_install_is_not_replayed_or_marked_closed(self):
        gate=self.owner(lambda packet:packet.__setitem__(1999,1));gate.session._transport.map_loading_priority_protocol=1
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):
            gate._send(267,ids=((1,1001,0x10000),(2,1002,0x20000)))
        self.assertEqual(len(self.sent),1);self.assertFalse(gate.closed)

    def test_transport_admits_priority_only_with_exact_capability_and_wire(self):
        import io
        from expedition33._session import SessionTransport
        def transport(capability):
            value=SessionTransport.__new__(SessionTransport)
            value._check_thread=lambda:None;value._closed=False;value.mesh_protocol=3
            value.map_load_gate_protocol=1;value.map_loading_priority_protocol=capability
            value._process=N(stdin=io.StringIO());value._read=lambda:dict(event='session_response',command='mesh',closed=False)
            return value
        gate=self.owner();gate.session._transport.map_loading_priority_protocol=1
        gate._send(267,ids=((1,1001,0x10000),(2,1002,0x20000)));packet=self.sent[0]
        for capability in (0,None,False,True,2):
            connection=transport(capability)
            with self.subTest(capability=capability),self.assertRaisesRegex(ValueError,'loading priority'):
                connection.command('mesh',packet)
            self.assertEqual(connection._process.stdin.getvalue(),'')
        connection=transport(1);connection.command('mesh',packet)
        self.assertTrue(connection._process.stdin.getvalue().startswith('mesh '))
        bad=bytearray(packet);bad[120]=1;connection=transport(1)
        with self.assertRaises(ValueError):connection.command('mesh',bytes(bad))
        self.assertEqual(connection._process.stdin.getvalue(),'')
