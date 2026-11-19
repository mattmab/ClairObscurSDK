import importlib
import unittest
import test_story_runtime as fixtures
WORLD=fixtures.WORLD
NativeFlow=importlib.import_module('story_packs_test.native_flow').NativeFlow

class Driver:
    def __init__(self):self.serial=0;self.calls=[];self.event=None;self.ended=0
    def available(self):return True
    def start_lines(self,speaker,lines):
        self.serial+=1;self.calls.append(('lines',speaker,lines));return self.serial
    def start_choices(self,choices):
        self.serial+=1;self.calls.append(('choices',choices));return self.serial
    def completion(self,identity):
        event=self.event;self.event=None;return event
    def end(self):self.ended+=1
    def retire(self):return True

class NativeFlowTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp
    def test_authoring_holds_completion_and_redisplay_does_not_apply_flags(self):
        import copy
        from unittest.mock import Mock
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver)
        flow.interact([10,20,30]);flow.editing=True
        driver.event=dict(presentation=1,kind='lines')
        self.assertFalse(flow.poll());self.assertIsNotNone(driver.event)
        before=self.state.get(self.key)
        document=copy.deepcopy(self.runtime.document)
        document['dialogues']['first-meeting']['nodes']['welcome']['text']='Edited live'
        driver.replace_presentation=Mock(return_value=7)
        flow.refresh_authored(document,'first-meeting')
        self.assertEqual(flow.presentation,7);self.assertEqual(flow.view['text'],'Edited live')
        self.assertEqual(self.state.get(self.key),before)
        self.assertEqual(flow.runtime.conversation.view()['text'],'Edited live')
        flow.editing=False
        with self.assertRaisesRegex(ValueError,'different native'):flow.poll()

    def test_uncertain_authoring_redisplay_stops_without_replaying(self):
        from unittest.mock import Mock
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver)
        flow.interact([10,20,30]);flow.editing=True
        driver.replace_presentation=Mock(side_effect=RuntimeError('uncertain'))
        with self.assertRaisesRegex(RuntimeError,'uncertain'):flow.refresh_authored(self.runtime.document,'first-meeting')
        flow.editing=False
        self.assertFalse(flow.poll());self.assertEqual(flow.stage,'failed')
    def test_lines_then_original_choices_then_following_line_and_native_end(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver)
        self.assertTrue(flow.interact([10,20,30]));self.assertEqual(flow.stage,'lines');self.assertEqual(driver.calls[0][1],'boy')
        driver.event=dict(presentation=1,kind='lines');self.assertTrue(flow.poll())
        self.assertEqual(driver.calls[-1],('choices',('Tell me about this place.','I will come back later.')))
        driver.event=dict(presentation=2,kind='choices',index=0);flow.poll()
        self.assertEqual(flow.stage,'lines');self.assertTrue(self.state.get(self.key)['flags']['heard-story'])
        driver.event=dict(presentation=3,kind='lines');flow.poll()
        self.assertEqual(driver.ended,1);self.assertIsNone(flow.stage)
    def test_old_completion_cannot_advance_a_new_presentation(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30])
        driver.event=dict(presentation=999,kind='lines')
        with self.assertRaisesRegex(ValueError,'different native'):flow.poll()
        self.assertEqual(flow.stage,'lines');self.assertEqual(len(driver.calls),1)
    def test_invalid_choice_index_is_not_replayed_or_mapped_to_a_different_response(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30])
        driver.event=dict(presentation=1,kind='lines');flow.poll()
        driver.event=dict(presentation=2,kind='choices',index=True)
        with self.assertRaises(ValueError):flow.poll()
        self.assertEqual(flow.stage,'failed');self.assertFalse(flow.poll());self.assertNotIn('heard-story',self.state.get(self.key)['flags'])
    def test_travel_dismisses_owned_dialogue_and_prevents_old_callbacks(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);driver=Driver();flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30])
        self.assertTrue(flow.retire());driver.event=dict(presentation=1,kind='lines')
        self.assertFalse(flow.poll());self.assertIsNone(self.runtime.conversation)

    def test_all_conditional_responses_hidden_end_after_line_without_hanging(self):
        for choice in self.runtime.document['dialogues']['first-meeting']['nodes']['welcome']['choices']:
            choice['requires']={'unavailable':True}
        self.runtime.reconcile(WORLD,(1,),ready=True)
        driver=Driver();flow=NativeFlow(self.runtime,driver)
        self.assertTrue(flow.interact([10,20,30]))
        self.assertEqual(flow.view['choices'],())
        driver.event=dict(presentation=1,kind='lines')
        self.assertTrue(flow.poll())
        self.assertIsNone(flow.stage)
        self.assertIsNone(self.runtime.conversation)
        self.assertEqual(driver.ended,1)
        self.assertEqual(len(driver.calls),1)
        self.assertNotIn('heard-story',self.state.get(self.key)['flags'])
