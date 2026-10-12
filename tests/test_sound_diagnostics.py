"""Offline negotiated sound op4 wire validation, no process or socket access."""
import pathlib
import sys
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33._cinematic_sound_event import NativeCinematicSoundEvent, HEADER, SIZE, validate_request


class SoundDiagnosticsTests(unittest.TestCase):
    def owner(self, counts=(5,4,3,2,1,0), *, failed=0, state=1, observed=1, mutate=lambda value: value):
        session = SimpleNamespace(_check=Mock(), _abort_ownership=Mock())
        def reply(name, request):
            self.assertEqual(name, 'cinematic-sound-event')
            validate_request(request)
            self.assertEqual(HEADER.unpack_from(request)[1], 4)
            data = bytearray(request)
            struct.pack_into('<4I', data, 24, 0,state,observed,failed)
            struct.pack_into('<6I', data, 40, *counts)
            return {'cinematic_sound_event_packet': bytes(mutate(data)).hex()}
        session._transport = SimpleNamespace(cinematic_sound_diagnostics_protocol=1, command=Mock(side_effect=reply))
        owner = NativeCinematicSoundEvent(SimpleNamespace(_session=session, _audio_owners=[]))
        owner.state='armed'
        return owner,session

    def test_ordered_counts_and_selection_exception_do_not_require_failed_equality(self):
        owner,session=self.owner((5,4,3,2,1,2),failed=1,state=2)
        result=owner.diagnostics()
        self.assertEqual(result['failures'],2)
        self.assertEqual(owner.failed,1)
        self.assertEqual(owner.state,'quarantined')
        session._abort_ownership.assert_not_called()

    def test_every_stage_inversion_rejects_and_revokes_owner(self):
        for index in range(1,5):
            counts=[1]*5+[0]; counts[index]=2
            owner,session=self.owner(counts)
            with self.assertRaises(ValueError): owner.diagnostics()
            self.assertEqual(owner.state,'unknown')
            session._abort_ownership.assert_called_once()

    def test_shape_header_and_tail_corruption_rejected(self):
        def word(offset,value):
            def change(data): struct.pack_into('<I',data,offset,value); return data
            return change
        for mutate in (lambda data:data[:-1],lambda data:data+b'\0',word(0,2),word(4,3),
                       word(16,1),word(24,1501),word(28,0),word(28,3),word(64,1)):
            owner,session=self.owner(mutate=mutate)
            with self.assertRaises(ValueError): owner.diagnostics()
            session._abort_ownership.assert_called_once()

    def test_header_failures_cannot_exceed_diagnostic_failure_count(self):
        owner,session=self.owner(failed=1)
        with self.assertRaises(ValueError): owner.diagnostics()
        session._abort_ownership.assert_called_once()

    def test_missing_negotiation_and_inactive_owner_never_send(self):
        owner,session=self.owner()
        session._transport.cinematic_sound_diagnostics_protocol=0
        with self.assertRaises(RuntimeError): owner.diagnostics()
        session._transport.command.assert_not_called()
        session._transport.cinematic_sound_diagnostics_protocol=1
        owner.state='closed'
        with self.assertRaises(RuntimeError): owner.diagnostics()
        session._transport.command.assert_not_called()
        session._abort_ownership.assert_not_called()

    def test_zero_eligible_is_valid_absence_of_observation(self):
        owner,session=self.owner((0,)*6,observed=0)
        self.assertEqual(owner.diagnostics()['selected_dispatches'],0)
        session._abort_ownership.assert_not_called()

    def test_impossible_failure_or_observation_counts_reject(self):
        for counts, observed in (((5,4,3,2,1,6),1), ((5,4,3,2,1,0),2)):
            owner, session = self.owner(counts, observed=observed)
            with self.assertRaises(ValueError): owner.diagnostics()
            session._abort_ownership.assert_called_once()

    def test_saturated_dispatch_count_allows_legacy_observation_wrap(self):
        owner, session = self.owner((0xffffffff,)*5+(0,), observed=0)
        self.assertEqual(owner.diagnostics()['selected_dispatches'], 0xffffffff)
        session._abort_ownership.assert_not_called()


if __name__=='__main__': unittest.main()
