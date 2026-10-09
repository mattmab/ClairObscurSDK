from dataclasses import replace
import threading
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.sdk import Session
from expedition33._scope import SessionScope
from expedition33.ownership import LeaseError
from expedition33 import _lease_wire as wire


class Transport:
    def __init__(self):
        self._closed=False
        self.owner=threading.get_ident()
        self.lease_protocol=1
        self.reflected_protocol=1
        self.start={'pid':100}
        self.objects=[{'index':1,'serial':2,'address':'0x1234','name':'Default__Actor',
                       'class_name':'Actor','metaclass_name':'Class','class_index':9}]
        self.tokens=set(); self.next=1; self.calls=[]
        self.defer=False; self.malformed=False; self.abort_count=0
        self.close_failed=False

    def _check_thread(self):
        if threading.get_ident()!=self.owner: raise RuntimeError('Wrong owner thread')

    def command(self, command, packet=None):
        self._check_thread()
        if self._closed: raise RuntimeQueryError('Transport closed')
        self.calls.append(command)
        if command=='drain': return {'events':[],'dropped':0}
        values=list(wire.PACKET.unpack(packet))
        values[2]=1
        if command=='lease-acquire':
            self.tokens.add(self.next); values[7]=self.next; self.next+=1
        elif command=='lease-release':
            if self.defer: values[1]=407
            elif values[7] not in self.tokens: values[1]=402
            else: self.tokens.remove(values[7])
        values[3]=len(self.tokens)
        return {'lease_packet':'bad' if self.malformed else wire.PACKET.pack(*values).hex()}

    def _abort(self):
        self.abort_count+=1; self._closed=True; self.tokens.clear()

    def close(self):
        if self.close_failed:
            self._abort()
            raise RuntimeQueryError('Close unacknowledged')
        self.tokens.clear(); self._closed=True


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.transport=Transport()
        self.patch=patch('expedition33.sdk.SessionTransport',return_value=self.transport)
        self.factory=self.patch.start(); self.addCleanup(self.patch.stop)
        self.session=Session(leases=True)
        self.obj=self.session._object

    def tearDown(self):
        self.transport.close_failed=False
        self.session.close()

    def test_backend_selection_and_independent_context_ownership(self):
        self.assertIn('research-probe-v7',str(self.factory.call_args.kwargs['_executable']))
        with self.session.retain(self.obj) as first:
            second=self.session.retain(self.obj)
            self.assertEqual(first.object,self.obj)
            self.assertEqual(len(self.transport.tokens),2)
        self.assertFalse(first.active)
        self.assertTrue(first.release())
        self.assertTrue(second.active)
        self.assertEqual(len(self.transport.tokens),1)
        with self.assertRaises(LeaseError): _=first.object

    def test_scope_cleanup_preserves_other_mod_and_session(self):
        a=SessionScope(self.session); b=SessionScope(self.session)
        first=a.retain(self.obj); second=b.retain(self.obj)
        a.close()
        self.assertFalse(first.active)
        self.assertTrue(second.active)
        self.assertFalse(self.transport._closed)
        self.assertEqual(len(self.transport.tokens),1)
        with self.assertRaises(RuntimeError): a.retain(self.obj)
        b.close()
        self.assertFalse(self.transport.tokens)

    def test_deferred_mod_cleanup_is_revoked_and_polled(self):
        scope=SessionScope(self.session); lease=scope.retain(self.obj)
        self.transport.defer=True
        scope.close()
        self.assertFalse(lease.active); self.assertTrue(lease.release_pending)
        self.assertEqual(len(self.transport.tokens),1)
        with self.assertRaises(LeaseError): _=lease.object
        self.transport.defer=False
        self.session.poll()
        self.assertFalse(lease.release_pending)
        self.assertTrue(lease.release())
        self.assertFalse(self.transport.tokens)

    def test_malformed_acquire_aborts_without_retry_and_revokes_existing(self):
        first=self.session.retain(self.obj)
        self.transport.malformed=True
        with self.assertRaises(LeaseError) as caught: self.session.retain(self.obj)
        self.assertEqual(caught.exception.outcome,'unknown')
        self.assertEqual(self.transport.abort_count,1)
        self.assertEqual(self.transport.calls.count('lease-acquire'),2)
        self.assertFalse(first.active)
        with self.assertRaises(LeaseError): first.release()

    def test_malformed_release_is_not_retried(self):
        lease=self.session.retain(self.obj); self.transport.malformed=True
        with self.assertRaises(LeaseError): lease.release()
        self.session.close()
        with self.assertRaises(LeaseError): lease.release()
        self.assertEqual(self.transport.calls.count('lease-release'),1)

    def test_invalid_owner_and_unsupported_backend_reject_before_io(self):
        with self.assertRaises(ValueError): self.session.retain(replace(self.obj,pid=101))
        with self.assertRaises(ValueError): self.session.retain(object())
        self.transport.lease_protocol=0
        with self.assertRaises(LeaseError) as caught: self.session.retain(self.obj)
        self.assertEqual(caught.exception.outcome,'not_dispatched')
        self.assertFalse(self.transport.calls)

    def test_close_invalidates_all_and_wrong_thread_cannot_release(self):
        lease=self.session.retain(self.obj)
        errors=[]
        def worker():
            try: lease.release()
            except RuntimeError as error: errors.append(str(error))
        thread=threading.Thread(target=worker); thread.start(); thread.join()
        self.assertEqual(len(errors),1); self.assertTrue(lease.active)
        self.session.close()
        self.assertFalse(lease.active); self.assertTrue(lease.release())

    def test_failed_or_already_aborted_close_does_not_claim_release(self):
        lease=self.session.retain(self.obj)
        self.transport._abort()
        self.session.close()
        with self.assertRaises(LeaseError) as caught: lease.release()
        self.assertEqual(caught.exception.outcome,'unknown')

    def test_close_failure_revokes_access_without_claiming_acknowledgement(self):
        lease=self.session.retain(self.obj)
        self.transport.close_failed=True
        with self.assertRaises(RuntimeQueryError): self.session.close()
        self.assertFalse(lease.active)
        with self.assertRaises(LeaseError) as caught: lease.release()
        self.assertEqual(caught.exception.outcome,'unknown')


if __name__=='__main__': unittest.main()
