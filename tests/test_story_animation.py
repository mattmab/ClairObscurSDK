import copy,importlib,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import test_story_packs
import test_story_authoring as authoring_fixtures
from test_story_native_flow import NativeFlow,Driver
import test_story_runtime as fixtures
from test_story_view import StoryView
from expedition33.story_animation import DialogueAnimations,choices
schema=test_story_packs.schema
selection=dict(asset='/Game/Animations/Idle.Idle',target='boy',loop=True,speed=1.)

class AnimationAuthoringTests(unittest.TestCase):
    setUp=authoring_fixtures.StoryAuthoringTests.setUp
    def test_node_and_response_animations_roundtrip_and_clear(self):
        self.draft.animation('first-meeting','welcome',None,selection)
        row=self.draft.document['dialogues']['first-meeting']['nodes']['welcome']
        key=row['choices'][0]['id'];response=dict(selection,target='player',loop=False,speed=.5)
        self.draft.animation('first-meeting','welcome',key,response)
        saved=self.editor.open(self.draft.document['id']).document['dialogues']['first-meeting']['nodes']['welcome']
        self.assertEqual(saved['animation'],selection);self.assertEqual(saved['choices'][0]['animation'],response)
        self.draft.animation('first-meeting','welcome',None,None)
        row=self.draft.document['dialogues']['first-meeting']['nodes']['welcome']
        self.assertNotIn('animation',row);self.assertEqual(row['choices'][0]['animation'],response)
    def test_invalid_animation_settings_do_not_write(self):
        before=self.draft.path.read_bytes()
        for changes in ({'target':'missing'},{'speed':float('nan')},{'loop':1},{'asset':'garbage'}):
            with self.assertRaises(ValueError):self.draft.animation('first-meeting','welcome',None,dict(selection,**changes))
            self.assertEqual(self.draft.path.read_bytes(),before)

class AnimationFlowTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp
    def flow(self):
        row=self.pack['dialogues']['first-meeting']['nodes']['welcome']
        row['animation']=copy.deepcopy(selection);row['choices'][0]['animation']=dict(selection,target='player')
        self.runtime.reconcile(fixtures.WORLD,(1,),ready=True)
        self.runtime.document['dialogues']['first-meeting']['nodes']['welcome'].update(copy.deepcopy(row))
        driver=Driver();driver.animate=Mock();driver.start_response_animation=Mock();driver.response_animation_complete=Mock(return_value=False)
        flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30]);return flow,driver
    def test_response_animation_does_not_delay_following_text_or_flags(self):
        flow,driver=self.flow();driver.animate.assert_called_once_with(selection)
        driver.event=dict(presentation=1,kind='lines');flow.poll()
        driver.start_response_animation.assert_not_called()
        driver.event=dict(presentation=2,kind='choices',index=0);flow.poll()
        self.assertEqual(flow.stage,'lines');driver.response_animation_complete.assert_not_called()
        self.assertTrue(self.state.get(self.key)['flags']['heard-story']);self.assertEqual(flow.stage,'lines')
    def test_response_animation_failure_is_not_replayed(self):
        flow,driver=self.flow();driver.event=dict(presentation=1,kind='lines');flow.poll()
        driver.start_response_animation.side_effect=RuntimeError('stopped')
        driver.event=dict(presentation=2,kind='choices',index=0)
        with self.assertRaisesRegex(RuntimeError,'stopped'):flow.poll()
        self.assertEqual(flow.stage,'failed');self.assertFalse(flow.poll())
        driver.start_response_animation.assert_called_once()
    def test_world_retirement_during_response_animation_cancels_continuation(self):
        flow,driver=self.flow();driver.event=dict(presentation=1,kind='lines');flow.poll()
        driver.event=dict(presentation=2,kind='choices',index=0);flow.poll()
        self.assertTrue(flow.retire());self.assertFalse(flow.poll())
        self.assertTrue(self.state.get(self.key)['flags']['heard-story'])

class AnimationPickerTests(unittest.TestCase):
    def test_graph_picker_selects_independently_and_preserves_content(self):
        pack=test_story_packs.sample();save=Mock()
        model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=save)
        view=StoryView(N(_check=lambda:None),model);view.pack=pack['id'];view.dialogue='first-meeting';view.screen='story_graph'
        frame=view.render();control=next(c for c in frame.controls if c.label.startswith('Animation'))
        frame=view.activate(frame.revision,control.token);self.assertEqual(view.screen,'story_animations');save.assert_not_called()
        view.query='idle';view.page=0;frame=view.render()
        clip=next(c for c in frame.controls if c.enabled and view._commands[c.token][0]=='story_animation_select')
        view.activate(frame.revision,clip.token)
        self.assertEqual(view.screen,'story_graph');args=save.call_args.args
        self.assertEqual(args[:5],(pack['id'],'animation','first-meeting','welcome',None))
        self.assertEqual(args[5]['target'],'boy');self.assertTrue(args[5]['loop'])
    def test_library_filters_skeleton_and_search(self):
        rows=choices('faceless-boy','idle');self.assertTrue(rows)
        self.assertTrue(all('idle' in (r['path']+r['label']).casefold() for r in rows))
        self.assertFalse(choices('unsupported'))
    def test_world_cleanup_never_dispatches_against_retired_components(self):
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=object();owner.records={1:object()};owner.failed=True;owner._call=Mock()
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close(world_retired=True))
        owner._call.assert_not_called()
    def test_uncertain_animation_retains_owner_for_cleanup(self):
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=object();owner.records={1:object()};owner.failed=True;owner._call=Mock()
        self.assertFalse(owner.close());owner._call.assert_not_called();self.assertTrue(owner.records)

class AnimationDispatchTests(unittest.TestCase):
    def objects(self):
        def obj(index,cls):return N(index=index,serial=100+index,address=1000+index,class_index=1,class_name=cls)
        component=obj(1,'SkeletalMeshComponent');mesh=obj(2,'SkeletalMesh');clip=obj(3,'AnimSequence');rig=obj(4,'Skeleton')
        def values(**kwargs):return N(types={(0,k):'ObjectProperty' for k in kwargs},values={(0,k):v for k,v in kwargs.items()},errors={})
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=N(pid=1,_session=N());owner.records={};owner.failed=False;owner._call=Mock();owner.mutated=set()
        reads=[(None,{1:values(SkeletalMesh=mesh,AnimationMode=0,GlobalAnimRateScale=1.)}),
               (None,{2:values(Skeleton=rig)}),(None,{3:values(Skeleton=rig,SequenceLength=2.)})]
        return owner,component,clip,rig,reads,values
    def test_matching_body_rig_plays_with_authored_loop_speed_and_duration(self):
        owner,body,clip,rig,reads,values=self.objects()
        with patch('expedition33.story_animation.body',return_value=body),patch('expedition33.values.capture_selected_values',side_effect=reads),patch('expedition33.assets.load_asset',return_value=N(return_value=clip)),patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=body),None)):
            duration=owner.play((8,9,10),dict(selection,speed=.5),player=True)
        self.assertEqual(duration,4.);self.assertTrue(owner.records)
        self.assertEqual(owner._call.call_args_list[0].kwargs,dict(_track=(body.index,body.serial,body.address),NewAnimToPlay=clip,bLooping=True))
    def test_incompatible_rig_never_dispatches_or_changes_animation_mode(self):
        owner,body,clip,rig,reads,values=self.objects();reads[-1]=(None,{3:values(Skeleton=None,SequenceLength=2.)})
        with patch('expedition33.story_animation.body',return_value=body),patch('expedition33.values.capture_selected_values',side_effect=reads),patch('expedition33.assets.load_asset',return_value=N(return_value=clip)):
            with self.assertRaisesRegex(ValueError,'skeletons differ'):owner.play((8,9,10),selection)
        owner._call.assert_not_called();self.assertFalse(owner.records);self.assertFalse(owner.failed)
    def test_player_special_animation_is_not_overwritten(self):
        owner,body,clip,rig,reads,values=self.objects();reads[0][1][1].values[(0,'AnimationMode')]=1
        with patch('expedition33.story_animation.body',return_value=body),patch('expedition33.values.capture_selected_values',side_effect=reads),patch('expedition33.assets.load_asset',return_value=N(return_value=clip)):
            with self.assertRaisesRegex(ValueError,'special animation'):owner.play((8,9,10),selection,player=True)
        owner._call.assert_not_called()

    def test_missing_skeletons_are_not_considered_a_compatible_pair(self):
        owner,body,clip,rig,reads,values=self.objects();reads[1]=(None,{2:values(Skeleton=None)});reads[-1]=(None,{3:values(Skeleton=None,SequenceLength=2.)})
        with patch('expedition33.story_animation.body',return_value=body),patch('expedition33.values.capture_selected_values',side_effect=reads),patch('expedition33.assets.load_asset',return_value=N(return_value=clip)):
            with self.assertRaisesRegex(ValueError,'skeletons differ'):owner.play((8,9,10),selection)
        owner._call.assert_not_called()

class AnimationPreflightCleanupTests(unittest.TestCase):
    def test_unused_prepared_actor_is_not_stopped_or_restored(self):
        owner=DialogueAnimations.__new__(DialogueAnimations)
        owner.scope=object();owner.records={(1,2,3):(N(object=object()),0,1.)};owner.mutated=set();owner.failed=False;owner._call=Mock()
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close())
        owner._call.assert_not_called()

    def test_only_actor_that_was_animated_is_restored(self):
        owner=DialogueAnimations.__new__(DialogueAnimations)
        changed=object();unused=object();owner.scope=object();owner.failed=False;owner._call=Mock()
        owner.records={(1,2,3):(N(object=changed),0,1.),(4,5,6):(N(object=unused),0,1.)};owner.mutated={(1,2,3)}
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close())
        self.assertEqual(len(owner._call.call_args_list),2)
        self.assertTrue(all(call.args[0] is changed for call in owner._call.call_args_list))


class AnimationBatchPreflightTests(unittest.TestCase):
    def setUp(self):
        def obj(i,cls):return N(index=i,serial=10+i,address=1000+i,class_index=1,class_name=cls)
        self.body=obj(1,'SkeletalMeshComponent');self.mesh=obj(2,'SkeletalMesh')
        self.clips=[obj(3,'AnimSequence'),obj(4,'AnimSequence')];self.rig=obj(5,'Skeleton');self.instance=obj(6,'AnimInstance')
        self.owner=DialogueAnimations.__new__(DialogueAnimations)
        self.owner.scope=N(pid=7,_session=N(),_check=Mock());self.owner.records={};self.owner.prepared={}
        self.owner.failed=False;self.owner.preflight_reads=True
        self.actor=(9,19,1009);self.selections=({'asset':'a'},{'asset':'b'},{'asset':'a'})
        self.state=self.values(SkeletalMesh=self.mesh,AnimationMode=0,GlobalAnimRateScale=1.,AnimScriptInstance=self.instance)
        self.assets={2:self.values(Skeleton=self.rig),3:self.values(Skeleton=self.rig,SequenceLength=2.),4:self.values(Skeleton=self.rig,SequenceLength=3.)}
    @staticmethod
    def values(**kw):return N(types={(0,k):'ObjectProperty' for k in kw},values={(0,k):v for k,v in kw.items()},errors={},truncated=set())
    def exercise(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            actor_read=stack.enter_context(patch('expedition33.story_animation.body',return_value=self.body))
            reads=stack.enter_context(patch('expedition33.values.capture_selected_values',side_effect=((None,{1:self.state}),(None,self.assets))))
            stack.enter_context(patch('expedition33.assets.load_asset',side_effect=(N(return_value=c) for c in self.clips)))
            retain=stack.enter_context(patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=self.body),None)))
            try:return self.owner.prepare_many(self.actor,self.selections,player=True)
            finally:self.actor_read=actor_read;self.reads=reads;self.retain=retain
    def test_two_clips_share_only_current_batch_body_and_asset_reads(self):
        body,state,clips=self.exercise()
        self.assertIs(body,self.body);self.assertIs(state,self.state);self.assertEqual([r[2] for r in clips],[2.,3.])
        self.actor_read.assert_called_once_with(self.owner.scope,self.actor,defer_reads=True)
        self.assertEqual(self.reads.call_count,2);self.retain.assert_called_once()
        self.assertEqual(self.reads.call_args.args[1],((2,12,1002),(3,13,1003),(4,14,1004)))
        self.assertEqual(len(self.owner.prepared),2)
    def test_every_new_batch_reobserves_mesh_mode_instance_and_clips(self):
        self.exercise();self.state.values[(0,'AnimationMode')]=1
        with self.assertRaisesRegex(ValueError,'special animation'):self.exercise()
        self.actor_read.assert_called_once();self.assertEqual(self.reads.call_count,1);self.retain.assert_not_called()
    def test_one_incompatible_clip_never_publishes_any_new_qualification(self):
        self.assets[4].values[(0,'Skeleton')]=None
        with self.assertRaisesRegex(ValueError,'skeletons differ'):self.exercise()
        self.assertEqual(self.owner.prepared,{});self.assertEqual(self.owner.records,{})
        self.retain.assert_not_called()
    def test_truncated_body_is_not_accepted_as_performance_ready(self):
        self.state.truncated.add((0,'AnimScriptInstance'))
        with self.assertRaisesRegex(ValueError,'observation incomplete'):self.exercise()
        self.retain.assert_not_called();self.assertFalse(self.owner.prepared)
    def test_read_failure_does_not_publish_partial_batch_or_repeat_reads(self):
        from expedition33 import RuntimeQueryError
        from expedition33.story_preflight import PreflightReadDeferred
        with patch('expedition33.story_animation.body',return_value=self.body),patch('expedition33.values.capture_selected_values',side_effect=RuntimeQueryError('REFLECTION_TARGET_CHANGED')) as reads:
            with self.assertRaises(PreflightReadDeferred):self.owner.prepare_many(self.actor,self.selections,player=True)
        reads.assert_called_once();self.assertFalse(self.owner.prepared);self.assertFalse(self.owner.records)
    def test_empty_or_unbounded_batch_does_not_discover_actor(self):
        with patch('expedition33.story_animation.body') as read:
            for rows in ((),tuple({'asset':str(i)} for i in range(33))):
                with self.assertRaisesRegex(ValueError,'32'):self.owner.prepare_many(self.actor,rows)
        read.assert_not_called()

    def test_same_operation_body_proof_skips_only_duplicate_body_reads(self):
        from expedition33.story_animation import BodyPreflightObservation
        self.body.outer_index,self.body.outer_serial=self.actor[:2];self.body.object_flags=0
        self.owner.scope._session._transport=N(command_wait_protocol=1,_native_command_sequence=19)
        reader=N(_token=object())
        with patch('expedition33._reader.active_reader',return_value=reader):
            proof=BodyPreflightObservation(self.owner.scope,self.actor,self.body,self.state)
            with patch('expedition33.story_animation.body') as body_read,patch('expedition33.values.capture_selected_values',return_value=(None,self.assets)) as reads,\
                    patch('expedition33.assets.load_asset',side_effect=(N(return_value=c) for c in self.clips)),\
                    patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=self.body),None)):
                result=self.owner.prepare_many(self.actor,self.selections,player=True,body_observation=proof)
        self.assertIs(result[0],self.body);body_read.assert_not_called();reads.assert_called_once()
        self.assertTrue(proof.used);self.assertEqual(len(self.owner.prepared),2)


class BodyPreflightObservationTests(unittest.TestCase):
    def fixture(self):
        from expedition33.story_animation import BodyPreflightObservation
        actor=(1,2,3);component=N(outer_index=1,outer_serial=2,object_flags=0)
        state=AnimationBatchPreflightTests.values(SkeletalMesh=object(),AnimationMode=0,GlobalAnimRateScale=1.,AnimScriptInstance=object())
        session=N(_transport=N(command_wait_protocol=1,_native_command_sequence=9))
        scope=N(_session=session,_check=Mock());reader=N(_token=object())
        with patch('expedition33._reader.active_reader',return_value=reader):proof=BodyPreflightObservation(scope,actor,component,state)
        return proof,scope,reader,actor,component,state

    def test_body_proof_can_be_consumed_once_without_invocation(self):
        proof,scope,reader,actor,component,state=self.fixture()
        with patch('expedition33._reader.active_reader',return_value=reader):
            self.assertEqual(proof.consume(scope,actor),(component,state))
            self.assertIsNone(proof.consume(scope,actor))

    def test_native_dispatch_next_poll_or_selected_actor_change_forces_fresh_path(self):
        for change in ('sequence','next_poll','different_reader','actor','session','unbound'):
            proof,scope,reader,actor,*_=self.fixture()
            if change=='sequence':scope._session._transport._native_command_sequence+=1
            elif change=='next_poll':reader._token=object()
            elif change=='different_reader':reader=N(_token=reader._token)
            elif change=='actor':actor=(7,8,9)
            elif change=='session':scope=N(_session=object(),_check=Mock())
            else:reader._token=None
            with self.subTest(change=change),patch('expedition33._reader.active_reader',return_value=reader):
                self.assertIsNone(proof.consume(scope,actor));self.assertTrue(proof.used)

    def test_incomplete_body_or_foreign_owner_is_rejected_before_publication(self):
        from expedition33.story_animation import BodyPreflightObservation
        for change in ('owner','generation','retiring','truncated','missing'):
            proof,scope,reader,actor,component,state=self.fixture()
            if change=='owner':component.outer_index=8
            elif change=='generation':component.outer_serial=9
            elif change=='retiring':component.object_flags=0x20
            elif change=='truncated':state.truncated.add((0,'AnimScriptInstance'))
            else:state.values.pop((0,'AnimationMode'))
            with self.subTest(change=change),patch('expedition33._reader.active_reader',return_value=reader):
                with self.assertRaises((ValueError,RuntimeError)):BodyPreflightObservation(scope,actor,component,state)


class AnimationWarmPlannerTests(unittest.TestCase):
    def test_fresh_batch_keeps_independent_planners_without_any_extra_capture(self):
        def obj(i):return N(index=i,serial=i+10,address=i+1000,class_index=99,object_flags=0)
        target=obj(1);clips=(obj(2),obj(3));function=obj(4)
        catalog=N(pid=7,by_index={obj.index:obj for obj in (target,*clips)},find_path=lambda path:function)
        first=Mock(_catalog=catalog);second=Mock(_catalog=catalog)
        session=N();warm=N(session=session,paths={'/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage'},observations=object(),planner=Mock())
        session._story_performance_preflight=warm
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=N(pid=7,_session=session,invocation_planner=Mock(side_effect=(first,second)))
        owner.calls={}
        with patch('expedition33.catalog.capture_selected') as read:
            calls=[owner._prepare_call(target,'AnimInstance','PlaySlotAnimationAsDynamicMontage',_observed=catalog,Asset=clip,LoopCount=1) for clip in clips]
        read.assert_not_called();warm.planner.assert_not_called();self.assertEqual(owner.scope.invocation_planner.call_count,2)
        for planner,call in zip((first,second),calls):
            planner.adopt_observations.assert_called_once_with(catalog)
            self.assertIs(call,planner.prepare_dialogue_slot.return_value)
        self.assertIsNot(calls[0],calls[1]);first.close.assert_not_called();second.close.assert_not_called()
        owner.scope=object();owner.records={};owner.failed=False
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close())
        first.close.assert_called_once();second.close.assert_called_once()
    def test_fresh_batch_rejects_changed_clip_before_plan_or_dispatch(self):
        target=N(index=1,serial=2,address=100,object_flags=0);clip=N(index=3,serial=4,address=300,class_index=99,object_flags=0)
        session=N();warm=N(session=session,paths={'/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage'},observations=object())
        session._story_performance_preflight=warm
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=N(pid=7,_session=session,invocation_planner=Mock());owner.calls={}
        catalog=N(pid=7,by_index={1:target,3:N(**(vars(clip)|{'serial':5}))})
        with self.assertRaisesRegex(RuntimeError,'target or clip changed'):
            owner._prepare_call(target,'AnimInstance','PlaySlotAnimationAsDynamicMontage',_observed=catalog,Asset=clip)
        owner.scope.invocation_planner.assert_not_called();self.assertEqual(owner.calls,{})
    def test_shared_planner_is_closed_once_after_unused_preflight(self):
        owner=DialogueAnimations.__new__(DialogueAnimations)
        planner=Mock();owner.calls={'first':(planner,object()),'second':(planner,object())}
        owner.scope=object();owner.records={};owner.failed=False
        owner._warm_planners={(1,2,3):(object(),planner)}
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):
            self.assertTrue(owner.close())
        planner.close.assert_called_once();self.assertEqual(owner._warm_planners,{})
    def test_same_target_keeps_each_clip_plan_in_its_own_generation(self):
        def obj(i):return N(index=i,serial=i+10,address=i+1000,class_index=99)
        target=obj(1);clip=obj(2);other=obj(3);function=obj(4)
        catalog=N(by_index={1:target,2:clip,3:other},find_path=lambda path:function)
        first=Mock(_catalog=catalog);second=Mock(_catalog=catalog)
        warm=N(paths={'/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage'},planner=Mock(side_effect=(first,second)))
        owner=DialogueAnimations.__new__(DialogueAnimations);owner.scope=N(pid=7,_session=N(_story_performance_preflight=warm))
        owner.calls={};owner.preflight_reads=True
        a=owner._prepare_call(target,'AnimInstance','PlaySlotAnimationAsDynamicMontage',Asset=clip,LoopCount=1)
        b=owner._prepare_call(target,'AnimInstance','PlaySlotAnimationAsDynamicMontage',Asset=other,LoopCount=1)
        self.assertEqual(warm.planner.call_count,2)
        self.assertIs(a,first.prepare_dialogue_slot.return_value);self.assertIs(b,second.prepare_dialogue_slot.return_value)
        first.adopt_observations.assert_not_called();second.adopt_observations.assert_not_called()
        self.assertIs(owner._prepare_call(target,'AnimInstance','PlaySlotAnimationAsDynamicMontage',Asset=clip,LoopCount=1),a)
        self.assertEqual(warm.planner.call_count,2)

