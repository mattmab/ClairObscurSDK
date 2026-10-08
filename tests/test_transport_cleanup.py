import unittest
from unittest.mock import Mock
from expedition33._session import SessionTransport


class TransportCleanupTests(unittest.TestCase):
    def test_dead_pipe_flush_does_not_mask_disconnect(self):
        transport = SessionTransport.__new__(SessionTransport)
        transport._closed = False
        transport._process = Mock()
        transport._process.poll.return_value = 1
        transport._process.stdin.close.side_effect = OSError('broken pipe flush')
        transport._reader = Mock()
        transport._abort()
        self.assertTrue(transport._closed)
        transport._process.kill.assert_not_called()
        transport._reader.join.assert_called_once()
        transport._process.stdout.close.assert_called_once()
