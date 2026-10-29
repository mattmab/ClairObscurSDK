import json,queue,unittest
from unittest.mock import Mock,patch
from expedition33._session import SessionTransport
from expedition33 import RuntimeQueryError,TargetExitedError

class CommandWaitTests(unittest.TestCase):
    def transport(self,values,**kw):
        t=SessionTransport.__new__(SessionTransport);t._lines=queue.Queue()
        t.command_wait_protocol=1;t._awaiting_command_sequence=42;t._native_command_sequence=41
        for k,v in kw.items():setattr(t,k,v)
        for value in values:t._lines.put(json.dumps(value))
        return t
    def pending(self,elapsed=5000,**kw):
        return dict(event='session_pending',version=1,sequence=42,elapsed_ms=elapsed,state=1,**kw)
    def test_waits_for_same_command_past_old_deadline_without_replay(self):
        reply=dict(event='session_response',command='console-poll',command_sequence=42,closed=False)
        t=self.transport([self.pending(),self.pending(12000),self.pending(59000),reply])
        t._owner=__import__('threading').get_ident();t._closed=False;t._process=Mock()
        t._command('console-poll')
        t._process.stdin.write.assert_called_once_with('console-poll\n')
        self.assertIsNone(t._awaiting_command_sequence)
    def test_wrong_sequence_and_stale_or_unbounded_notices_are_rejected(self):
        for key,value in (('sequence',41),('sequence',True),('state',3),('version',True),('elapsed_ms',60000),('elapsed_ms',4999)):
            notice=self.pending();notice[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(RuntimeQueryError):self.transport([notice])._read()
        with self.assertRaises(RuntimeQueryError):self.transport([self.pending(),self.pending()])._read()
        with self.assertRaises(RuntimeQueryError):self.transport([self.pending()],command_wait_protocol=0)._read()
        with self.assertRaises(RuntimeQueryError):self.transport([self.pending()],_awaiting_command_sequence=None)._read()
    def test_pending_never_masks_target_exit_or_terminal_timeout(self):
        for end,kind in ((dict(event='target_exited',exit_code=0),TargetExitedError),
                         (dict(event='error',message='SESSION_COMMAND_TIMEOUT'),RuntimeQueryError)):
            with self.assertRaises(kind):self.transport([self.pending(),end])._read()
    def test_heartbeats_cannot_extend_absolute_deadline(self):
        with patch('expedition33._session.time.monotonic',side_effect=(0.,0.,71.)):
            with self.assertRaisesRegex(RuntimeQueryError,'deadline'):self.transport([self.pending()])._read()
