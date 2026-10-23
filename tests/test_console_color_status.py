import threading,io,unittest
import expedition33
from expedition33._session import SessionTransport
class Tests(unittest.TestCase):
 def transport(self,cap=1,status=None):
  t=SessionTransport.__new__(SessionTransport);t._owner=threading.get_ident();t._closed=False;t.console_color_status_protocol=cap
  class P:stdin=io.StringIO()
  t._process=P();t._abort=lambda:None
  t._read=lambda:dict(event='session_response',command='console-color-status',closed=False,console_color_status=status or dict(version=1,native_version=205,bound=1,disabled=0,unsupported=0,frames=3,fallbacks=1,faults=0))
  return t
 def test_exact_read_only_command_and_actual_native_version(self):
  t=self.transport();r=t._command('console-color-status');self.assertEqual(t._process.stdin.getvalue(),'console-color-status\n');self.assertEqual(r['console_color_status']['native_version'],205)
 def test_capability_and_payload_rejected_before_dispatch(self):
  for cap in [0,True]:
   t=self.transport(cap)
   with self.assertRaises(ValueError):t._command('console-color-status')
   self.assertEqual(t._process.stdin.getvalue(),'')
  t=self.transport()
  with self.assertRaises(ValueError):t._command('console-color-status',b'bad')
  self.assertEqual(t._process.stdin.getvalue(),'')
 def test_console_poll_preserves_control_string_and_validates_status(self):
  t=self.transport();read=t._read
  def response():
   r=read();r.update(command='console-poll',console_text='sdk.test exact control',events=[]);return r
  t._read=response;r=t._command('console-poll')
  self.assertEqual(r['console_text'],'sdk.test exact control');self.assertEqual(r['console_color_status']['native_version'],205)
  self.assertEqual(t._process.stdin.getvalue(),'console-poll\n')
 def test_drain_does_not_require_status_or_change_observer_records(self):
  t=self.transport();events=[dict(object_address='0x123',thread=1,result=2)]
  t._read=lambda:dict(event='session_response',command='drain',closed=False,events=events)
  self.assertEqual(t._command('drain')['events'],events)
 def test_malformed_bool_counter_rejected(self):
  t=self.transport(status=dict(version=1,native_version=205,bound=1,disabled=0,unsupported=0,frames=True,fallbacks=0,faults=0))
  with self.assertRaises(expedition33.RuntimeQueryError):t._command('console-color-status')
if __name__=='__main__':unittest.main()
