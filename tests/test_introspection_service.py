import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from expedition33.introspection.service import FileService

spec = importlib.util.spec_from_file_location('e33_client_test',
    Path(__file__).resolve().parents[1] / 'scripts/e33_introspect.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class FakeHarness:
    SUPPORTED = {'status'}
    def __init__(self): self.calls = []
    def request(self, request):
        self.calls.append(request)
        if request.get('fail'): raise SystemExit('contained')
        return {'operations': ['status']}


class FileServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.harness = FakeHarness()
        self.service = FileService(self.data, self.harness, 123)
        self.addCleanup(self.service.close)

    def publish(self, name='test', **fields):
        request = dict(op='status', session=self.service.session, expires=time.time() + 60)
        request.update(fields)
        (self.data / 'requests' / (name + '.json')).write_text(json.dumps(request))
        self.service._last_poll = 0
        self.service.pump()
        return json.loads((self.data / 'responses' / (name + '.json')).read_text())

    def test_sessions_expiry_and_exception_recovery(self):
        self.assertTrue(self.publish()['ok'])
        self.assertFalse(self.publish('stale', session='old')['ok'])
        self.assertFalse(self.publish('expired', expires=0)['ok'])
        self.assertFalse(self.publish('infinite', expires=float('inf'))['ok'])
        self.assertFalse(self.publish('error', fail=True)['ok'])
        self.assertTrue(self.publish('recovered')['ok'])
        self.assertEqual(len(self.harness.calls), 3)

    def test_malformed_and_oversized_request(self):
        for name, text in [('broken', '{'), ('large', 'x' * 65537), ('notdict', '[]')]:
            (self.data / 'requests' / (name + '.json')).write_text(text)
            self.service._last_poll = 0; self.service.pump()
            self.assertFalse(json.loads((self.data / 'responses' / (name + '.json')).read_text())['ok'])
        self.assertFalse(self.harness.calls)

    def test_claim_unknown_outcome_is_never_replayed(self):
        pending = self.data / 'requests/collision.json'
        claimed = pending.with_suffix('.processing')
        claimed.write_text('original claim')
        pending.write_text('{}')
        self.service.pump()
        self.assertEqual(claimed.read_text(), 'original claim')
        self.assertFalse(pending.exists())
        self.assertFalse(self.harness.calls)

    def test_restart_changes_session_and_disables_heartbeat(self):
        old = self.service.session
        self.service.close()
        self.assertFalse(json.loads((self.data / 'status.json').read_text())['enabled'])
        self.service = FileService(self.data, self.harness, 123)
        self.addCleanup(self.service.close)
        self.assertNotEqual(old, self.service.session)
        self.assertFalse(self.publish(session=old)['ok'])

    def test_client_roundtrip_and_timeout_does_not_resubmit(self):
        def service(_):
            self.service._last_poll = 0; self.service.pump()
        with patch.object(client.time, 'sleep', side_effect=service):
            result = client.send({'op': 'status'}, self.data, 2)
        self.assertTrue(result['ok'])
        with self.assertRaises(TimeoutError): client.send({'op': 'status'}, self.data, .01)
        self.assertEqual(len(list((self.data / 'requests').glob('*.json'))), 1)

    def test_response_bounds(self):
        with patch.object(self.harness, 'request', return_value={'large': 'x' * 262144}):
            result = self.publish()
        self.assertFalse(result['ok'])
        self.assertLess((self.data / 'responses/test.json').stat().st_size, 262144)

    def test_client_rejects_invalid_timeout_before_enqueue(self):
        for timeout in (0, -1, float('inf'), float('nan'), 301):
            with self.assertRaises(ValueError): client.send({'op': 'status'}, self.data, timeout)
        self.assertFalse(list((self.data / 'requests').glob('*')))


if __name__ == '__main__': unittest.main()
