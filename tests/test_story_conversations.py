import copy
import importlib
import unittest
import test_story_runtime as fixtures
WORLD=fixtures.WORLD
from test_story_native_flow import Driver

routing=importlib.import_module('story_packs_test.conversations')

class AvailableDriver(Driver):
    def __init__(self,ready=False):
        super().__init__();self.ready=ready;self.hold=False;self.retired_world=False
    def available(self):return self.ready
    def retire(self):return not self.hold
    def retire_world(self):self.retired_world=True;return not self.hold

class ConversationRoutingTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp

    def prepare(self):
        second=copy.deepcopy(self.runtime.document['placements'][0]);second['id']='boy-second'
        self.runtime.document['placements'].append(second)
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.drivers={key:AvailableDriver(key=='boy-second') for key in self.runtime.actors}
        return routing.Conversations(self.runtime,lambda key,npc:self.drivers[key])

    def test_native_selected_actor_wins_even_when_placements_overlap(self):
        owner=self.prepare();self.assertTrue(owner.poll())
        self.assertEqual(owner.active,'boy-second')
        self.assertEqual(self.runtime.speaker,'boy-second')
        self.assertFalse(self.drivers['boy-here'].calls)
        self.assertEqual(self.drivers['boy-second'].calls[0][0],'lines')

    def test_unavailable_cast_does_not_change_story_flags_or_block_other_conversations(self):
        owner=self.prepare();driver=self.drivers['boy-second']
        driver.prepare_conversation=lambda:'Place Lune on this map'
        self.assertTrue(owner.poll());self.assertIsNone(owner.flow)
        self.assertIsNone(owner.error);self.assertFalse(driver.calls)
        self.assertFalse(self.runtime.native_active)
        self.assertNotIn('met-boy',self.state.get(self.key)['flags'])
        self.assertIn('Lune',owner.warnings['boy-second'])
        driver.prepare_conversation=lambda:None
        self.assertTrue(owner.poll());self.assertFalse(owner.warnings)
        self.assertEqual(owner.active,'boy-second')

    def test_other_speaker_hidden_by_line_flag_survives_until_native_end(self):
        owner=self.prepare()
        self.runtime.document['placements'][0]['requires']={'met-boy':False}
        owner.poll();self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertIn('boy-here',self.runtime.actors)
        self.assertEqual(self.runtime.native_active,{'boy-here','boy-second'})
        driver=self.drivers['boy-second']
        driver.event=dict(presentation=1,kind='lines');owner.poll()
        driver.event=dict(presentation=2,kind='choices',index=1);owner.poll()
        self.assertFalse(self.runtime.native_active)
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertNotIn('boy-here',self.runtime.actors)
        self.assertIn('boy-second',self.runtime.actors)

    def test_unknown_native_end_keeps_other_speaker_even_when_flags_hide_it(self):
        owner=self.prepare()
        self.runtime.document['placements'][0]['requires']={'met-boy':False}
        owner.poll();driver=self.drivers['boy-second']
        driver.event=dict(presentation=1,kind='lines');owner.poll()
        def uncertain():raise RuntimeError('End outcome unknown')
        driver.end=uncertain
        driver.event=dict(presentation=2,kind='choices',index=1);owner.poll()
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertIn('boy-here',self.runtime.actors)
        self.assertIn('boy-here',self.runtime.native_active)
        driver.hold=True;self.assertFalse(owner.retire())
        self.assertIn('boy-here',self.runtime.native_active)
        driver.hold=False;self.assertTrue(owner.retire())
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertNotIn('boy-here',self.runtime.actors)

    def test_unknown_dispatch_does_not_replay_each_poll(self):
        owner=self.prepare()
        def failed(*args):raise RuntimeError('Uncertain native dispatch')
        self.drivers['boy-second'].start_lines=failed
        self.assertFalse(owner.poll());self.assertIn('Uncertain',owner.error)
        self.assertFalse(owner.poll());self.assertEqual(owner.flow.stage,'failed')

    def test_retirement_holds_owners_until_native_cleanup_acknowledges(self):
        owner=self.prepare();owner.poll();driver=self.drivers['boy-second'];driver.hold=True
        self.assertFalse(owner.retire(world_retired=True))
        self.assertIn('boy-second',owner.drivers);self.assertTrue(driver.retired_world)
        driver.hold=False;self.assertTrue(owner.retire(world_retired=True))
        self.assertFalse(owner.drivers);self.assertIsNone(self.runtime.conversation)

    def test_ineligible_or_missing_placement_cannot_start_native_dialogue(self):
        self.prepare();self.runtime.errors['boy-second']='partial spawn'
        with self.assertRaises(ValueError):self.runtime.interact_placement('boy-second')
        with self.assertRaises(ValueError):self.runtime.interact_placement('missing')

    def flag_removes_active(self):
        self.runtime.document['placements'][0]['requires']={'met-boy':False}
        self.runtime.reconcile(WORLD,(1,),ready=True)
        driver=AvailableDriver(True)
        owner=routing.Conversations(self.runtime,lambda key,npc:driver)
        owner.poll();self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertIn('boy-here',self.runtime.actors)
        driver.event=dict(presentation=1,kind='lines');owner.poll()
        return owner,driver

    def test_flag_hides_actor_only_after_native_end_then_prunes_driver(self):
        owner,driver=self.flag_removes_active()
        driver.event=dict(presentation=2,kind='choices',index=1);owner.poll()
        self.assertEqual(driver.ended,1);self.assertFalse(self.runtime.native_active)
        self.runtime.reconcile(WORLD,(1,),ready=True);owner.poll()
        self.assertFalse(self.runtime.actors);self.assertFalse(owner.drivers)

    def test_unknown_native_end_keeps_carrier_until_explicit_cleanup(self):
        owner,driver=self.flag_removes_active()
        def uncertain():raise RuntimeError('End outcome unknown')
        driver.end=uncertain
        driver.event=dict(presentation=2,kind='choices',index=1);owner.poll()
        self.assertIsNone(self.runtime.conversation)
        self.assertIn('unknown',owner.error)
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertIn('boy-here',self.runtime.actors)
        driver.hold=True;self.assertFalse(owner.retire())
        self.assertIn('boy-here',self.runtime.native_active)
        driver.hold=False;self.assertTrue(owner.retire())
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertFalse(self.runtime.actors)


class SpeakerBindingTests(unittest.TestCase):
    def test_bindings_use_each_characters_own_actor_and_reject_ambiguous_others(self):
        from types import SimpleNamespace as N
        from story_packs_test.conversations import speaker_bindings
        runtime=N(document=dict(characters={'boy':{},'lune':{},'unplaced':{}},placements=[
            dict(id='boy-one',character='boy'),dict(id='boy-two',character='boy'),dict(id='lune',character='lune')]),
            actors={'boy-one':N(speaker='first'),'boy-two':N(speaker='second'),'lune':N(speaker='lune')},errors={})
        self.assertEqual(speaker_bindings(runtime,'boy-two'),{'boy':'second','lune':'lune'})
        self.assertEqual(speaker_bindings(runtime,'lune'),{'lune':'lune'})
        runtime.errors={'boy-one':'failed'}
        self.assertEqual(speaker_bindings(runtime,'lune'),{'boy':'second','lune':'lune'})


class ConversationParticipantSelectionTests(unittest.TestCase):
    def test_missing_reachable_cast_has_named_guidance_and_ignores_unreachable_nodes(self):
        from types import SimpleNamespace as N
        from story_packs_test.conversations import conversation_cast
        boy=N(speaker='boy')
        runtime=N(document=dict(characters={'boy':dict(name='Faceless Boy'),'lune':dict(name='Lune'),'sciel':dict(name='Sciel')},
            placements=[dict(id='boy',character='boy',dialogue='talk')],dialogues={'talk':dict(entry='one',nodes={
                'one':dict(speaker='boy',next='two',choices=[]),
                'two':dict(speaker='lune',next=None,choices=[dict(next='one')]),
                'unused':dict(speaker='sciel',next=None,choices=[])})}),actors={'boy':boy},errors={},key='save',state=N(get=lambda key:{'flags':{}}))
        bindings,participants,issue=conversation_cast(runtime,'boy')
        self.assertEqual(bindings,{'boy':'boy'});self.assertEqual(participants,(boy,))
        self.assertIn('Lune',issue);self.assertNotIn('Sciel',issue)

    def test_only_reachable_characters_and_interacting_owner_join_conversation(self):
        from types import SimpleNamespace as N
        from story_packs_test.conversations import conversation_participants
        boy=N(speaker='boy');lune=N(speaker='lune');sciel=N(speaker='sciel')
        runtime=N(document=dict(characters={'boy':{},'lune':{},'sciel':{}},placements=[
            dict(id='boy',character='boy',dialogue='talk'),dict(id='lune',character='lune'),dict(id='sciel',character='sciel')],
            dialogues={'talk':dict(entry='one',nodes={
                'one':dict(speaker='boy',next='two',choices=[]),
                'two':dict(speaker='lune',next=None,choices=[dict(next='one')]),
                'unused':dict(speaker='sciel',next=None,choices=[])})}),
            actors={'boy':boy,'lune':lune,'sciel':sciel},errors={},key='save',state=N(get=lambda key:{'flags':{}}))
        self.assertEqual(conversation_participants(runtime,'boy'),(boy,lune))

    def test_conditionally_unavailable_speaker_does_not_block_native_entry(self):
        case=fixtures.StoryRuntimeTests();case.setUp()
        self.addCleanup(case.doCleanups)
        runtime=case.runtime;document=runtime.document
        document['characters']['lune']=dict(name='Lune',profile='lune')
        nodes=document['dialogues']['first-meeting']['nodes']
        nodes['welcome']['choices'][0]['requires']={'invite-lune':True}
        nodes['story']['speaker']='lune'
        runtime.reconcile(WORLD,(1,),ready=True)
        from types import SimpleNamespace
        runtime.actors['boy-here']=SimpleNamespace(speaker='boy')
        before=copy.deepcopy(case.state.get(case.key))
        self.assertIsNone(routing.conversation_cast(runtime,'boy-here')[2])
        self.assertEqual(case.state.get(case.key),before)
        case.state.update_flags(case.key,{'invite-lune':True})
        self.assertIn('Lune',routing.conversation_cast(runtime,'boy-here')[2])

    def test_cast_follows_line_and_response_effects_through_cycles(self):
        dialogue=dict(entry='first',nodes={
            'first':dict(speaker='boy',set={},next=None,choices=[
                dict(next='unlock',requires={'ready':False},set={}),
                dict(next='last',requires={'ready':True},set={})]),
            'unlock':dict(speaker='boy',set={'ready':True},next='first',choices=[]),
            'last':dict(speaker='lune',set={},next=None,choices=[])})
        flags={}
        self.assertEqual(routing.reachable_speakers(dialogue,flags),{'boy','lune'})
        self.assertEqual(flags,{})
        dialogue['nodes']['unlock']['set']={}
        dialogue['nodes']['first']['choices'][0]['set']={'ready':True}
        self.assertEqual(routing.reachable_speakers(dialogue,flags),{'boy','lune'})
        self.assertEqual(routing.reachable_speakers(dialogue,flags,state_limit=0),{'boy','lune'})
