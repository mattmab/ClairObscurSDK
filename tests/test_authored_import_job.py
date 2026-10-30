import threading
import time
import unittest
from types import SimpleNamespace as N
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33._reader import ReadBatch,ReadCancelled,_active
from expedition33.cinematics.authored_import_job import AuthoredImportJob,_partial_read_failure


def partial_read(message='READ_FAILED address=0x1234 win32=299'):
    import json
    return RuntimeQueryError('Read worker rejected query: '+json.dumps({'event':'snapshot_start'})+'\n'
        +json.dumps({'event':'error','message':message})+'\n')


class ImportJobTests(unittest.TestCase):
    identity=(7,11,0x10000)

    def launch(self,steps,*,exit_gate=None):
        created=[];entered=[];closed=[]
        class Reader:
            def __init__(self,pid,**kwargs):
                created.append((threading.get_ident(),pid,kwargs))
            def __enter__(self):entered.append(threading.get_ident());return self
            def __exit__(self,*error):
                if exit_gate is not None:exit_gate.wait(2)
                closed.append(threading.get_ident())
        obj=N(index=7,serial=11,address=0x10000,class_name='LevelSequence')
        source=N(by_index={7:obj})
        with patch('expedition33.cinematics.authored_import_job.ReadBatch',Reader),\
             patch('expedition33.cinematics.authored_import_job.capture_selected',return_value=source),\
             patch('expedition33.cinematics.authored_import_job._inspect_graph_steps',side_effect=steps):
            job=AuthoredImportJob(41,self.identity,executable='reader').start()
            yield job,created,entered,closed

    def test_completed_result_only_after_worker_reader_closes(self):
        gate=threading.Event();at_exit=threading.Event()
        def steps(*args,**kwargs):
            yield 1;yield 64
            at_exit.set()
            return {'sequence':'/Game/A.A','nodes':{str(i):{} for i in range(64)}}
        for job,created,entered,closed in self.launch(steps,exit_gate=gate):
            self.assertTrue(at_exit.wait(2));self.assertEqual(job.poll().state,'running')
            self.assertEqual(job.poll().nodes,64);self.assertFalse(closed)
            gate.set();job._thread.join(2)
            result=job.poll();self.assertEqual(result.state,'completed');self.assertEqual(result.nodes,64)
            self.assertEqual(result.graph['sequence'],'/Game/A.A')
            self.assertEqual(created[0][0],entered[0]);self.assertEqual(entered,closed)
            self.assertNotEqual(entered[0],threading.get_ident())
            self.assertIs(created[0][2]['_cancel'],job._cancel)
            self.assertNotIn('_timing',created[0][2])
            with self.assertRaises(RuntimeError):job.start()

    def test_installed_v236_reader_and_reference_signatures_are_supported(self):
        calls=[]
        class LegacyReader:
            def __init__(self,pid,*,share=False,_executable=None,_cancel=None):
                calls.append(('reader',pid,share))
            def __enter__(self):return self
            def __exit__(self,*args):calls.append(('close',))
        obj=N(index=7,serial=11,address=0x10000,class_name='LevelSequence')
        def legacy_read_many(catalog,observed,*,fields=None):
            calls.append(('read_many',fields));return {}
        def steps(catalog,asset,read,*,max_nodes,read_many,metrics):
            read_many(catalog,[asset],fields=('Actor',))
            yield 1
            return {'nodes':{'fresh':{}}}
        with patch('expedition33.cinematics.authored_import_job.ReadBatch',LegacyReader),\
             patch('expedition33.cinematics.authored_import_job.capture_selected',return_value=N(by_index={7:obj})),\
             patch('expedition33.cinematics.authored_import_job.read_values_many_with_references',legacy_read_many),\
             patch('expedition33.cinematics.authored_import_job._inspect_graph_steps',side_effect=steps):
            job=AuthoredImportJob(41,self.identity).start();job._thread.join(3)
        self.assertEqual(job.poll().state,'completed')
        self.assertEqual(calls,[('reader',41,True),('read_many',('Actor',)),('close',)])

    def test_cancellation_is_nonblocking_and_hides_a_late_result(self):
        gate=threading.Event();started=threading.Event()
        def steps(*args,**kwargs):
            started.set();gate.wait(2);yield 1
            return {'nodes':{'x':{}}}
        for job,_,_,closed in self.launch(steps):
            self.assertTrue(started.wait(2));self.assertFalse(job.close())
            self.assertEqual(job.poll().state,'cancelling');self.assertIsNone(job.poll().graph)
            gate.set();job._thread.join(2)
            self.assertTrue(closed);self.assertTrue(job.close())
            self.assertEqual(job.poll().state,'cancelled');self.assertIsNone(job.poll().graph)

    def test_cancel_after_completion_discards_published_graph(self):
        def steps(*args,**kwargs):
            yield 1
            return {'nodes':{'x':{}}}
        for job,_,_,_ in self.launch(steps):
            job._thread.join(2);self.assertEqual(job.poll().state,'completed')
            job.cancel();self.assertEqual(job.poll().state,'cancelled');self.assertIsNone(job.poll().graph)

    def test_reader_and_bad_identity_failure_are_terminal(self):
        def steps(*args,**kwargs):
            yield 1
            raise ValueError('bad source')
        for job,_,_,closed in self.launch(steps):
            job._thread.join(2);result=job.poll()
            self.assertEqual(result.state,'failed');self.assertIn('bad source',result.error);self.assertTrue(closed)
        for identity in ((7,11,1),(7,True,0x10000),[7,11,0x10000]):
            with self.assertRaises(ValueError):AuthoredImportJob(41,identity)

    def test_partial_read_restarts_entire_import_with_new_reader_and_metrics(self):
        attempts=[];generator_closed=[]
        def steps(*args,**kwargs):
            attempt=len(attempts);attempts.append(kwargs['metrics'])
            kwargs['metrics']['attempt_marker']=attempt
            try:
                if attempt==0:
                    yield 64
                    raise partial_read()
                yield 1
                return {'nodes':{'fresh':{}}}
            finally:generator_closed.append(attempt)
        for job,created,entered,closed in self.launch(steps):
            job._thread.join(3);result=job.poll()
            self.assertEqual(result.state,'completed');self.assertEqual(result.graph,{'nodes':{'fresh':{}}})
            self.assertEqual(result.timing['read_retries'],1);self.assertEqual(result.timing['attempt_marker'],1)
            self.assertEqual(len(created),2);self.assertIsNot(attempts[0],attempts[1])
            self.assertEqual(entered,closed);self.assertEqual(generator_closed,[0,1])

    def test_retry_is_bounded_and_other_errors_are_terminal(self):
        for error,expected in ((partial_read(),2),(RuntimeQueryError('other failure'),1),
                               (partial_read('READ_FAILED address=0x1234 win32=5'),1),
                               (ReadCancelled('cancelled'),1)):
            attempts=[]
            def steps(*args,**kwargs):
                attempts.append(1);yield 1;raise error
            for job,created,_,closed in self.launch(steps):
                job._thread.join(3);self.assertEqual(len(created),expected)
                self.assertEqual(len(closed),expected);self.assertEqual(len(attempts),expected)
                self.assertEqual(job.poll().state,'cancelled' if isinstance(error,ReadCancelled) else 'failed')

    def test_cancel_while_failed_reader_closes_prevents_retry(self):
        gate=threading.Event();failed=threading.Event()
        def steps(*args,**kwargs):
            yield 1;failed.set();raise partial_read()
        for job,created,_,closed in self.launch(steps,exit_gate=gate):
            self.assertTrue(failed.wait(2));self.assertFalse(job.close());gate.set();job._thread.join(2)
            self.assertEqual(len(created),1);self.assertEqual(len(closed),1)
            self.assertEqual(job.poll().state,'cancelled');self.assertIsNone(job.poll().graph)

    def test_retry_rechecks_identity_after_reader_cleanup(self):
        events=[]
        class Reader:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):events.append('enter');return self
            def __exit__(self,*args):events.append('exit')
        good=N(index=7,serial=11,address=0x10000,class_name='LevelSequence')
        changed=N(index=7,serial=12,address=0x10000,class_name='LevelSequence')
        def capture(*args):
            events.append('capture')
            return N(by_index={7:good if events.count('capture')==1 else changed})
        def steps(*args,**kwargs):
            yield 1;raise partial_read()
        with patch('expedition33.cinematics.authored_import_job.ReadBatch',Reader),\
             patch('expedition33.cinematics.authored_import_job.capture_selected',side_effect=capture),\
             patch('expedition33.cinematics.authored_import_job._inspect_graph_steps',side_effect=steps):
            job=AuthoredImportJob(41,self.identity).start();job._thread.join(3)
        self.assertEqual(events,['enter','capture','exit','enter','capture','exit'])
        self.assertEqual(job.poll().state,'failed');self.assertIn('identity changed',job.poll().error)
        self.assertIsNone(job.poll().graph)

    def test_matching_failure_during_generator_cleanup_is_not_retried(self):
        def steps(*args,**kwargs):
            class Steps:
                def __next__(self):raise ValueError('non-read failure')
                def close(self):raise partial_read()
            return Steps()
        for job,created,_,closed in self.launch(steps):
            job._thread.join(2)
            self.assertEqual(job.poll().state,'failed');self.assertEqual(len(created),1);self.assertEqual(len(closed),1)

    def test_reader_cleanup_failure_does_not_start_retry(self):
        created=[]
        class Reader:
            def __init__(self,*args,**kwargs):created.append(self)
            def __enter__(self):return self
            def __exit__(self,*args):raise RuntimeError('reader cleanup failed')
        obj=N(index=7,serial=11,address=0x10000,class_name='LevelSequence')
        def steps(*args,**kwargs):
            yield 1;raise partial_read()
        with patch('expedition33.cinematics.authored_import_job.ReadBatch',Reader),\
             patch('expedition33.cinematics.authored_import_job.capture_selected',return_value=N(by_index={7:obj})),\
             patch('expedition33.cinematics.authored_import_job._inspect_graph_steps',side_effect=steps):
            job=AuthoredImportJob(41,self.identity).start();job._thread.join(3)
        self.assertEqual(len(created),1);self.assertEqual(job.poll().state,'failed')
        self.assertIn('reader cleanup failed',job.poll().error)

    def test_partial_read_classifier_is_exact(self):
        self.assertTrue(_partial_read_failure(partial_read()))
        self.assertTrue(_partial_read_failure(partial_read('READ_FAILED address=0x1234 size=32 received=8 '
                         'region_state=0x1000 region_protect=0x4 win32=299')))
        for message in ('READ_FAILED address=0x1234 win32=299 extra',
                        'READ_FAILED address=0x1234 size=32 received=8 region_state=0x1000 win32=299',
                        'READ_FAILED address=0x1234 win32=5'):
            self.assertFalse(_partial_read_failure(partial_read(message)))
        self.assertFalse(_partial_read_failure(RuntimeQueryError('READ_FAILED address=0x1234 win32=299')))
        self.assertFalse(_partial_read_failure(ReadCancelled('Read worker rejected query: '+
                         '{"event":"error","message":"READ_FAILED address=0x1234 win32=299"}')))

    def test_reader_wait_honors_cancellation_and_cannot_borrow_parent(self):
        cancel=threading.Event();reader=ReadBatch(41,_cancel=cancel)
        timer=threading.Timer(.03,cancel.set);timer.start();start=time.monotonic()
        try:
            with self.assertRaises(ReadCancelled):reader._line(time.monotonic()+5)
        finally:timer.join()
        self.assertLess(time.monotonic()-start,1.)
        parent=ReadBatch(41,share=True);token=_active.set(parent)
        try:
            with self.assertRaisesRegex(Exception,'nested'):ReadBatch(41,_cancel=threading.Event()).__enter__()
        finally:_active.reset(token)

    def test_inflight_cancel_closes_reader_on_its_owner_and_never_retries(self):
        import io
        from unittest.mock import Mock
        cancel=threading.Event();reader=ReadBatch(41,_cancel=cancel)
        stdin=io.StringIO();stdout=io.StringIO()
        process=N(stdin=stdin,stdout=stdout,wait=Mock(return_value=0),kill=Mock())
        reader._process=process;reader._token=object()
        timer=threading.Timer(.03,cancel.set);timer.start()
        try:
            with self.assertRaises(ReadCancelled):reader.query(['--catalog'])
        finally:timer.join()
        self.assertTrue(reader._closed);self.assertTrue(stdin.closed);self.assertTrue(stdout.closed)
        self.assertEqual(reader._sequence,1);process.wait.assert_called_once()
        with self.assertRaisesRegex(Exception,'closed'):reader.query(['--catalog'])


if __name__=='__main__':unittest.main()
