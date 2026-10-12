import threading
import unittest
import uuid
from unittest.mock import Mock
from expedition33.controller_commands import Command, CommandClient, CommandServer

class ControllerCommandsTests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        self.server=CommandServer({
            'test.record':Command('inspect',lambda value: self.calls.append((value,threading.get_ident())) or value),
            'test.denied':Command('mutate',lambda: self.calls.append('bad'))},capabilities={'inspect'})
        self.client=CommandClient(self.server.connection())
    def tearDown(self): self.server.close()
    def test_queue_wait_and_handler_time_are_separate(self):
        telemetry=Mock()
        self.server._telemetry=telemetry
        self.client.request('test.record',{'value':3})
        self.server.poll()
        calls=telemetry.record.call_args_list
        self.assertEqual([call.args[1] for call in calls],['controller_queue_wait','controller'])
        self.assertLessEqual(calls[0].args[2],calls[1].args[2])
        self.assertTrue(all(call.args[3]>=0 for call in calls))
    def test_network_never_executes_and_retries_are_idempotent(self):
        rid=uuid.uuid4().hex
        self.assertEqual(self.client.request('test.record',{'value':3},request_id=rid)['state'],'queued')
        self.assertEqual(self.calls,[])
        self.server.poll()
        reply=self.client.request('test.record',{'value':3},request_id=rid)
        self.assertEqual(reply['result'],3)
        self.assertEqual(self.calls,[(3,threading.get_ident())])
        self.assertEqual(self.client.request('test.record',{'value':4},request_id=rid)['error'],'id_conflict')
        self.assertFalse(self.server.poll())
    def test_auth_session_and_capability_rejections(self):
        bad=self.server.connection(); bad['token']='wrong'
        self.assertEqual(CommandClient(bad).request('test.record')['error'],'unauthorized')
        bad=self.server.connection(); bad['session']='old'
        self.assertEqual(CommandClient(bad).request('test.record')['error'],'wrong_session')
        self.assertEqual(self.client.request('test.denied')['error'],'capability_denied')
        self.assertEqual(self.client.request('py',{'code':'print(1)'})['error'],'unknown_command')
        self.assertEqual(self.client.request('exec',{'code':'print(1)'})['error'],'unknown_command')
        self.assertEqual(self.calls,[])
    def test_invalid_arguments_fail_without_poisoning_service(self):
        reply=self.client.request('test.record',{'unexpected':1}); self.server.poll()
        self.assertEqual(self.client.request('request.status',request_id=reply['id'])['state'],'failed')
        self.assertEqual(self.calls,[])
        self.client.request('test.record',{'value':'ok'}); self.server.poll()
        self.assertEqual(self.calls[0][0],'ok')
    def test_owner_thread_and_queue_limit(self):
        errors=[]
        def wrong_thread():
            try: self.server.poll()
            except RuntimeError: errors.append(True)
        thread=threading.Thread(target=wrong_thread); thread.start(); thread.join()
        self.assertEqual(errors,[True])
        for i in range(16): self.assertEqual(self.client.request('test.record',{'value':i})['state'],'queued')
        self.assertEqual(self.client.request('test.record',{'value':17})['error'],'capacity')
        self.server.close()
        self.assertFalse(self.server.poll())
        self.assertEqual(self.calls,[])
    def test_unicode_token_cannot_stop_listener(self):
        bad=self.server.connection(); bad['token']='\u2603'*64
        self.assertEqual(CommandClient(bad).request('sdk.capabilities')['error'],'unauthorized')
        self.assertEqual(self.client.request('sdk.capabilities')['state'],'queued')

    def test_cancel_and_expire_never_execute(self):
        import time
        reply=self.client.request('test.record',{'value':1})
        self.assertEqual(self.client.request('request.cancel',request_id=reply['id'])['state'],'cancelled')
        self.assertFalse(self.server.poll())
        self.server._queue_timeout=.001
        reply=self.client.request('test.record',{'value':2})
        time.sleep(.01)
        self.server.poll()
        self.assertEqual(self.client.request('request.status',request_id=reply['id'])['state'],'expired')
        self.assertEqual(self.calls,[])

    def test_nonfinite_json_cannot_stop_listener(self):
        import socket
        import json
        request=dict(token=self.server.connection()['token'],session=self.server.session,
                     id=uuid.uuid4().hex,command='test.record',arguments={'value':float('nan')})
        with socket.create_connection(('127.0.0.1',self.server.connection()['port'])) as sock:
            sock.sendall(json.dumps(request).encode()+b'\n')
            self.assertEqual(sock.recv(256),b'')
        self.assertEqual(self.client.request('sdk.capabilities')['state'],'queued')
    def test_running_work_cannot_be_cancelled_or_reexecuted(self):
        rid=uuid.uuid4().hex
        replies=[]
        self.server._commands['test.running']=Command('inspect',lambda: replies.append(
            self.client.request('request.cancel',request_id=rid)))
        self.client.request('test.running',request_id=rid)
        self.server.poll()
        self.assertEqual(replies[0]['error'],'not_preemptible')
        self.assertEqual(self.client.request('test.running',request_id=rid)['state'],'completed')
        self.assertEqual(len(replies),1)

    def test_connection_file_removed_on_normal_close(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path=self.server.write_connection(Path(directory))
            self.assertTrue(path.exists())
            self.server.close()
            self.assertFalse(path.exists())
