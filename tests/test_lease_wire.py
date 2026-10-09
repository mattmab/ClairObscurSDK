from types import SimpleNamespace
import threading
import unittest
from expedition33 import _lease_wire as wire
from expedition33._session import SessionTransport


class LeaseWireTests(unittest.TestCase):
    def test_acquire_identity_and_token_agreement(self):
        obj=SimpleNamespace(index=42,serial=7,address=0x123400)
        sent=wire.request('lease-acquire',object=obj)
        self.assertEqual(len(sent),40)
        values=list(wire.PACKET.unpack(sent))
        values[2:4]=[1,1]; values[7]=9
        result=wire.decode('lease-acquire',sent,wire.PACKET.pack(*values).hex())
        self.assertEqual((result.error,result.outcome,result.active,result.token),(0,'completed',1,9))
        values[5]+=1
        with self.assertRaises(ValueError): wire.decode('lease-acquire',sent,wire.PACKET.pack(*values).hex())

    def test_release_rejects_changed_token_and_status_bounds(self):
        sent=wire.request('lease-release',token=8)
        values=list(wire.PACKET.unpack(sent)); values[2]=1
        self.assertEqual(wire.decode('lease-release',sent,wire.PACKET.pack(*values).hex()).token,8)
        values[7]=9
        with self.assertRaises(ValueError): wire.decode('lease-release',sent,wire.PACKET.pack(*values).hex())
        values[7]=8; values[3]=129
        with self.assertRaises(ValueError): wire.decode('lease-release',sent,wire.PACKET.pack(*values).hex())

    def test_rejections_and_unknown_are_not_success(self):
        sent=wire.request('lease-status')
        values=list(wire.PACKET.unpack(sent)); values[1]=411
        self.assertEqual(wire.decode('lease-status',sent,wire.PACKET.pack(*values).hex()).outcome,'not_dispatched')
        values[1]=0; values[2]=2
        self.assertEqual(wire.decode('lease-status',sent,wire.PACKET.pack(*values).hex()).outcome,'unknown')
        with self.assertRaises(ValueError): wire.request('lease-release',token=0)
        with self.assertRaises(ValueError): wire.request('lease-status',token=1)
        with self.assertRaises(ValueError): wire.decode('lease-status',sent,'00')

    def test_old_transport_rejects_before_io(self):
        session=SessionTransport.__new__(SessionTransport)
        session._closed=False; session._owner=threading.get_ident(); session.lease_protocol=0
        with self.assertRaisesRegex(ValueError,'does not support object leases'):
            session.command('lease-status',wire.request('lease-status'))


if __name__=='__main__': unittest.main()
