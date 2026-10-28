import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33._pod_values import NumericStructValue, QUALIFIED_FRAME_TIME
from expedition33._sequence_endpoint import OwnedSequenceEndpoint, qualified_time, MAX_SUBFRAME
from expedition33.sequences import OwnedLevelSequence


def frame(number, sub=0., numerator=24, denominator=1):
    return NumericStructValue(QUALIFIED_FRAME_TIME, {
        'Time': {'FrameNumber': {'Value': number}, 'SubFrame': sub},
        'Rate': {'Numerator': numerator, 'Denominator': denominator},
    })


class OwnedSequenceEndpointTests(unittest.TestCase):
    def setUp(self):
        self.context = ((123,1,2,0x10000), (123,3,4,0x20000), (123,5,6,0x30000))
        self.endpoint = OwnedSequenceEndpoint(self.context, frame(240))

    def command(self, name, returned=True):
        ticket = self.endpoint.begin_command(name)
        self.endpoint.finish_command(ticket, returned=returned)

    def observe(self, number, *, sub=0., playing=False, paused=False, context=None, end=None):
        return self.endpoint.observe(context=self.context if context is None else context,
            current_time=frame(number, sub), end_time=frame(240) if end is None else end,
            playing=playing, paused=paused)

    def started(self):
        self.command('Play')
        self.observe(1, playing=True)

    def test_natural_endpoint_requires_playing_and_exact_end(self):
        self.started()
        self.assertEqual(self.observe(239, sub=MAX_SUBFRAME), 'endpoint_observed')

    def test_idle_before_play_is_not_end(self):
        self.assertEqual(self.observe(240), 'ready')

    def test_no_observed_playback_is_not_end(self):
        self.command('Play')
        self.assertEqual(self.observe(240), 'interrupted')

    def test_early_stop_is_not_end(self):
        self.started()
        self.assertEqual(self.observe(239), 'interrupted')

    def test_explicit_stop_at_end_is_cancelled(self):
        self.started()
        self.command('Stop')
        self.assertEqual(self.observe(239, sub=MAX_SUBFRAME), 'cancelled')

    def test_world_or_player_replacement_invalidates(self):
        self.started()
        changed = self.context[:2] + ((123,5,7,0x30000),)
        self.assertEqual(self.observe(240, context=changed), 'unknown')

    def test_changed_duration_invalidates(self):
        self.started()
        self.assertEqual(self.observe(240, end=frame(241)), 'unknown')

    def test_beyond_end_is_not_accepted_by_tolerance(self):
        self.started()
        self.assertEqual(self.observe(241), 'unknown')

    def test_pending_or_lost_play_ack_never_completes(self):
        ticket = self.endpoint.begin_command('Play')
        self.assertEqual(self.observe(240), 'unknown')
        self.endpoint.finish_command(ticket, returned=False)
        self.assertEqual(self.observe(240), 'unknown')

    def test_seek_invalidates_before_dispatch(self):
        self.started()
        with self.assertRaisesRegex(RuntimeError, 'Unreviewed'):
            self.endpoint.begin_command('SetPlaybackPosition')
        self.assertEqual(self.observe(240), 'unknown')

    def test_pause_at_endpoint_does_not_complete(self):
        self.started()
        self.command('Pause')
        self.assertEqual(self.observe(239, sub=MAX_SUBFRAME, paused=True), 'paused')
        self.command('Play')
        self.assertEqual(self.observe(239, sub=MAX_SUBFRAME), 'endpoint_observed')

    def test_unexpected_repeat_play_invalidates(self):
        self.started()
        with self.assertRaisesRegex(RuntimeError, 'first Play'):
            self.endpoint.begin_command('Play')
        self.assertEqual(self.observe(240), 'unknown')

    def test_equivalent_frame_rates_compare_exact_rational_times(self):
        self.assertEqual(qualified_time(frame(240)), qualified_time(frame(300, numerator=30)))

    def test_adjacent_float_subframe_is_not_accepted_as_terminal(self):
        self.started()
        self.assertEqual(self.observe(239, sub=float.fromhex('0x1.fffffcp-1')), 'interrupted')

    def test_fractional_upper_end_is_not_in_the_verified_profile(self):
        with self.assertRaisesRegex(ValueError, 'integer exclusive'):
            OwnedSequenceEndpoint(self.context, frame(240, .5))

    def test_changed_end_frame_rate_is_not_hidden_by_rational_equivalence(self):
        self.started()
        self.assertEqual(self.observe(239, sub=MAX_SUBFRAME, end=frame(300, numerator=30)), 'unknown')

    def test_exclusive_end_itself_is_not_the_verified_natural_terminal(self):
        self.started()
        self.assertEqual(self.observe(240), 'interrupted')

    def test_captured_shipping_phase_terminal(self):
        endpoint = OwnedSequenceEndpoint(self.context, frame(3687, numerator=60))
        ticket = endpoint.begin_command('Play')
        endpoint.finish_command(ticket, returned=True)
        endpoint.observe(context=self.context, current_time=frame(100, numerator=60),
                         end_time=frame(3687, numerator=60), playing=True, paused=False)
        self.assertEqual(endpoint.observe(context=self.context,
            current_time=frame(3686, MAX_SUBFRAME, numerator=60), end_time=frame(3687, numerator=60),
            playing=False, paused=False), 'endpoint_observed')

    def test_invalid_frame_rate_or_noncanonical_subframe_rejects(self):
        for invalid in (frame(1, numerator=0), frame(1, denominator=-1), frame(1, sub=1.)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                qualified_time(invalid)

    def test_mutable_or_partial_context_is_not_admitted(self):
        for invalid in (list(self.context), ((123,1,2),)*3,
                        self.context[:2]+((124,5,6,0x30000),)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                OwnedSequenceEndpoint(invalid, frame(240))

    def test_wrong_ack_cannot_be_repaired_by_late_correct_ack(self):
        ticket = self.endpoint.begin_command('Play')
        with self.assertRaises(RuntimeError):
            self.endpoint.finish_command(ticket+1, returned=True)
        with self.assertRaises(RuntimeError):
            self.endpoint.finish_command(ticket, returned=True)
        self.assertEqual(self.endpoint.state, 'unknown')


class SequenceEndpointIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.context = ((123,1,2,0x10000), (123,3,4,0x20000), (123,5,6,0x30000))
        self.sequence = object.__new__(OwnedLevelSequence)
        sequence = self.sequence
        sequence.scope = SimpleNamespace(_check=Mock(), _session=SimpleNamespace(_transport=SimpleNamespace()))
        sequence.owner = SimpleNamespace(status=Mock(return_value='armed'))
        sequence.state, sequence.uncertain = 'ready', False
        sequence._completion_invalidated=False
        sequence.player = object()
        sequence._endpoint = OwnedSequenceEndpoint(self.context, frame(240))
        sequence._function = lambda owner,name:name
        self.failure = None
        @contextmanager
        def invoke(**kwargs):
            if self.failure:
                raise self.failure
            yield SimpleNamespace(return_value=None)
        sequence.planner = SimpleNamespace(prepare=Mock(return_value=SimpleNamespace(invoke=invoke)))

    def test_explicit_stop_is_journalled_before_native_dispatch(self):
        self.sequence.play()
        self.sequence.stop()
        self.assertEqual(self.sequence._endpoint.state, 'cancelled')
        self.assertEqual(self.sequence.state, 'stopped')
        self.sequence.planner.prepare.assert_called_with(self.sequence.player, 'Stop')

    def test_dispatch_exception_cannot_complete_or_retry(self):
        self.failure = RuntimeError('lost acknowledgement')
        with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
            self.sequence.play()
        self.assertEqual(self.sequence._endpoint.state, 'unknown')
        self.assertTrue(self.sequence.uncertain)
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            self.sequence.play()
        self.assertEqual(self.sequence.planner.prepare.call_count, 1)

    def test_legacy_play_needs_no_endpoint_or_frame_time(self):
        self.sequence._endpoint = None
        self.sequence.play()
        self.assertEqual(self.sequence.state, 'playing')

    def test_read_only_query_group_checks_owner_twice_and_blocks_mutations(self):
        sequence=self.sequence
        with sequence._query_group():
            for name in ('IsPlaying','IsPaused','GetCurrentTime','GetEndTime'):sequence._call(name)
            with self.assertRaisesRegex(RuntimeError,'cannot mutate'):sequence.play()
        self.assertEqual(sequence.owner.status.call_count,2)
        self.assertEqual(sequence.planner.prepare.call_count,4)
        self.assertFalse(sequence._query_group_active)

    def test_query_group_rejects_changed_owner_and_does_not_leak_authority(self):
        sequence=self.sequence;sequence.owner.status.side_effect=('armed','closed')
        with self.assertRaisesRegex(RuntimeError,'changed during'):
            with sequence._query_group():sequence._call('IsPlaying')
        self.assertFalse(sequence._query_group_active)
        sequence.owner.status.side_effect=None;sequence.owner.status.return_value='closed'
        with self.assertRaisesRegex(RuntimeError,'context was closed'):sequence._call('IsPlaying')
        self.assertEqual(sequence.planner.prepare.call_count,1)

    def test_tracking_rejects_missing_native_timing_before_context_read(self):
        self.sequence._endpoint = None
        with patch('expedition33._sequence_endpoint.current_owned_context') as context:
            with self.assertRaisesRegex(RuntimeError, 'frame-time'):
                self.sequence.prepare_completion()
        context.assert_not_called()

    def test_boolean_protocol_flags_are_not_native_version_numbers(self):
        self.sequence._endpoint = None
        transport = self.sequence.scope._session._transport
        transport.frame_time_values_protocol = True
        transport.sequence_player_protocol = 1
        with patch('expedition33._sequence_endpoint.current_owned_context') as context:
            with self.assertRaisesRegex(RuntimeError, 'frame-time'):
                self.sequence.prepare_completion()
        context.assert_not_called()

    def test_completion_rechecks_context_after_timing_calls(self):
        self.sequence.play()
        self.sequence._endpoint.observe(context=self.context, current_time=frame(1),
            end_time=frame(240), playing=True, paused=False)
        self.sequence._call = lambda name: {'GetCurrentTime':frame(239, MAX_SUBFRAME), 'GetEndTime':frame(240),
                                           'IsPlaying':False, 'IsPaused':False}[name]
        replacement = self.context[:2] + ((123,5,7,0x30000),)
        with patch('expedition33._sequence_endpoint.current_owned_context', side_effect=(self.context,replacement)):
            with self.assertRaisesRegex(RuntimeError, 'changed during'):
                self.sequence.completion()
        self.assertEqual(self.sequence._endpoint.state, 'unknown')

    def test_preparation_discards_pre_factory_metadata_but_keeps_owned_identities(self):
        sequence=self.sequence
        sequence._endpoint=None
        sequence.scope.pid=123
        transport=sequence.scope._session._transport
        transport.frame_time_values_protocol=transport.sequence_player_protocol=1
        sequence.player=SimpleNamespace(index=5,serial=7,address=0x30000)
        sequence.actor=SimpleNamespace(index=6,serial=8,address=0x40000)
        stale=Mock();stale.with_observations.side_effect=RuntimeError('stale metadata')
        fresh=Mock();combined=Mock();fresh.with_observations.return_value=combined
        sequence.catalog=stale;sequence.planner=Mock()
        sequence._call=lambda name:frame(240) if name=='GetEndTime' else False
        sequence.completion=Mock(return_value={'state':'ready'})
        with patch('expedition33._sequence_endpoint.current_owned_context',return_value=self.context),\
             patch('expedition33.sequences.capture_matching',return_value=fresh),\
             patch('expedition33.sequences.capture_selected',return_value='owned') as selected:
            sequence.prepare_completion()
        stale.with_observations.assert_not_called()
        sequence.planner.refresh_from.assert_called_once_with(combined)
        selected.assert_called_once_with(123,((5,7,0x30000),(6,8,0x40000)))
        sequence.completion.assert_not_called()
        self.assertEqual(sequence._endpoint.state,'ready')

    def test_preparation_checks_idle_and_same_context_without_polling_unstarted_playback(self):
        sequence=self.sequence;sequence._endpoint=None;sequence.scope.pid=123
        sequence.scope._session._transport.frame_time_values_protocol=1
        sequence.scope._session._transport.sequence_player_protocol=1
        sequence.player=SimpleNamespace(index=5,serial=7,address=0x30000)
        sequence.actor=SimpleNamespace(index=6,serial=8,address=0x40000)
        sequence.planner=Mock();sequence._call=Mock(side_effect=[False,False,frame(240)])
        fresh=Mock();fresh.with_observations.return_value=Mock()
        with patch('expedition33._sequence_endpoint.current_owned_context',side_effect=[self.context,self.context]) as context,patch('expedition33.sequences.capture_matching',return_value=fresh),patch('expedition33.sequences.capture_selected'):
            result=sequence.prepare_completion()
        self.assertEqual([c.args[0] for c in sequence._call.call_args_list],['IsPlaying','IsPaused','GetEndTime'])
        self.assertEqual(context.call_count,2)
        self.assertEqual(result,dict(state='ready',endpoint_observed=False,on_finished_observed=False,seen_playing=False))

    def test_factory_continuation_uses_one_post_factory_scan_and_keeps_context_brackets(self):
        sequence=self.sequence;sequence._endpoint=None;sequence.scope.pid=123
        sequence.scope._session._transport.frame_time_values_protocol=1
        sequence.scope._session._transport.sequence_player_protocol=1
        sequence.planner=Mock();sequence._call=Mock(side_effect=[False,False,frame(240)])
        fresh=Mock();combined=Mock();fresh.with_observations.return_value=combined
        with patch('expedition33._sequence_endpoint.current_owned_context',side_effect=[self.context,self.context]) as context,\
             patch('expedition33.sequences.capture_matching',return_value=fresh) as capture,\
             patch('expedition33.sequences.capture_selected') as selected:
            self.assertIs(sequence._finish_build('factory outputs',None,True),sequence)
        self.assertEqual(capture.call_count,1);selected.assert_not_called()
        fresh.with_observations.assert_called_once_with('factory outputs')
        self.assertIn('QualifiedFrameTime',capture.call_args.kwargs['names'])
        self.assertIn('GetEndTime',capture.call_args.kwargs['names'])
        sequence.planner.refresh_from.assert_called_once_with(combined)
        self.assertEqual(context.call_count,2);self.assertEqual(sequence._endpoint.state,'ready')
        self.assertEqual([c.args[0] for c in sequence._call.call_args_list],['IsPlaying','IsPaused','GetEndTime'])

    def test_integrated_construction_rejects_timing_capability_before_loading_assets(self):
        sequence=self.sequence;sequence._endpoint=None
        with patch('expedition33.sequences.load_asset') as load:
            with self.assertRaisesRegex(RuntimeError,'frame-time'):sequence.build(object(),'/Game/Test',completion=True)
            with self.assertRaisesRegex(ValueError,'boolean'):sequence.build(object(),'/Game/Test',completion=1)
        load.assert_not_called()

    def test_endpoint_sample_does_not_pair_running_cursor_with_later_stopped_state(self):
        self.sequence.play()
        self.sequence._endpoint.seen_playing=True
        calls=[]
        def read(name):
            calls.append(name)
            if name=='IsPlaying':return False
            if name=='IsPaused':return False
            if name=='GetCurrentTime':return frame(239,MAX_SUBFRAME) if 'IsPlaying' in calls else frame(238)
            if name=='GetEndTime':return frame(240)
        self.sequence._call=read
        with patch('expedition33._sequence_endpoint.current_owned_context',return_value=self.context):
            self.assertTrue(self.sequence.completion()['endpoint_observed'])
        self.assertLess(calls.index('IsPlaying'),calls.index('GetCurrentTime'))

    def test_report_explicitly_does_not_claim_delegate_delivery(self):
        self.sequence.play()
        self.sequence._endpoint.observe(context=self.context, current_time=frame(1),
            end_time=frame(240), playing=True, paused=False)
        self.sequence._call = lambda name: {'GetCurrentTime':frame(239, MAX_SUBFRAME), 'GetEndTime':frame(240),
                                           'IsPlaying':False, 'IsPaused':False}[name]
        with patch('expedition33._sequence_endpoint.current_owned_context', return_value=self.context):
            report = self.sequence.completion()
        self.assertTrue(report['endpoint_observed'])
        self.assertFalse(report['on_finished_observed'])
        self.assertAlmostEqual(report['position_seconds'],(239+MAX_SUBFRAME)/24)
        self.assertEqual(report['end_seconds'],10.)


if __name__ == '__main__':
    unittest.main()
