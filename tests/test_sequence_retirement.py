import struct
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _sequence_owner as sequence
from expedition33 import _media_owner as media


class SequenceRetirementTests(unittest.TestCase):
    def owner(self, module, capability):
        transport=N(command=Mock(),**{capability:1})
        session=N(_transport=transport,_check=lambda:None,_abort_ownership=Mock())
        owner=(module.NativeSequenceOwner if module is sequence else module.NativeMediaOwner)(N(_session=session))
        owner.state='armed'
        return owner,session

    def replies(self, owner, session, states):
        responses=iter(states)
        def command(name,data):
            error,state=next(responses)
            result=data[:24]+struct.pack('<II',error,state)+data[32:]
            return {('sequence_owner_packet' if isinstance(owner,sequence.NativeSequenceOwner) else 'media_owner_packet'):result.hex()}
        session._transport.command.side_effect=command

    def test_sequence_known_pending_retains_owner_and_close_uses_retire_only(self):
        owner,session=self.owner(sequence,'sequence_retirement_protocol')
        self.replies(owner,session,((1595,1),(407,1),(0,0)))
        self.assertFalse(owner.retire_world())
        self.assertFalse(owner.close())
        self.assertTrue(owner.close())
        self.assertEqual(owner.state,'closed')
        self.assertEqual([int.from_bytes(c.args[1][4:8],'little') for c in session._transport.command.call_args_list],[7,7,7])
        session._abort_ownership.assert_not_called()

    def test_sequence_unknown_never_aborts_unrelated_sdk_or_retries(self):
        for fault in ('lost','native','bad_state'):
            owner,session=self.owner(sequence,'sequence_retirement_protocol')
            if fault=='lost':session._transport.command.side_effect=OSError('lost')
            else:self.replies(owner,session,((1596,2) if fault=='native' else (0,1),))
            with self.assertRaises((RuntimeError,OSError)):owner.retire_world()
            with self.assertRaises(RuntimeError):owner.close()
            self.assertEqual(owner.state,'unknown');session._abort_ownership.assert_not_called()
            session._transport.command.assert_called_once()

    def test_media_retirement_pending_then_ack_never_calls_normal_close(self):
        owner,session=self.owner(media,'media_retirement_protocol')
        self.replies(owner,session,((1404,1),(0,0)))
        self.assertFalse(owner.retire_world());self.assertTrue(owner.close())
        self.assertEqual([int.from_bytes(c.args[1][4:8],'little') for c in session._transport.command.call_args_list],[4,4])
        session._abort_ownership.assert_not_called()

    def test_media_unknown_keeps_owner_without_session_abort(self):
        owner,session=self.owner(media,'media_retirement_protocol')
        self.replies(owner,session,((1403,2),))
        with self.assertRaises(RuntimeError):owner.retire_world()
        self.assertEqual(owner.state,'unknown');session._abort_ownership.assert_not_called()

    def test_missing_capability_and_hidden_payload_rejected(self):
        owner,session=self.owner(sequence,'sequence_retirement_protocol')
        session._transport.sequence_retirement_protocol=0
        with self.assertRaises(RuntimeError):owner.retire_world()
        session._transport.command.assert_not_called()
        data=sequence.HEADER.pack(1,7,42,0,0,0)+bytes(sequence.SIZE-32)
        sequence.validate_request(data)
        with self.assertRaises(ValueError):sequence.validate_request(data[:-1]+b'\1')
