import unittest
from types import SimpleNamespace as NS
from expedition33.sdk import Session
class MetadataSessionCloseTests(unittest.TestCase):
 def session(self,owner_close,native_close):
  session=Session.__new__(Session);session._closed=False
  session._transport=NS(_check_thread=lambda:None,_closed=False,close=native_close)
  session._metadata_preparation=NS(close=owner_close)
  session._traces=set();session._menus=set();session._leases=set();session._hooks=[]
  session.console=NS(_close=lambda:None);session._dispatcher=NS(close=lambda:None)
  return session
 def test_owner_error_does_not_skip_native_close_ack_and_is_not_replayed(self):
  calls=[];error=RuntimeError('owner pending')
  def owner():calls.append('metadata');raise error
  session=self.session(owner,lambda:calls.append('native_ack'))
  with self.assertRaises(RuntimeError) as caught:session.close()
  self.assertIs(caught.exception,error);self.assertEqual(calls,['metadata','native_ack']);self.assertTrue(session._closed)
  session.close();self.assertEqual(calls,['metadata','native_ack'])
 def test_native_close_failure_keeps_unknown_journal_even_after_owner_attempt(self):
  calls=[];journal=NS(_state='pending_release')
  def native():calls.append('native_attempt');raise RuntimeError('no native ACK')
  session=self.session(lambda:calls.append('metadata'),native);session._leases=[journal]
  session._metadata_preparation.journal=[journal]
  with self.assertRaisesRegex(RuntimeError,'no native ACK'):session.close()
  self.assertEqual(calls,['metadata','native_attempt']);self.assertEqual(journal._state,'unknown')
  self.assertIs(session._metadata_preparation.journal[0],journal)
 def test_gc_pending_metadata_lease_is_completed_by_existing_global_close(self):
  journal=NS(_state='pending_release');calls=[]
  session=self.session(lambda:calls.append('metadata'),lambda:calls.append('native_ack'));session._leases=[journal]
  session.close();self.assertEqual(journal._state,'released');self.assertEqual(calls,['metadata','native_ack'])
