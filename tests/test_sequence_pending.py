import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33 import _sequence_owner as staged


class PendingSequenceTests(unittest.TestCase):
    def setUp(self):
        self.session = SimpleNamespace(_check=Mock(), _abort_ownership=Mock(), _transport=SimpleNamespace(command=Mock()))
        self.owner = staged.NativeSequenceOwner(SimpleNamespace(_session=self.session))
        self.owner.state = 'armed'

    def replies(self, *pairs):
        responses = iter(pairs)
        def command(name, request):
            error, state = next(responses)
            data = bytearray(request)
            staged.struct.pack_into('<II', data, 24, error, state)
            return {'sequence_owner_packet': data.hex()}
        self.session._transport.command.side_effect = command

    def test_composite_close_deferral_preserves_owner_until_full_ack(self):
        self.replies((407, 0), (0, 0))
        self.assertFalse(self.owner.close())
        self.assertEqual(self.owner.status(), 'cleanup_pending')
        self.assertEqual(self.session._transport.command.call_count, 1)
        with self.assertRaisesRegex(RuntimeError, 'Only sequence cleanup'):
            self.owner._send(3)
        self.assertTrue(self.owner.close())
        self.assertEqual(self.owner.state, 'closed')
        self.session._abort_ownership.assert_not_called()

    def test_sequence_predispatch_deferral_also_blocks_playback_until_close(self):
        self.replies((407, 1), (0, 0))
        self.assertFalse(self.owner.close())
        self.assertEqual(self.owner.status(), 'cleanup_pending')
        self.assertTrue(self.owner.close())

    def test_407_state_zero_is_not_accepted_for_status(self):
        self.replies((407, 0))
        with self.assertRaisesRegex(RuntimeError, 'Native sequence rejected'):
            self.owner.status()
        self.session._abort_ownership.assert_called_once()
        self.assertEqual(self.owner.state, 'unknown')

    def test_407_armed_state_is_also_rejected_for_status(self):
        self.replies((407, 1))
        with self.assertRaisesRegex(RuntimeError, 'Native sequence rejected'):
            self.owner.status()
        self.session._abort_ownership.assert_called_once()
        self.assertEqual(self.owner.state, 'unknown')

    def test_unknown_or_other_error_still_aborts(self):
        self.replies((1473, 0))
        with self.assertRaisesRegex(RuntimeError, '1473'):
            self.owner.close()
        self.session._abort_ownership.assert_called_once()

    def test_abort_failure_does_not_replace_native_error(self):
        self.replies((1493, 0))
        self.session._abort_ownership.side_effect = OSError('abort pipe failed')
        with self.assertRaisesRegex(RuntimeError, '1493') as result:
            self.owner.close()
        self.assertIn('abort pipe failed', result.exception.__notes__[0])
        self.assertEqual(self.owner.state, 'unknown')

    def diagnostic_reply(self, *, error=1493, state=0, mutate=None):
        values = [0x44413345, 1, 64, 0, 3, 1493, 201, 0, 2, 0, 0, 0, 1, 0, 0, 0]
        def command(name, request):
            data = bytearray(request)
            staged.struct.pack_into('<II', data, 24, error, state)
            data[32:96] = staged.AUDIO_DIAGNOSTIC.pack(*values)
            if mutate:
                mutate(data)
            return {'sequence_owner_packet': data.hex()}
        self.session._transport.command.side_effect = command

    def test_failed_native_close_preserves_negotiated_diagnostics_before_abort(self):
        self.session._transport.audio_cleanup_diagnostics_protocol = 1
        self.diagnostic_reply()
        with self.assertRaisesRegex(RuntimeError, '1493'):
            self.owner.close()
        self.assertEqual(self.owner.cleanup_diagnostics['phase'], 3)
        self.assertEqual(self.owner.cleanup_diagnostics['native_error'], 201)
        self.assertEqual(self.owner.cleanup_diagnostics['owner_state'], 2)
        self.session._abort_ownership.assert_called_once()

    def test_legacy_does_not_accept_diagnostic_payload(self):
        self.diagnostic_reply()
        with self.assertRaisesRegex(ValueError, 'acknowledgement mismatch'):
            self.owner.close()
        self.assertIsNone(self.owner.cleanup_diagnostics)

    def test_malformed_diagnostics_never_become_cached_evidence(self):
        mutations = ((0, 0), (1, 2), (2, 63), (3, 1), (4, 17), (7, 3), (8, 4), (9, 65),
                     (10, 2), (11, 65), (12, 65), (13, 65))
        for index, value in mutations:
            self.setUp()
            self.session._transport.audio_cleanup_diagnostics_protocol = 1
            self.diagnostic_reply(mutate=lambda data, i=index, v=value: staged.struct.pack_into('<I', data, 32 + 4*i, v))
            with self.assertRaises(ValueError):
                self.owner.close()
            self.assertIsNone(self.owner.cleanup_diagnostics)
            self.session._abort_ownership.assert_called_once()

    def test_nonzero_unused_tail_is_rejected(self):
        self.session._transport.audio_cleanup_diagnostics_protocol = 1
        self.diagnostic_reply(mutate=lambda data: data.__setitem__(96, 1))
        with self.assertRaisesRegex(ValueError, 'tail'):
            self.owner.close()
        self.assertIsNone(self.owner.cleanup_diagnostics)

    def test_successful_or_deferred_close_can_include_valid_snapshot(self):
        for error in (0, 407):
            self.setUp()
            self.session._transport.audio_cleanup_diagnostics_protocol = 1
            self.diagnostic_reply(error=error)
            self.assertEqual(self.owner.close(), error == 0)
            self.assertIsNotNone(self.owner.cleanup_diagnostics)
            self.session._abort_ownership.assert_not_called()
