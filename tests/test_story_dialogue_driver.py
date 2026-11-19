import unittest
from contextlib import nullcontext,contextmanager
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33.story_dialogue import NativeStoryDialogueDriver as Driver

class Call:
    def __init__(self,scope,system,dialogue):
        self.scope=scope;self.system=system;self.dialogue=dialogue;self.unknown=False;self.serial=0;self.ended=0;self.closed=False
    def register_participants(self,npcs):self.registered=tuple(npcs)
    def frame_speaker(self,npc,camera_npc):self.framed=(npc,camera_npc)
    def retire_camera_world(self):return True
    def lines(self,speaker,texts):self.serial+=1;return self.serial
    def choices(self,texts):self.serial+=1;return self.serial
    def end(self):self.ended+=1
    def close(self):self.closed=True;return True

class NativeStoryDriverTests(unittest.TestCase):
    def test_completed_driver_retirement_never_touches_destroyed_participants(self):
        driver=Driver.__new__(Driver);driver.call=None;driver._ended_cleanly=True
        class Destroyed:
            presentation_only=True
            def set_visual_visible(self,value):raise AssertionError('Destroyed participant accessed')
        driver.participants=(Destroyed(),)
        self.assertTrue(driver.retire())
    def test_rejected_camera_keeps_acknowledged_line_and_can_complete(self):
        from expedition33 import RuntimeQueryError
        error=RuntimeQueryError('camera rejected');error.native_error=3910;error.outcome='not_dispatched'
        self.driver.participants=(N(speaker=self.speaker),)
        with patch.object(Call,'frame_speaker',side_effect=error):
            with self.assertLogs('expedition33.story_dialogue',level='WARNING'):
                receipt=self.driver.start_lines('boy',('Already dispatched',))
        self.assertEqual(self.driver.call.serial,1)
        self.assertEqual(self.driver.pending,receipt)
        self.value['complete']=True
        self.assertEqual(self.driver.completion(receipt)['presentation'],receipt)

    def test_unknown_camera_failure_remains_quarantined(self):
        from expedition33 import RuntimeQueryError
        error=RuntimeQueryError('camera unknown');error.native_error=3911;error.outcome='unknown'
        self.driver.participants=(N(speaker=self.speaker),)
        with patch.object(Call,'frame_speaker',side_effect=error):
            with self.assertRaises(RuntimeQueryError):self.driver.start_lines('boy',('Line',))
        self.assertEqual(self.driver.call.serial,1)
        self.assertIsNotNone(self.driver.pending)

    def test_physical_echo_sophie_revealed_and_hidden_with_dialogue_owner(self):
        events=[]
        sophie=N(state='prepared',presentation_only=True,speaker=N(index=20,serial=1,address=0x50000),
            reveal=lambda **kwargs:events.append(('reveal',kwargs)),set_interaction_enabled=lambda value:events.append(('interaction',value)),
            set_visual_visible=lambda value:events.append(('visible',value)))
        self.driver.participants=(sophie,)
        presentation=self.driver.start_lines('boy',('Hello',))
        self.assertEqual(events[:3],[('reveal',{'visual':False}),('interaction',False),('visible',True)])
        self.value['complete']=True;self.driver.completion(presentation)
        self.driver.end()
        self.assertEqual(events[-1],('visible',False))

    def test_first_pose_and_player_hiding_precede_cast_reveal_and_text(self):
        events=[]
        self.driver._prepare_dispatch=lambda:events.append('prepare-hidden')
        self.driver.animate_line=lambda view:events.append('pose')
        self.driver.start_lines=lambda *args:events.append('reveal-camera-text') or 'receipt'
        self.driver.play_audio=lambda audio:None
        self.assertEqual(self.driver.present({'speaker_id':'boy','text':'Hello'}),'receipt')
        self.assertEqual(events,['prepare-hidden','pose','reveal-camera-text'])

    def test_player_role_uses_aligned_private_camera_even_without_standin_visual(self):
        self.driver.speakers['gustave']=self.speaker
        camera=N(speaker=N(index=10,serial=1,address=0x60000),state='visible')
        self.driver.authored_cast=N(standin=camera,begin=lambda:None)
        self.driver.start_lines('gustave',('Hello',))
        self.assertIs(self.driver.call.framed[1],camera)
    def test_carrier_gated_before_presentation_and_remains_gated_after_end(self):
        events=[]
        self.npc.set_interaction_enabled=lambda enabled:events.append(('gate',enabled))
        with patch.object(Call,'lines',side_effect=lambda *a:events.append(('lines',)) or 1):
            presentation=self.driver.start_lines('boy',('Hello',))
        self.assertEqual(events[:2],[('gate',False),('lines',)])
        self.value['complete']=True;self.driver.completion(presentation)
        self.driver.end()
        self.assertNotIn(('gate',True),events)
    def setUp(self):
        cleanup=patch("expedition33._story_dialogue_camera_cleanup.finish",return_value=True)
        self.camera_cleanup=cleanup.start();self.addCleanup(cleanup.stop)
        self.system=N(index=1,serial=2,address=0x10000);self.dialogue=N(index=3,serial=4,address=0x20000)
        self.speaker=N(index=5,serial=6,address=0x30000)
        self.value=dict(system=self.system,dialogue=self.dialogue,active=self.dialogue,complete=False,choice=1)
        self.npc=N(scope=N(pid=123,_session=N(_transport=N(_executable='test-probe'))),identity=(7,8,0x40000),state='visible')
        self.driver=Driver(self.npc,{'boy':self.speaker},observer=lambda scope,npc:self.value)
        patcher=patch('expedition33.story_dialogue.NativeDialogueText',Call);patcher.start();self.addCleanup(patcher.stop)
        reader=patch('expedition33.story_dialogue.shared_operation',side_effect=lambda *a,**k:nullcontext())
        reader.start();self.addCleanup(reader.stop)

    def test_camera_cleanup_retry_does_not_repeat_native_end(self):
        from expedition33 import RuntimeQueryError
        receipt=self.driver.start_lines('boy',('Goodbye',))
        self.value['complete']=True
        self.driver.completion(receipt)
        call=self.driver.call
        self.camera_cleanup.side_effect=[False,True]
        with self.assertRaisesRegex(RuntimeQueryError,'camera restoration is pending'):self.driver.end()
        self.assertEqual(call.ended,1)
        self.driver.end()
        self.assertEqual(call.ended,1)
        self.assertIsNone(self.driver.call)

    def test_line_and_camera_share_one_reader_and_exception_releases_operation(self):
        events=[]
        @contextmanager
        def operation(pid,**kwargs):
            self.assertEqual(pid,123);self.assertEqual(kwargs,{'_executable':'test-probe'})
            events.append('enter')
            try:yield
            finally:events.append('exit')
        def observe(scope,npc):
            self.assertEqual(events,['enter','enter']);return self.value
        self.driver.observer=observe
        self.driver.participants=(N(speaker=self.speaker),)
        def frame(call,*args):
            self.assertEqual(events,['enter','enter','exit']);raise RuntimeError('camera outcome unknown')
        with patch('expedition33.story_dialogue.shared_operation',operation),patch.object(Call,'frame_speaker',frame):
            with self.assertRaisesRegex(RuntimeError,'camera outcome unknown'):
                self.driver.start_lines('boy',('Hello',))
        self.assertEqual(events,['enter','enter','exit','exit'])
        self.assertIsNotNone(self.driver.call)
        self.assertIsNotNone(self.driver.pending)
    def test_original_line_refresh_cannot_override_speaker_camera(self):
        actor=N(speaker=self.speaker);self.driver.participants=(actor,)
        first=self.driver.start_lines('boy',('Hello',));call=self.driver.call
        self.value['complete']=True;self.driver.completion(first)
        order=[]
        lines=call.lines
        call.lines=lambda *args:(order.append('lines'),lines(*args))[1]
        call.frame_speaker=lambda *args:order.append('camera')
        self.driver.start_lines('boy',('Again',))
        self.assertEqual(order,['lines','camera'])
    def test_previous_choice_is_not_completion_and_native_events_are_consumed_once(self):
        self.assertTrue(self.driver.available());presentation=self.driver.start_lines('boy',('Hello',))
        self.assertIsNone(self.driver.completion(presentation))
        self.value['complete']=True;event=self.driver.completion(presentation);self.assertEqual(event['kind'],'lines')
        with self.assertRaises(RuntimeError):self.driver.completion(presentation)
        self.value['complete']=False;presentation=self.driver.start_choices(('Ask','Leave'))
        self.assertIsNone(self.driver.completion(presentation));self.value['complete']=True
        self.assertEqual(self.driver.completion(presentation)['index'],1)
        self.driver.end();self.assertIsNone(self.driver.call)
    def test_foreign_active_dialogue_cannot_be_advanced_or_ended(self):
        presentation=self.driver.start_lines('boy',('Hello',));call=self.driver.call
        self.value['active']=N(index=9,serial=10,address=0x50000)
        with self.assertRaises(RuntimeError):self.driver.completion(presentation)
        self.assertTrue(self.driver.retire());self.assertEqual(call.ended,0);self.assertTrue(call.closed)
    def test_unbound_speaker_does_not_dispatch_or_create_a_dialogue_owner(self):
        with self.assertRaises(ValueError):self.driver.start_lines('not-present',('Hello',))
        self.assertIsNone(self.driver.call)

    def test_missing_cast_ends_owned_empty_dialogue_before_any_story_presentation(self):
        self.driver.cast_resolver=lambda:({},(),'Place Lune on this map')
        self.assertEqual(self.driver.prepare_conversation(),'Place Lune on this map')
        self.assertIsNone(self.driver.call);self.assertIsNone(self.driver.pending)

    def test_cast_is_resolved_at_interaction_instead_of_using_stale_spawn_time_bindings(self):
        other=N(index=8,serial=9,address=0x60000)
        self.driver.cast_resolver=lambda:({'boy':other},('fresh actor',),None)
        self.assertIsNone(self.driver.prepare_conversation())
        self.assertEqual(self.driver.speakers,{'boy':other})
        self.assertEqual(self.driver.participants,('fresh actor',))

    def test_missing_cast_cannot_dismiss_foreign_dialogue(self):
        self.driver.cast_resolver=lambda:({},(),'Missing cast')
        self.value['active']=N(index=9,serial=10,address=0x50000)
        with self.assertRaisesRegex(RuntimeError,'no longer active'):self.driver.prepare_conversation()
        self.assertIsNone(self.driver.call)

    def test_unknown_rejection_end_keeps_owner_for_cleanup_and_does_not_repeat(self):
        self.driver.cast_resolver=lambda:({},(),'Missing cast')
        def unknown(call):call.unknown=True;raise RuntimeError('End outcome unknown')
        with patch.object(Call,'end',unknown):
            with self.assertRaisesRegex(RuntimeError,'unknown'):self.driver.prepare_conversation()
        self.assertIsNotNone(self.driver.call);self.assertFalse(self.driver.retire())
        with self.assertRaisesRegex(RuntimeError,'after presentation'):self.driver.prepare_conversation()
    def test_pending_input_cannot_be_replaced_and_invalid_native_response_is_rejected(self):
        presentation=self.driver.start_choices(('Ask','Leave'))
        with self.assertRaises(RuntimeError):self.driver.start_lines('boy',('Hello',))
        self.value.update(complete=True,choice=99)
        with self.assertRaises(RuntimeError):self.driver.completion(presentation)
        self.assertEqual(self.driver.pending,presentation)

    def test_multiple_participants_register_on_first_presentation_only(self):
        self.driver.participants=(N(speaker=self.speaker),N(speaker=N(index=8,serial=9,address=0x60000)))
        first=self.driver.start_lines('boy',('Hello',))
        call=self.driver.call;self.assertEqual(call.registered,self.driver.participants)
        self.value['complete']=True;self.driver.completion(first)
        call.register_participants=lambda *args:self.fail('Participants registered twice')
        self.driver.start_lines('boy',('Again',))

    def test_world_retirement_releases_participant_leases_without_ending_replacement_dialogue(self):
        self.driver.participants=(N(speaker=self.speaker),N(speaker=N(index=8,serial=9,address=0x60000)))
        self.driver.start_lines('boy',('Hello',));call=self.driver.call
        self.value['active']=N(index=9,serial=10,address=0x50000)
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=False) as close:
            self.assertFalse(self.driver.retire_world())
            close.assert_called_once_with(call.scope)
        self.assertIs(self.driver.call,call)
        self.assertIsNotNone(self.driver.pending)
        self.assertEqual(call.ended,0)
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):
            self.assertTrue(self.driver.retire_world())
        self.assertTrue(call.closed);self.assertIsNone(self.driver.call)
        self.assertIsNone(self.driver.pending);self.assertEqual(call.ended,0)

    def test_unknown_participant_dispatch_keeps_ownership_on_world_retirement(self):
        self.driver.start_lines('boy',('Hello',));call=self.driver.call;call.unknown=True
        with patch('expedition33._retired_tracking.close_lease_only_scope') as close:
            self.assertFalse(self.driver.retire_world());close.assert_not_called()
        self.assertIs(self.driver.call,call);self.assertIsNotNone(self.driver.pending)

    def test_camera_retirement_must_acknowledge_before_any_dialogue_scope_release(self):
        self.driver.start_lines('boy',('Hello',));call=self.driver.call
        call.retire_camera_world=lambda:False
        with patch('expedition33._retired_tracking.close_lease_only_scope') as close:
            self.assertFalse(self.driver.retire_world());close.assert_not_called()
        self.assertIs(self.driver.call,call);self.assertIsNotNone(self.driver.pending)
        self.assertFalse(call.closed);self.assertEqual(call.ended,0)

    def test_camera_failure_retains_the_already_dispatched_presentation(self):
        lune=N(index=8,serial=9,address=0x60000)
        boy_actor=N(speaker=self.speaker);lune_actor=N(speaker=lune)
        self.driver.speakers['lune']=lune;self.driver.participants=(boy_actor,lune_actor)
        first=self.driver.start_lines('boy',('Hello',));call=self.driver.call
        self.assertEqual(call.framed,(self.npc,boy_actor))
        self.value['complete']=True;self.driver.completion(first)
        def unknown(*args):raise RuntimeError('Camera outcome unknown')
        call.frame_speaker=unknown
        with self.assertRaisesRegex(RuntimeError,'Camera outcome unknown'):
            self.driver.start_lines('lune',('Answer',))
        self.assertIsNotNone(self.driver.pending);self.assertIs(self.driver.call,call)

