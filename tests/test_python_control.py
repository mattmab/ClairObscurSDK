import hashlib,json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from expedition33._console_dispatch import CommandDispatcher
from expedition33.python_control import PythonControl,enabled

class PythonControlTests(unittest.TestCase):
    def setUp(self):
        self.owner=threading.get_ident()
        self.session=SimpleNamespace(pid=42,_closed=False,poll=lambda:7)
        def check():
            if threading.get_ident()!=self.owner:raise RuntimeError('Wrong owner thread')
        self.session._check=check
        self.session.console=SimpleNamespace(dispatcher=CommandDispatcher(self.session,lambda _:self.fail('Native console must not be used')))
        with patch('expedition33.python_control.CommandServer.write_connection',return_value=None):self.control=PythonControl(self.session,Path('.'))
        self.addCleanup(self.control.close)
    def test_authenticated_dedup_and_persistent_namespace_on_owner_poll(self):
        c=self.control.server.connection();rid='a'*32
        request=dict(token=c['token'],session=c['session'],id=rid,command='python.execute',arguments={'source':'counter=globals().get("counter",0)+1; print(counter)'})
        self.assertEqual(self.control.server._receive(request)['state'],'queued')
        self.assertEqual(self.session.poll(),7)
        reply=self.control.server._receive(request)
        self.assertEqual(reply['state'],'completed');self.assertEqual(reply['result']['output'],'1\n')
        self.assertEqual(self.session.poll(),7)
        self.assertEqual(self.control.execute('print(counter)')['output'],'1\n')
    def test_python_error_is_reported_without_replay(self):
        r=self.control.execute('marker=23; raise ValueError("deliberate")')
        self.assertTrue(r['failed']);self.assertIn('deliberate',r['output'])
        self.assertEqual(self.control.execute('print(marker)')['output'],'23\n')
    def test_file_hash_mismatch_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'local.py';p.write_text('print("local file")')
            with self.assertRaises(ValueError):self.control.execute_file(str(p),'0'*64)
            r=self.control.execute_file(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(r['output'],'local file\n')
    def test_close_restores_poll_and_rejects_new_execution(self):
        self.assertTrue(self.control.close());self.assertEqual(self.session.poll(),7)
        with self.assertRaises(RuntimeError):self.control.execute('print(1)')
    def test_python_output_is_bounded(self):
        r=self.control.execute('print("x"*50000)')
        self.assertTrue(r['truncated']);self.assertLessEqual(len(r['output'].encode()),16000)
    def test_setting_requires_explicit_boolean_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'enabled.json'
            self.assertFalse(enabled(tmp))
            for value,expected in (({'enabled':True},True),({'enabled':1},False),({'enabled':False},False)):
                p.write_text(json.dumps(value));self.assertEqual(enabled(tmp),expected)
            p.write_text('{');self.assertFalse(enabled(tmp))
