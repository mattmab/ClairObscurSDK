import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _sequence_drag as wire,_sequence_owner as owner,_invocation_wire as call

class SequenceDragTests(unittest.TestCase):
    def request(self):
        getter=bytearray(call.SIZE)
        call.HEADER.pack_into(getter,0,1,4,4,0,0,0,1,0,0,0)
        call.FIELD.pack_into(getter,call.FIELDS_AT,5,0,4,1,0,0,b'ReturnValue',0,0,0)
        config=wire.CONFIG.pack(wire.MAGIC,1,1,2,0x1000,2,3,0x2000,-158,5345,0,0,0,0)
        return bytes(getter)+config+bytes(call.SIZE-64)
    def test_protocol_validates_range_identity_and_empty_status(self):
        payload=self.request();wire.validate(20,payload)
        owner.validate_request(owner.HEADER.pack(1,20,8,0,0,0)+payload)
        for at in (call.SIZE,call.SIZE+12,call.SIZE+44,call.SIZE+48,len(payload)-1):
            bad=bytearray(payload);bad[at]^=0x80
            if at in (call.SIZE+12,call.SIZE+44):
                # Explicitly reject zero serial or reversed range.
                struct.pack_into('<i',bad,at,0 if at==call.SIZE+12 else -200)
            with self.assertRaises(ValueError):wire.validate(20,bytes(bad))
        for operation in (21,22):
            wire.validate(operation,bytes(2*call.SIZE))
            with self.assertRaises(ValueError):wire.validate(operation,payload)
    def sequence(self):
        transport=N(sequence_drag_scrub_protocol=1,command=Mock())
        sequence=N(scope=N(_check=Mock(),_session=N(_transport=transport,_abort_ownership=Mock())),
                   owner=N(state='armed',owner=8),uncertain=False,state='playing')
        return sequence,transport
    def test_status_updates_paused_state_without_a_python_seek(self):
        s,t=self.sequence();drag=wire.SequenceDrag(s);drag.bound=True
        response=owner.HEADER.pack(1,21,8,0,0,1)+wire.STATUS.pack(wire.MAGIC,1,12,1,71,.5,.2,*([0]*8))+bytes(2*call.SIZE-64)
        t.command.return_value={'sequence_owner_packet':response.hex()}
        self.assertEqual(drag.poll(),(True,71,.5,.2,True))
        self.assertEqual(s.state,'paused');self.assertFalse(s.uncertain)
        self.assertEqual(drag.poll(),(False,71,.5,.2,True))
    def test_rebinding_starts_a_new_counter_generation(self):
        s,t=self.sequence();drag=wire.SequenceDrag(s);drag.counter=55
        s._seek_function=N(index=1,serial=2,address=0x1000)
        drag.pause=N(object=N(index=2,serial=3,address=0x2000))
        plan=object()
        payload=self.request()
        # Bind acknowledgement is an exact echo, with the native armed state.
        t.command.side_effect=lambda command,data:{'sequence_owner_packet':(data[:28]+struct.pack('<I',1)+data[32:]).hex()}
        from unittest.mock import patch
        with patch('expedition33._sequence_drag.call.encode_plan',return_value=payload[:call.SIZE]), \
             patch('expedition33._sequence_drag.replace',return_value=plan):
            drag.bind(plan,-158,5345)
        self.assertTrue(drag.bound);self.assertEqual(drag.counter,0)

    def test_viewport_reply_checks_bounds_and_delivers_click_once(self):
        s,t=self.sequence();t.sequence_timeline_viewport_protocol=1
        drag=wire.SequenceDrag(s);drag.start=-158;drag.end=5345
        data=wire.VIEWPORT.pack(0x56533345,1,2,1,100,300,150,1,0,0,0,0,0)
        t.command.return_value={'sequence_owner_packet':(owner.HEADER.pack(1,23,8,0,0,1)+data+bytes(2*call.SIZE-64)).hex()}
        result=drag.viewport();self.assertTrue(result['pick']);self.assertEqual(result['lane'],1)
        self.assertFalse(drag.viewport()['pick'])
        bad=wire.VIEWPORT.pack(0x56533345,1,3,1,-200,300,150,1,0,0,0,0,0)
        t.command.return_value={'sequence_owner_packet':(owner.HEADER.pack(1,23,8,0,0,1)+bad+bytes(2*call.SIZE-64)).hex()}
        with self.assertRaises(RuntimeError):drag.viewport()
        self.assertEqual(s.owner.state,'unknown')

    def test_expanded_viewport_decodes_hover_without_claiming_a_seek(self):
        s,t=self.sequence();t.sequence_timeline_viewport_protocol=2
        drag=wire.SequenceDrag(s);drag.start=0;drag.end=100
        bits=struct.unpack('<I',struct.pack('<f',.5))[0]
        data=wire.VIEWPORT.pack(0x56533345,2,1,1,20,80,40,5,bits,2,1,8,0)
        t.command.return_value={'sequence_owner_packet':(owner.HEADER.pack(1,23,8,0,0,1)+data+bytes(2*call.SIZE-64)).hex()}
        result=drag.viewport();self.assertTrue(result['pick']);self.assertEqual(result['lane'],5)
        self.assertEqual((result['hover'],result['hover_frame'],result['hover_lane']),(True,50.,2))
        self.assertEqual(s.state,'playing')  # Selection never claims native Pause/seek.

    def test_malformed_ack_quarantines_without_replay(self):
        s,t=self.sequence();drag=wire.SequenceDrag(s)
        t.command.return_value={'sequence_owner_packet':'00'}
        with self.assertRaises(RuntimeError):drag.poll()
        self.assertEqual(t.command.call_count,1);self.assertEqual(s.owner.state,'unknown')
        s.scope._session._abort_ownership.assert_called_once()
    def test_release_requires_matching_ack_before_clearing_binding(self):
        s,t=self.sequence();drag=wire.SequenceDrag(s);drag.bound=True
        response=owner.HEADER.pack(1,22,8,0,0,1)+bytes(2*call.SIZE)
        t.command.return_value={'sequence_owner_packet':response.hex()}
        drag.close();self.assertFalse(drag.bound)
        drag.close();self.assertEqual(t.command.call_count,1)
