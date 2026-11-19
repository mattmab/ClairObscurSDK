import unittest
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import Mock,patch

from expedition33 import RuntimeQueryError
from expedition33.invocation import Parameter
from expedition33.story_dialogue_start import StoryDialogueStart,validate_plan,interaction_context


def plan():
    return N(function_flags=201457664,entry_rva=0x13937a0,parameter_size=9,return_offset=65535,
        parameters=(Parameter('InteractingWorldCharacter','ObjectProperty',0,8,1,2251868533162644),
                    Parameter('Instant','BoolProperty',8,1,1,2251869606904468,0xff010001)))


class StartTests(unittest.TestCase):
    def setUp(self):
        self.owner=StoryDialogueStart.__new__(StoryDialogueStart)
        self.npc=N(identity=(1,2,0x10000),state='visible',_interaction_enabled=True)
        self.owner.npc=self.npc;self.owner.scope=Mock(pid=10)
        self.owner.save_key='saved-guid';self.owner.visit=(20,2,0x20000)
        self.owner.identity_reader=Mock();self.owner.identity_reader.read.return_value='saved-guid'
        self.owner.identity_reader.close.return_value=True
        self.owner.planner=None;self.owner.call=None;self.owner.attempted=False
        self.owner.acknowledged=False;self.owner.unknown=False;self.owner.closed=False
        self.owner.started_at=None;self.owner.issue=None
        self.call=Mock(_plan=plan());self.call.invoke.return_value=nullcontext()
        self.owner.scope.invocation_planner.return_value.prepare_blueprint.return_value=self.call
        self.pawn=N(index=4,serial=5,address=0x40000)
        self.context=dict(state='idle',catalog=Mock(),npc=self.npc,pawn=self.pawn,controller=(3,4,0x30000))
        self.observe=patch('expedition33.story_dialogue_start.interaction_context',return_value=self.context).start()
        patch('expedition33.catalog.capture_matching',return_value=Mock()).start()
        self.addCleanup(patch.stopall)

    def test_uses_original_event_and_current_controlled_pawn_exactly_once(self):
        self.assertEqual(self.owner.poll(),'requested')
        prepared=self.owner.scope.invocation_planner.return_value.prepare_blueprint
        self.assertEqual(prepared.call_args.kwargs,dict(InteractingWorldCharacter=self.pawn,Instant=False))
        self.assertEqual(self.owner.poll(),'pending')
        self.call.invoke.assert_called_once()
        self.context['state']='owned'
        self.assertEqual(self.owner.poll(),'acknowledged');self.assertTrue(self.owner.close())

    def test_manual_interaction_is_adopted_without_restarting(self):
        self.context['state']='owned'
        self.assertEqual(self.owner.poll(),'acknowledged')
        self.call.invoke.assert_not_called();self.assertFalse(self.owner.attempted)

    def test_other_dialogue_and_hidden_or_unprepared_npc_are_not_started(self):
        self.context['state']='busy';self.assertEqual(self.owner.poll(),'waiting')
        self.context['state']='idle';self.npc._interaction_enabled=False
        self.assertEqual(self.owner.poll(),'waiting')
        self.npc._interaction_enabled=True;self.npc.state='prepared'
        self.assertEqual(self.owner.poll(),'waiting');self.call.invoke.assert_not_called()

    def test_wrong_save_is_rejected_before_dispatch(self):
        self.owner.identity_reader.read.return_value='different-save'
        with self.assertRaisesRegex(RuntimeQueryError,'save identity'):self.owner.poll()
        self.call.invoke.assert_not_called()

    def test_pawn_change_during_preparation_defers_without_dispatch(self):
        fresh=dict(self.context,pawn=N(index=8,serial=1,address=0x80000))
        self.observe.side_effect=[self.context,fresh]
        self.assertEqual(self.owner.poll(),'waiting');self.call.invoke.assert_not_called()
        self.assertFalse(self.owner.attempted)

    def test_unknown_dispatch_retained_without_replay_and_can_observe_ack(self):
        self.call.invoke.side_effect=RuntimeQueryError('transport lost acknowledgement')
        with self.assertRaises(RuntimeQueryError):self.owner.poll()
        self.assertTrue(self.owner.unknown);self.assertFalse(self.owner.close())
        self.assertEqual(self.owner.poll(),'pending');self.call.invoke.assert_called_once()
        self.context['state']='owned';self.assertEqual(self.owner.poll(),'acknowledged')
        self.assertFalse(self.owner.unknown);self.assertTrue(self.owner.close())

    def test_timeout_reports_investigation_never_retries_or_guesses_completion(self):
        with patch('expedition33.story_dialogue_start.time.monotonic',return_value=10):self.owner.poll()
        with patch('expedition33.story_dialogue_start.time.monotonic',return_value=12.1):
            self.assertEqual(self.owner.poll(),'pending')
        self.assertIn('2 seconds',self.owner.issue);self.assertFalse(self.owner.acknowledged)
        self.call.invoke.assert_called_once();self.assertFalse(self.owner.close())
        self.assertTrue(self.owner.close(world_retired=True))

    def test_schema_drift_rejected_before_mutation(self):
        self.call._plan.parameters=(self.call._plan.parameters[0],replace(self.call._plan.parameters[1],offset=7))
        with self.assertRaisesRegex(RuntimeQueryError,'schema'):self.owner.poll()
        self.call.invoke.assert_not_called();self.assertFalse(self.owner.attempted)

    def test_exact_audited_event_abi(self):
        validate_plan(plan())
        for key,value in (('function_flags',0),('entry_rva',0x13937b0),('parameter_size',8),('return_offset',0)):
            changed=plan();setattr(changed,key,value)
            with self.assertRaises(RuntimeQueryError):validate_plan(changed)


class ContextTests(unittest.TestCase):
    def setUp(self):
        from expedition33.cinematics.blueprint_actor import STORY_NPC
        self.scope=N(pid=99);self.visit=(7,2,0x70000);self.controller=(8,3,0x80000)
        self.npc=N(index=1,serial=1,address=0x10000,class_name=STORY_NPC.rsplit('.',1)[-1],object_flags=0)
        self.pawn=N(index=2,serial=2,address=0x20000,object_flags=0)
        self.world=N(index=7,serial=2,address=0x70000,class_name='World')
        self.system=N(index=9,serial=2,address=0x90000,class_name='BP_DialogueSystemComponent_C',outer_index=8,outer_serial=3,object_flags=0)
        self.dialogue=N(index=10,serial=1,address=0xa0000)
        self.catalog=Mock(by_index={1:self.npc,8:N(index=8,object_flags=0)})
        self.catalog.outer_chain.return_value=[self.world]
        self.anchor=Mock();self.anchor.context.return_value={'world':(99,*self.visit),'controller':(99,*self.controller)}
        patch('expedition33.cinematics.controller_anchor.for_scope',return_value=self.anchor).start()
        self.systems=N(objects=[self.system]);patch('expedition33.catalog.capture_matching',return_value=self.systems).start()
        self.values=patch('expedition33.values.capture_selected_values').start()
        self.addCleanup(patch.stopall)

    def readings(self,*,talking=False,dialogue=None,active=None):
        def value(**fields):
            return N(types={(1,k):'ObjectProperty' for k in fields},errors={},truncated=False,values={(1,k):v for k,v in fields.items()})
        self.values.side_effect=[(self.catalog,{8:value(Pawn=self.pawn),1:value(IsInDialog=talking,SpawnedDialog=dialogue)}),
                                 (self.catalog,{8:value(BP_DialogueSystemComponent=self.system)}),
                                 (Mock(),{9:value(ActiveDialogue=active)})]

    def read(self):return interaction_context(self.scope,(1,1,0x10000),self.visit)

    def test_local_controller_ownership_and_world_checked(self):
        self.readings();result=self.read()
        self.assertEqual(result['state'],'idle');self.assertIs(result['pawn'],self.pawn)
        self.assertEqual(result['controller'],self.controller)

    def test_other_world_rejected_before_npc_or_pawn_reads(self):
        self.anchor.context.return_value['world']=(99,7,99,0x70000)
        with self.assertRaisesRegex(RuntimeQueryError,'world visit'):self.read()
        self.values.assert_not_called()

    def test_different_controller_system_is_never_selected(self):
        self.readings();self.system.outer_serial=4
        with self.assertRaisesRegex(RuntimeQueryError,'dialogue component differs'):self.read()

    def test_only_this_npcs_active_dialogue_is_adopted(self):
        self.readings(talking=True,dialogue=self.dialogue,active=self.dialogue)
        self.assertEqual(self.read()['state'],'owned')
        self.readings(talking=False,active=self.dialogue)
        self.assertEqual(self.read()['state'],'busy')

    def test_foreign_carrier_class_rejected(self):
        self.readings();self.npc.class_name='BP_Unrelated_C'
        with self.assertRaisesRegex(RuntimeQueryError,'owned story NPC'):self.read()


if __name__=='__main__':unittest.main()
