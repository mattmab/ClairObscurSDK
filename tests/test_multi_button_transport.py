import unittest
from unittest.mock import patch
from expedition33 import RuntimeQueryError, _multi_button_wire as wire
from expedition33.sdk import Session
import test_button_action_transport as legacy


class MultiButtonTransportTests(unittest.TestCase):
    def transport(self):
        value = legacy.ButtonActionTransportTests().transport()
        value.multi_button_protocol = 1
        value.multi_button_capacity = 16
        value._read = lambda: dict(event='session_response', command='multi-button', closed=False)
        return value

    def test_all_capabilities_required_before_send(self):
        for name in legacy.ButtonActionTransportTests.capabilities + ('multi_button_protocol',):
            for invalid in (0, True, 2):
                transport = self.transport(); setattr(transport, name, invalid)
                with self.assertRaises(ValueError): transport.command('multi-button', wire.request('drain', 1))
                self.assertEqual(transport._process.stdin.getvalue(), '')
        for name, values in [('multi_button_capacity', (0, 15, 17, True)),
                             ('button_action_session', (0, -1, True, 2**64))]:
            for invalid in values:
                transport = self.transport(); setattr(transport, name, invalid)
                with self.assertRaises(ValueError): transport.command('multi-button', wire.request('drain', 1))
                self.assertEqual(transport._process.stdin.getvalue(), '')

    def test_clean_payload_and_response_correlation(self):
        sent = wire.request('drain', 1)
        transport = self.transport()
        for invalid in (None, bytearray(sent), bytes(wire.SIZE), sent[:-1]):
            with self.assertRaises(ValueError): transport.command('multi-button', invalid)
        self.assertEqual(transport._process.stdin.getvalue(), '')
        transport.command('multi-button', sent)
        self.assertEqual(transport._process.stdin.getvalue(), 'multi-button ' + sent.hex() + '\n')
        transport._read = lambda: dict(event='session_response', command='button-action', closed=False)
        with self.assertRaises(RuntimeQueryError): transport.command('multi-button', sent)
        self.assertTrue(transport._closed)

    def backend(self):
        value = legacy.ButtonActionTransportTests().fake_backend()
        value.multi_button_protocol = 1; value.multi_button_capacity = 16
        return value

    def test_explicit_v17_selection_preserves_v16(self):
        for options, version in (({'multi_controls': True}, 17), ({'button_actions': True}, 16)):
            value = self.backend()
            with patch('expedition33.sdk.SessionTransport', return_value=value) as factory:
                with Session(**options) as session:
                    self.assertIn(f'research-probe-v{version}', str(factory.call_args.kwargs['_executable']))
                    self.assertTrue(session.supports_multi_controls)
        with self.assertRaises(ValueError): Session(multi_controls=1)

    def test_failed_handshake_closes_controller(self):
        for name, invalid in [('multi_button_protocol', True), ('multi_button_protocol', 0),
                              ('multi_button_capacity', 15), ('multi_button_capacity', True)]:
            value = self.backend(); setattr(value, name, invalid)
            with patch('expedition33.sdk.SessionTransport', return_value=value):
                with self.assertRaisesRegex(RuntimeQueryError, 'Multi-control'): Session(multi_controls=True)
            self.assertTrue(value._closed)

    def test_capability_query_checks_entire_chain(self):
        value = self.backend()
        with patch('expedition33.sdk.SessionTransport', return_value=value):
            with Session(multi_controls=True) as session:
                for name in legacy.ButtonActionTransportTests.capabilities:
                    original = getattr(value, name)
                    setattr(value, name, True)
                    self.assertFalse(session.supports_multi_controls, name)
                    setattr(value, name, original)
                value.button_action_session = True
                self.assertFalse(session.supports_multi_controls)

