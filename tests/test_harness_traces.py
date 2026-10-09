from types import SimpleNamespace
import unittest
from expedition33.introspection import Harness, UnsupportedCapability


class NativeTrace:
    def __init__(self):
        self.state = 'active'; self.events = []; self.closed = False
        self.observed = self.dropped = 0
    def read(self):
        batch, self.events = tuple(self.events[:8]), self.events[8:]
        return batch
    def status(self):
        return SimpleNamespace(observed=self.observed, dropped=self.dropped, rejected=0)
    def stop(self): self.state = 'stopped'
    def close(self): self.closed = True; self.state = 'forgotten'


class HarnessTraceTests(unittest.TestCase):
    def fixture(self):
        traces = []
        def start(*args, **kwargs):
            handle = NativeTrace(); traces.append((handle, args, kwargs)); return handle
        session = SimpleNamespace(supports_reflected_invocation=True, supports_traces=True, trace=start)
        harness = Harness(session)
        backend = harness._backend
        obj = SimpleNamespace(pid=99, index=3, serial=4, class_index=2)
        function = SimpleNamespace(outer_index=2)
        catalog = SimpleNamespace(objects=[obj], by_index={3: obj}, ancestors=lambda _: (2,))
        backend.refresh = lambda: setattr(backend, 'catalog', catalog)
        backend.find_object = lambda kind, path: SimpleNamespace(_observed=function if kind == 'Function' else obj)
        backend.wrap = lambda value: SimpleNamespace(path='/Actor')
        harness._explorer.ref = lambda value: {'$object': value.path}
        return harness, traces, obj

    def test_original_request_contract_preserves_history_and_reports_loss(self):
        harness, traces, obj = self.fixture()
        started = harness.request(dict(op='trace_start', name='sample', function='/Actor:Fn',
                                       target={'$object': '/Actor'}, limit=10, seconds=5))
        self.assertEqual(started, dict(name='sample', limit=10, seconds=5))
        handle, args, kwargs = traces[0]
        self.assertIs(kwargs['target'], obj)
        self.assertEqual((kwargs['duration_ms'], kwargs['limit']), (5000, 10))
        handle.observed = 3; handle.dropped = 1
        handle.events = [SimpleNamespace(sequence=n, monotonic_ms=100 + n, pid=99, index=3,
            serial=4, arguments={'Value': n}, return_value=n * 2) for n in (1, 3)]
        result = harness.request(dict(op='trace_read', name='sample'))
        self.assertEqual((result['count'], result['observed'], result['dropped']), (2, 3, 1))
        self.assertEqual([e['sequence'] for e in result['events']], [1, 3])
        self.assertEqual(result['events'][1]['return'], 6)
        self.assertEqual(result['events'][0]['target_resolution'], 'drain_time')
        stopped = harness.request(dict(op='trace_stop', name='sample'))
        self.assertFalse(stopped['active'])
        self.assertEqual(stopped['events'], result['events'])
        forgotten = harness.request(dict(op='trace_stop', name='sample', forget=True))
        self.assertEqual(forgotten['count'], 2)
        self.assertTrue(handle.closed)
        self.assertFalse(harness._explorer.traces)
        harness.close()

    def test_unfiltered_exemplar_duplicate_rejection_stale_target_and_close(self):
        harness, traces, obj = self.fixture()
        harness.request(dict(op='trace_start', name='all', function='/Actor:Fn'))
        handle, args, kwargs = traces[0]
        self.assertIs(args[1], obj); self.assertIsNone(kwargs['target'])
        with self.assertRaises(ValueError):
            harness.request(dict(op='trace_start', name='all', function='/Actor:Fn'))
        handle.observed = 1
        handle.events = [SimpleNamespace(sequence=1, monotonic_ms=101, pid=99, index=3,
            serial=999, arguments={}, return_value=False)]
        result = harness.request(dict(op='trace_read', name='all'))
        self.assertIn('$stale_object', result['events'][0]['target'])
        harness.close()
        self.assertTrue(handle.closed)

    def test_capability_gate_and_fixture_only_status(self):
        with self.assertRaises(UnsupportedCapability):
            Harness().request(dict(op='trace_start', name='x', function='/Fn'))
        harness, traces, obj = self.fixture()
        status = harness.request({'op': 'status'})
        self.assertIn('trace_start', status['operations'])
        self.assertEqual(status['trace_types'], ['native_scalar_post'])
        self.assertIn('live validation pending', status['trace_validation'])
        self.assertFalse(status['parity_complete'])
        harness.close()
