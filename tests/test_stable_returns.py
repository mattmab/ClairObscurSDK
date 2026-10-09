import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.sdk import Session
from test_ownership import Transport


class StableReturnsTests(unittest.TestCase):
    def test_opt_in_and_required_capabilities(self):
        transport = Transport()
        transport.retained_protocol = transport.stable_identity_protocol = 1
        with patch('expedition33.sdk.SessionTransport', return_value=transport) as factory:
            with Session(stable_returns=True) as session:
                self.assertTrue(session.supports_stable_returns)
                self.assertTrue(session.supports_retained_invocation)
                self.assertIn('research-probe-v9', str(factory.call_args.kwargs['_executable']))
        self.assertTrue(transport._closed)

    def test_missing_capability_closes_open_transport(self):
        for missing in ('reflected_protocol', 'lease_protocol', 'retained_protocol', 'stable_identity_protocol'):
            transport = Transport()
            transport.retained_protocol = transport.stable_identity_protocol = 1
            setattr(transport, missing, 0)
            with patch('expedition33.sdk.SessionTransport', return_value=transport):
                with self.assertRaisesRegex(RuntimeQueryError, 'handshake'):
                    Session(stable_returns=True)
            self.assertTrue(transport._closed)

    def test_old_backend_does_not_claim_stable_returns(self):
        transport = Transport()
        transport.retained_protocol = 1
        with patch('expedition33.sdk.SessionTransport', return_value=transport):
            with Session(retained=True) as session:
                self.assertFalse(session.supports_stable_returns)

    def test_invalid_flag_does_not_open_transport(self):
        with patch('expedition33.sdk.SessionTransport') as factory:
            with self.assertRaises(ValueError): Session(stable_returns=1)
            factory.assert_not_called()
