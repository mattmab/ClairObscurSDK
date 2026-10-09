from types import SimpleNamespace
import unittest
from expedition33._scope import SessionScope


class NativeTrace:
    def __init__(self):
        self._state = 'active'
        self.calls = []
        self.fail = False
        self.plan = object()

    @property
    def state(self): return self._state
    def read(self): self.calls.append('read'); return (42,)
    def status(self): self.calls.append('status'); return self._state
    def stop(self): self.calls.append('stop'); self._state = 'stopped'
    def close(self):
        self.calls.append('close')
        if self.fail: raise RuntimeError('deferred')
        self._state = 'forgotten'


class TraceScopeTests(unittest.TestCase):
    def fixture(self):
        session = SimpleNamespace(_check=lambda: None, supports_traces=True, _traces=[], aborted=False,
            console=SimpleNamespace(dispatcher=SimpleNamespace(namespace={})))
        def abort(): session.aborted = True
        session._transport = SimpleNamespace(_abort=abort)
        def start(*args, **kwargs):
            native = NativeTrace(); session._traces.append(native); return native
        session.trace = start
        return session, SessionScope(session)

    def test_normal_unload_forgets_only_owned_trace_and_revokes_wrapper(self):
        session, scope = self.fixture()
        other = SessionScope(session)
        trace = scope.trace('fn', 'object')
        unrelated = other.trace('fn2', 'object')
        self.assertTrue(scope.supports_traces)
        self.assertEqual(trace.read(), (42,))
        scope.close()
        self.assertEqual(session._traces[0]._state, 'forgotten')
        self.assertEqual(unrelated.state, 'active')
        self.assertFalse(session.aborted)
        with self.assertRaisesRegex(RuntimeError, 'scope is closed'): trace.read()
        other.close()

    def test_manual_close_removes_scope_cleanup_obligation(self):
        session, scope = self.fixture()
        trace = scope.trace('fn', 'object')
        trace.stop(); trace.close(); scope.close()
        self.assertEqual(session._traces[0].calls, ['stop', 'close'])

    def test_child_scope_cleanup_and_failure_requests_session_shutdown(self):
        session, parent = self.fixture()
        child = SessionScope(parent)
        trace = child.trace('fn', 'object')
        parent.close()
        self.assertEqual(session._traces[0].calls, ['close'])
        with self.assertRaises(RuntimeError): trace.status()
        session, scope = self.fixture()
        scope.trace('fn', 'object')
        session._traces[0].fail = True
        with self.assertRaisesRegex(RuntimeError, 'trace cleanup'): scope.close()
        self.assertTrue(session.aborted)
        self.assertEqual(session._traces[0]._state, 'unknown')
