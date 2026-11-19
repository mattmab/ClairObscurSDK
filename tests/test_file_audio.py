import tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
from contextlib import contextmanager,nullcontext
from types import SimpleNamespace as N
from expedition33.file_audio import OwnedFileAudio,wav_file,MEDIA,SYNTH

class FileAudioTests(unittest.TestCase):
    def flags(self):
        a=self.owner();a.player=N(index=1,serial=11,address=101);a.component=N(index=2,serial=12,address=102)
        a.scope=N(pid=7,assign_scalar=Mock())
        def values(**kw):return N(types={(0,k):'BoolProperty' for k in kw},values={(0,k):v for k,v in kw.items()},errors={},truncated=set())
        rows={1:values(NativeAudioOut=True,PlayOnOpen=False,Loop=True),
              2:values(bAllowSpatialization=True,bStopWhenOwnerDestroyed=False,bAutoDestroy=True,bIsUISound=True)}
        return a,rows
    def test_audio_defaults_are_one_fresh_batch_with_per_field_native_compare_and_set(self):
        a,rows=self.flags();catalog=object()
        with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)) as read:
            a._prepare_flags()
        read.assert_called_once();self.assertEqual(read.call_args.args,(7,((1,11,101),(2,12,102))))
        self.assertEqual(a.scope.assign_scalar.call_count,7)
        for call in a.scope.assign_scalar.call_args_list:
            self.assertIs(call.kwargs['catalog'],catalog);self.assertTrue(call.kwargs['allow_mutation'])
            self.assertIs(call.kwargs['expected'],not call.args[2])
        self.assertFalse(a.unknown)
    def test_audio_partial_read_never_attempts_any_assignment(self):
        a,rows=self.flags();rows[2].truncated.add((0,'bIsUISound'))
        with patch('expedition33.values.capture_selected_values',return_value=(object(),rows)):
            with self.assertRaisesRegex(RuntimeError,'incomplete'):a._prepare_flags()
        a.scope.assign_scalar.assert_not_called();self.assertFalse(a.unknown)
    def test_audio_stale_cas_stops_remaining_assignments_without_replay(self):
        from expedition33.invocation import InvocationError
        for outcome,unknown in (('not_dispatched',False),('unknown',True)):
            a,rows=self.flags();a.scope.assign_scalar.side_effect=(None,InvocationError('CAS changed',outcome=outcome))
            with patch('expedition33.values.capture_selected_values',return_value=(object(),rows)):
                with self.assertRaisesRegex(InvocationError,'CAS changed'):a._prepare_flags()
            self.assertEqual(a.scope.assign_scalar.call_count,2);self.assertEqual(a.unknown,unknown)
    def test_owned_audio_dispatch_uses_its_prepared_call_and_preserves_unknown_result(self):
        a=self.owner();call=Mock();a._prepare_call=Mock(return_value=call)
        result=object();call.invoke.return_value=result
        self.assertIs(a._call('owned synth',SYNTH+'Start'),result)
        a._prepare_call.assert_called_once_with('owned synth',SYNTH+'Start')
        self.assertFalse(a.unknown)
        call.invoke.side_effect=RuntimeError('dispatch outcome unknown')
        with self.assertRaisesRegex(RuntimeError,'outcome unknown'):a._call('owned synth',SYNTH+'Start')
        self.assertTrue(a.unknown)

    def test_first_line_preflight_plans_without_opening_or_playing_media(self):
        a=self.owner()
        a.player=N(index=1,serial=2,address=100)
        a.component=N(index=2,serial=2,address=200)
        a.source=N(index=3,serial=2,address=300)
        functions={}
        catalog=Mock()
        catalog.by_index={obj.index:obj for obj in (a.player,a.component,a.source)}
        def function(path):
            if path not in functions:
                i=len(functions)+10;functions[path]=N(index=i,serial=2,address=i*100)
            return functions[path]
        catalog.find_path.side_effect=function
        catalog.with_observations.return_value=catalog
        calls=[]
        planner=Mock()
        def prepare(obj,fn,**arguments):
            result=Mock();calls.append(result);return result
        planner.prepare.side_effect=prepare
        a.scope=N(pid=1,invocation_planner=Mock(return_value=planner))
        with patch('expedition33.file_audio.capture_matching',return_value=catalog),\
             patch('expedition33.file_audio.capture_selected',return_value=catalog),\
             patch('expedition33.file_audio.describe_selected',return_value=N(catalog=catalog,descriptors={})):
            steps=a._prepare_playback_calls()
            next(steps) # Metadata discovery yields before the bounded plans.
            self.assertEqual(planner.prepare.call_count,0)
            with self.assertRaises(StopIteration):next(steps)
        a._void.assert_not_called()
        for call in calls:call.invoke.assert_not_called()
        for path,obj in ((MEDIA+'OpenSource',a.player),(SYNTH+'Start',a.component),
                         (MEDIA+'Close',a.player),(MEDIA+'IsReady',a.player)):
            self.assertIn(((obj.index,obj.serial,obj.address),path),a.calls)
        self.assertEqual(planner.prepare.call_count,10)
    def test_background_preparation_advances_one_stage_per_poll(self):
        a=self.owner();a.prepared=False;a._preparation=None
        a.scope=N(pid=1,_session=N(_transport=N(_executable='probe')))
        events=[]
        def stages():
            events.append('carrier');yield
            events.append('decoder');yield
            events.append('ready');a.prepared=True
        a._prepare_steps=stages
        with patch('expedition33.file_audio.shared_operation',return_value=nullcontext()):
            self.assertFalse(a.prepare_step());self.assertEqual(events,['carrier'])
            self.assertFalse(a.prepare_step());self.assertEqual(events,['carrier','decoder'])
            self.assertTrue(a.prepare_step());self.assertEqual(events,['carrier','decoder','ready'])
            self.assertTrue(a.prepare_step());self.assertEqual(len(events),3)
    def owner(self):
        a=OwnedFileAudio.__new__(OwnedFileAudio)
        a.closed=False;a.unknown=False;a.player='owned player';a.component='owned synth'
        a.playing=True;a.paused=False;a.ready=True;a.carrier=Mock();a.planners=[Mock()];a.calls={}
        a._void=Mock();return a
    def test_ordinary_stop_closes_decoder_and_stops_registered_synth(self):
        a=self.owner();self.assertTrue(a.stop())
        self.assertEqual([c.args for c in a._void.call_args_list],[('owned player',MEDIA+'Close'),('owned synth',SYNTH+'Stop')])
        self.assertFalse(a.playing);self.assertFalse(a.paused)
    def test_retirement_uses_native_actor_destruction_without_old_component_calls(self):
        a=self.owner();self.assertTrue(a.close(world_retired=True))
        a._void.assert_not_called();a.carrier.retire_world.assert_called_once();a.carrier.close.assert_not_called()
        self.assertTrue(a.closed)
    def test_deferred_native_destruction_preserves_audio_owner(self):
        a=self.owner();a.carrier.retire_world.return_value=False
        self.assertFalse(a.close(world_retired=True));self.assertFalse(a.closed)
        a.planners[0].close.assert_not_called()
    def test_unknown_outcome_is_never_replayed(self):
        a=self.owner();a.unknown=True
        self.assertFalse(a.stop());self.assertFalse(a.close());self.assertFalse(a.close(world_retired=True))
        a._void.assert_not_called();a.carrier.close.assert_not_called()
    def test_opening_does_not_issue_pause_until_decoder_ready(self):
        a=self.owner();a.ready=False;a._call=Mock();a.pause(True);a._call.assert_not_called()
    def test_decoder_timeout_closes_only_its_owned_stream(self):
        a=self.owner();a.started=0.;a.next_poll=0.;a.ready=False
        @contextmanager
        def call(*args,**kw):yield N(return_value=False)
        a._call=call
        with patch('expedition33.file_audio.time.monotonic',return_value=3.):
            with self.assertRaisesRegex(RuntimeError,'2 seconds'):a.poll()
        self.assertFalse(a.playing)
        self.assertEqual(len(a._void.call_args_list),2)
    def test_voice_gain_updates_only_the_owned_synth(self):
        a=self.owner();a.set_volume(2.)
        a._void.assert_called_once_with('owned synth',SYNTH+'SetVolumeMultiplier',VolumeMultiplier=2.)
        self.assertEqual(a.volume,2.)
        for value in (-1,5,float('nan')):
            with self.assertRaises(ValueError):a.set_volume(value)
    def test_normalized_wav_path_and_bounded_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'clip.wav'
            with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE',''));f.writeframes(b'\0'*4800)
            normalized,duration=wav_file(path)
            self.assertNotIn('\\',normalized);self.assertAlmostEqual(duration,.1)
            with wave.open(str(path),'wb') as f:f.setparams((1,1,24000,0,'NONE',''));f.writeframes(b'\0'*10)
            with self.assertRaises(ValueError):wav_file(path)

if __name__=='__main__':unittest.main()
