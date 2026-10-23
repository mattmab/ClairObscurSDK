from dataclasses import FrozenInstanceError
import importlib.util
from pathlib import Path
import sys
import threading
from types import SimpleNamespace as N
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/admission_monitor.py'
spec=importlib.util.spec_from_file_location('admission_monitor_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


class MonitorTests(unittest.TestCase):
    def test_original_read_traceback_is_local_while_snapshot_stays_sanitized(self):
        class Observer:
            def observe(self):raise RuntimeError('fixture observation detail')
            def close(self):pass
        with self.assertLogs('expedition33.readiness.local',level='ERROR') as logs:
            monitor=m.ReadOnlyAdmissionMonitor(Observer)
            self.assertTrue(monitor.closed.wait(.5))
        self.assertIn('Traceback',logs.output[0]);self.assertIn('fixture observation detail',logs.output[0])
        with self.assertRaisesRegex(RuntimeError,'observe:RuntimeError') as error:monitor.snapshot()
        self.assertNotIn('fixture observation detail',str(error.exception));monitor.close()
    def test_runtime_query_failure_is_pending_then_fresh_observer_recovers(self):
        from expedition33 import RuntimeQueryError
        failed=threading.Event();resume=threading.Event();created=[];closed=[]
        class Observer:
            def __init__(self):self.number=len(created);created.append(self)
            def observe(self):
                if self.number==0:
                    failed.set();raise RuntimeQueryError('private sample payload')
                resume.wait(.5);return N(state='world_ready')
            def close(self):closed.append(self.number)
        monitor=m.ReadOnlyAdmissionMonitor(Observer,interval=.01)
        try:
            self.assertTrue(failed.wait(.5));self.assertTrue(monitor.updated.wait(.5))
            self.assertIsNone(monitor.snapshot())
            self.assertEqual(monitor.diagnostics(),dict(query_failures=1,last_query_failure='observe:RuntimeQueryError'))
            self.assertNotIn('private',str(monitor.diagnostics()))
            monitor.updated.clear();resume.set()
            self.assertTrue(monitor.updated.wait(.5))
            self.assertEqual(monitor.snapshot().admission.state,'world_ready')
            self.assertEqual(closed,[0]);self.assertEqual(len(created),2)
        finally:resume.set();monitor.close()

    def test_failed_sample_invalidates_prior_ready_without_same_call_retry(self):
        from expedition33 import RuntimeQueryError
        allow_failure=threading.Event();calls=[]
        class Observer:
            def observe(self):
                calls.append(1)
                if len(calls)==1:return N(state='world_ready')
                allow_failure.wait(.5);raise RuntimeQueryError('query failed')
            def close(self):pass
        monitor=m.ReadOnlyAdmissionMonitor(Observer,interval=.1)
        try:
            self.assertTrue(monitor.updated.wait(.5));self.assertIsNotNone(monitor.snapshot())
            monitor.updated.clear();allow_failure.set()
            self.assertTrue(monitor.updated.wait(.5));self.assertIsNone(monitor.snapshot())
            self.assertEqual(len(calls),2)
        finally:allow_failure.set();monitor.close()

    def test_transient_query_cleanup_failure_remains_fatal(self):
        from expedition33 import RuntimeQueryError
        class Observer:
            def observe(self):raise RuntimeQueryError('sample')
            def close(self):raise RuntimeError('private close detail')
        monitor=m.ReadOnlyAdmissionMonitor(Observer)
        self.assertTrue(monitor.closed.wait(.5))
        with self.assertRaisesRegex(RuntimeError,'close:RuntimeError'):monitor.snapshot()
        self.assertTrue(monitor.close())

    def test_slow_read_never_blocks_host_and_worker_owns_factory_read_and_close(self):
        release=threading.Event();entered=threading.Event();threads=[]
        class Observer:
            def __init__(self):threads.append(threading.get_ident())
            def observe(self):
                threads.append(threading.get_ident());entered.set();release.wait(1)
                return N(state='inactive')
            def close(self):threads.append(threading.get_ident())
        monitor=m.ReadOnlyAdmissionMonitor(Observer)
        try:
            self.assertTrue(entered.wait(.5))
            for _ in range(100):self.assertIsNone(monitor.snapshot())
            self.assertFalse(monitor.close(timeout=0))
        finally:
            release.set();self.assertTrue(monitor.closed.wait(.5));monitor.close()
        self.assertEqual(len(set(threads)),1)
        self.assertNotEqual(threads[0],threading.get_ident())

    def test_one_slot_immutable_result_and_age_uncertainty(self):
        now=[10.]
        class Observer:
            def observe(self):return N(state='world_ready',token=('epoch',))
            def close(self):pass
        monitor=m.ReadOnlyAdmissionMonitor(Observer,clock=lambda:now[0],interval=1.,max_age=.2)
        try:
            self.assertTrue(monitor.updated.wait(.5))
            result=monitor.snapshot()
            self.assertEqual(result.sequence,1)
            with self.assertRaises(FrozenInstanceError):result.sequence=2
            now[0]=10.3;self.assertIsNone(monitor.snapshot())
        finally:monitor.close()

    def test_failure_visible_no_retry_and_owner_cleanup(self):
        counts=[0,0]
        class Observer:
            def observe(self):counts[0]+=1;raise ValueError('private payload')
            def close(self):counts[1]+=1
        monitor=m.ReadOnlyAdmissionMonitor(Observer)
        self.assertTrue(monitor.closed.wait(.5))
        with self.assertRaisesRegex(RuntimeError,'observe:ValueError') as raised:monitor.snapshot()
        self.assertNotIn('private payload',str(raised.exception))
        self.assertEqual(counts,[1,1]);self.assertTrue(monitor.close())

    def test_factory_failure_has_distinct_phase_without_payload(self):
        def factory():raise RuntimeError('private factory detail')
        monitor=m.ReadOnlyAdmissionMonitor(factory)
        self.assertTrue(monitor.closed.wait(.5))
        with self.assertRaisesRegex(RuntimeError,'factory:RuntimeError') as raised:monitor.snapshot()
        self.assertNotIn('private factory detail',str(raised.exception))
        monitor.close()

    def test_new_epoch_results_replace_entire_snapshot(self):
        changed=threading.Event();calls=[0]
        class Observer:
            def observe(self):
                calls[0]+=1
                if calls[0]>1:changed.set()
                return ('epoch',calls[0])
            def close(self):pass
        monitor=m.ReadOnlyAdmissionMonitor(Observer,interval=.001)
        try:
            self.assertTrue(changed.wait(.5))
            monitor.updated.wait(.5)
            result=monitor.snapshot()
            self.assertEqual(result.admission,('epoch',result.sequence))
        finally:monitor.close()


if __name__=='__main__':unittest.main()
