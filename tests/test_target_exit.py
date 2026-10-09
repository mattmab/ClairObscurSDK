import json
import queue
import unittest
from expedition33 import RuntimeQueryError, TargetExitedError
from expedition33._session import SessionTransport


class TargetExitTests(unittest.TestCase):
    def transport(self, value):
        transport = SessionTransport.__new__(SessionTransport)
        transport.target_exit_code = None
        transport._lines = queue.Queue()
        transport._lines.put(json.dumps(value))
        return transport

    def test_exit_reports_preserve_normal_and_crash_codes(self):
        for code in (0, 7, 259, 0xc0000005):
            transport = self.transport({'event': 'target_exited', 'exit_code': code})
            with self.assertRaises(TargetExitedError) as caught:
                transport._read()
            self.assertEqual(caught.exception.exit_code, code)
            self.assertEqual(transport.target_exit_code, code)
            self.assertIn('unknown outcome', str(caught.exception))

    def test_malformed_reports_and_timeouts_do_not_prove_exit(self):
        for code in (None, True, -1, 0x100000000, '0'):
            transport = self.transport({'event': 'target_exited', 'exit_code': code})
            with self.assertRaises(RuntimeQueryError) as caught:
                transport._read()
            self.assertNotIsInstance(caught.exception, TargetExitedError)
            self.assertIsNone(transport.target_exit_code)
        transport = self.transport({'event': 'error', 'message': 'SESSION_COMMAND_TIMEOUT'})
        with self.assertRaises(RuntimeQueryError) as caught:
            transport._read()
        self.assertNotIsInstance(caught.exception, TargetExitedError)
        self.assertIsNone(transport.target_exit_code)
