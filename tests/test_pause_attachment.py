import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33._pause_attachment import PauseAttachment, HEADER, SIZE, validate_request
from expedition33 import _trace_wire

class PauseAttachmentTests(unittest.TestCase):
    def owner(self, reply):
        transport = SimpleNamespace(command=Mock(side_effect=reply))
        session = SimpleNamespace(_check=Mock(), _transport=transport, _abort_ownership=Mock())
        owner = PauseAttachment(SimpleNamespace(_session=session))
        owner.state='armed'
        return owner,session

    def test_detach_ack_then_idempotent_close(self):
        def reply(command,sent):
            self.assertEqual(command,'pause-attachment')
            return {'pause_attachment_packet':sent.hex()}
        owner,session=self.owner(reply)
        self.assertTrue(owner.close()); self.assertTrue(owner.close())
        self.assertEqual(session._transport.command.call_count,1)
        session._abort_ownership.assert_not_called()

    def test_deferred_detach_preserves_owner_and_can_complete(self):
        def reply(command,sent):
            data=bytearray(sent); struct.pack_into('<II',data,24,407,1)
            return {'pause_attachment_packet':data.hex()}
        owner,session=self.owner(reply)
        self.assertFalse(owner.close()); self.assertEqual(owner.state,'armed')
        session._abort_ownership.assert_not_called()
        session._transport.command.side_effect=lambda command,sent:{'pause_attachment_packet':sent.hex()}
        self.assertTrue(owner.close())

    def test_ambiguous_detach_aborts_without_replay(self):
        owner,session=self.owner(lambda *_:{'pause_attachment_packet':'00'})
        with self.assertRaises(ValueError): owner.close()
        with self.assertRaisesRegex(RuntimeError,'unknown'): owner.close()
        self.assertEqual(session._transport.command.call_count,1)
        session._abort_ownership.assert_called_once_with()

    def test_arm_accepts_changed_gc_flags_but_rejects_changed_identity(self):
        fields=dict(pid=7,index=8,serial=9,address=0x10000,name='button',
            class_index=10,outer_index=11,outer_serial=12)
        original=SimpleNamespace(**fields,object_flags=0,item_flags=0)
        lease=SimpleNamespace(active=True,object=original,_token=4)
        for changed,accepted in (({'item_flags':0x40000000},True),({'serial':10},False),
                ({'class_index':13},False),({'outer_index':14},False)):
            current=dict(vars(original));current.update(changed)
            owner,_=self.owner(None);owner.state='empty';owner.scope._leases=[lease]
            owner._send=Mock(return_value=True)
            plan=SimpleNamespace(target=SimpleNamespace(**current))
            if accepted:self.assertTrue(owner.arm(lease,plan));owner._send.assert_called_once()
            else:
                with self.assertRaises(ValueError):owner.arm(lease,plan)
                owner._send.assert_not_called()

    def test_invalid_wire_never_accepted(self):
        data=HEADER.pack(1,2,8,0,0,0)+bytes(SIZE-HEADER.size)
        validate_request(data)
        for bad in (data[:-1],data+bytes(1),HEADER.pack(1,2,8,9,0,0)+data[32:],data[:-1]+b'x'):
            with self.assertRaises(ValueError):validate_request(bad)

    def test_renewal_keeps_registration_and_bounds(self):
        data=_trace_wire.encode_request('renew',2,3,duration_ms=100,limit=10)
        self.assertEqual(_trace_wire.HEADER.unpack_from(data)[:6],(1,6,2,3,100,10))
        for duration in (0,300001,True):
            with self.assertRaises(ValueError):_trace_wire.encode_request('renew',2,3,duration_ms=duration)

if __name__=='__main__':unittest.main()
