import unittest
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.sdk import Session
import test_multi_button_transport as multi


class PauseVectorTests(unittest.TestCase):
    def backend(self):
        backend = multi.MultiButtonTransportTests().backend()
        backend.trace_protocol = 1
        backend.trace_capacity = 16
        backend.keybind_protocol = 1
        backend.keybind_capacity = 96
        backend.ui_batch_protocol = 1
        backend.pause_attachment_protocol = 2
        backend.vector_value_protocol = 1
        return backend

    def test_pause_launcher_implicitly_includes_vectors(self):
        for explicit in (False, True):
            backend = self.backend()
            with patch('expedition33.sdk.SessionTransport', return_value=backend) as factory:
                with Session(pause_menu=True, vector_values=explicit) as session:
                    self.assertTrue(session.supports_vector_values)
                    self.assertTrue(session.supports_multi_controls)
                    self.assertIn('research-probe-v23-pause-vector',
                                  str(factory.call_args.kwargs['_executable']))

    def test_missing_or_invalid_vector_capability_closes_connection(self):
        for protocol in (0, True, 2, '1'):
            backend = self.backend()
            backend.vector_value_protocol = protocol
            with patch('expedition33.sdk.SessionTransport', return_value=backend):
                with self.assertRaisesRegex(RuntimeQueryError, 'Vector backend handshake'):
                    Session(pause_menu=True)
            self.assertTrue(backend._closed)
