import unittest
from unittest.mock import Mock,patch
from expedition33.story_facial import DialogueFacialPerformance
class FacialLifecycleTests(unittest.TestCase):
    def test_getter_output_lease_is_kept_until_acknowledged_scope_cleanup(self):
        owner,skin,face,_=self.preflight_owner();owner._hold=Mock(side_effect=lambda value:value)
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        owner._hold.assert_called_once_with(skin)
        result=owner._face_results[0];result.__exit__.assert_not_called();result.release.assert_not_called()
        with patch('expedition33._retired_tracking.close_lease_only_scope',side_effect=(False,True)):
            self.assertFalse(owner.close());self.assertEqual(owner._face_results,[result])
            self.assertTrue(owner.close());self.assertEqual(owner._face_results,[])
        result.release.assert_not_called() # The scope owns/retires the same output token.
    def test_foreign_or_expired_getter_ownership_never_reacquires_face(self):
        for case in ('result','scope','lease','identity'):
            owner,_,face,_=self.preflight_owner();result=owner._call()
            if case=='result':result.active=False
            elif case=='scope':result._scope=lambda:object()
            elif case=='lease':result._leases[0].active=False
            else:result._leases[0].object=type(face)(**(vars(face)|{'serial':99}))
            owner._hold=Mock()
            with self.assertRaises(RuntimeError):owner._retain_face_result(result)
            owner._hold.assert_not_called();self.assertEqual(owner._face_results,[result])
    def test_face_mesh_and_clip_skeletons_share_one_fresh_read(self):
        from types import SimpleNamespace as N
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance);owner.scope=N(pid=17);owner._preflighting=True
        mesh=N(index=1,serial=2,address=100,object_flags=0);clip=N(index=3,serial=4,address=300,object_flags=0)
        skeleton=N(index=5,serial=6,address=500)
        def value(obj):return N(values={(20,'Skeleton'):obj},types={(20,'Skeleton'):'ObjectProperty'},errors={},truncated=set())
        catalog=N(by_index={1:mesh,3:clip});rows={1:value(skeleton),3:value(skeleton)}
        with patch('expedition33.story_facial.capture_selected_values',return_value=(catalog,rows)) as read:
            self.assertTrue(owner._matching_skeletons(mesh,clip))
            read.assert_called_once_with(17,((1,2,100),(3,4,300)),fields=('Skeleton',),references=True)
            rows[3].truncated.add((20,'Skeleton'))
            with self.assertRaisesRegex(RuntimeError,'observation incomplete'):owner._matching_skeletons(mesh,clip)
        rows[3]=value(None)
        with patch('expedition33.story_facial.capture_selected_values',return_value=(catalog,rows)):
            self.assertFalse(owner._matching_skeletons(mesh,clip))
    def preflight_owner(self):
        from types import SimpleNamespace as N
        from unittest.mock import MagicMock
        def obj(index,**kw):return N(index=index,serial=1,address=0x10000+index*16,**kw)
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.actor=(1,1,0x10010);owner.closed=False;owner.unknown=False;owner.prepared=False;owner.owned=False
        owner.preflight_ready=False;owner.face=None;owner.old={};owner.changed_class=False;owner.planners=[]
        skin=obj(2,class_name='BP_CharacterSkinComponent_C',outer_index=1,outer_serial=1)
        face=obj(3,outer_index=1,outer_serial=1);mesh=obj(4);skeleton=obj(5)
        instance=obj(6,class_name='Face_AnimBP_Companion_C');cls=obj(7);clip=obj(8)
        values=dict(AnimClass=cls,AnimationMode=0,SkeletalMesh=mesh,AnimScriptInstance=instance)
        resources=Mock();resources.load.side_effect=[obj(9),clip]
        owner.scope=N(pid=11,_check=Mock(),_session=N(_transport=N(dialogue_slot_protocol=1),_story_construction_resources=N(resources=resources)))
        owner._hold=lambda value:value;owner._void=Mock();owner._set_scalar=Mock()
        owner._prepare_call=Mock()
        def result():
            value=MagicMock();value.active=True;value._scope=lambda:owner.scope;value._session=lambda:owner.scope._session
            value.outputs={'Face':face};value._leases=(N(active=True,_scope=lambda:owner.scope,_session=lambda:owner.scope._session,_token=12,object=face),)
            value.__enter__.return_value=value
            return value
        owner._call=Mock(side_effect=lambda *a,**kw:result())
        owner._values=Mock(side_effect=[values,{'Skeleton':skeleton},{'Skeleton':skeleton}])
        owner._matching_skeletons=lambda mesh,clip:owner._values(mesh,('Skeleton',))['Skeleton']==owner._values(clip,('Skeleton',))['Skeleton']
        return owner,skin,face,values

    def test_preflight_only_reads_and_never_snapshots_restoration_or_changes_face(self):
        from types import SimpleNamespace as N
        from expedition33.story_facial import SKIN
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        owner._call.assert_called_once_with(skin,SKIN+'GetFaceSkeletalMesh')
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()
        self.assertEqual(owner._prepare_call.call_count,4)
        owner._prepare_call.return_value.invoke.assert_not_called()
        self.assertTrue(owner.preflight_ready);self.assertFalse(owner.prepared)
        self.assertIsNone(owner.face);self.assertEqual(owner.old,{})
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close())
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()

    def test_changed_skin_binding_cannot_activate_old_warmed_face(self):
        from types import SimpleNamespace as N
        from contextlib import nullcontext
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        other=N(index=30,serial=1,address=0x30000)
        owner._call.side_effect=None;owner._call.return_value=nullcontext(N(outputs={'Face':other}))
        with self.assertRaisesRegex(RuntimeError,'face changed after preflight'):owner.prepare()
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()
        self.assertEqual(owner.old,{})

    def test_unchanged_revalidation_uses_fresh_binding_without_reloading_assets_or_skeletons(self):
        from types import SimpleNamespace as N
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin) as discover:
            owner.preflight()
            owner._values.reset_mock();owner._values.side_effect=None;owner._values.return_value=values
            owner._call.reset_mock()
            owner.preflight(revalidate=True)
        self.assertEqual(discover.call_count,2) # Old retained skin alone is not current-cast proof.
        owner._call.assert_called_once()
        owner._values.assert_called_once_with(face,('AnimClass','AnimationMode','SkeletalMesh','AnimScriptInstance'))
        self.assertEqual(owner.scope._session._story_construction_resources.resources.load.call_count,2)
        self.assertTrue(owner.preflight_ready);self.assertEqual(owner.old,{})
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()

    def test_changed_mesh_revalidation_runs_full_skeleton_qualification(self):
        from types import SimpleNamespace as N
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):
            owner.preflight()
            changed=dict(values,SkeletalMesh=N(index=30,serial=1,address=0x30000))
            owner.scope._session._story_construction_resources.resources.load.side_effect=[owner.human,owner.clip]
            owner._values.side_effect=[changed,changed,{'Skeleton':N(index=31,serial=1,address=0x31000)},{'Skeleton':N(index=32,serial=1,address=0x32000)}]
            with self.assertRaisesRegex(RuntimeError,'skeleton differs'):owner.preflight(revalidate=True)
        self.assertFalse(owner.preflight_ready);self.assertEqual(owner.old,{})
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()

    def test_changed_skin_generation_cannot_reuse_retained_binding(self):
        from types import SimpleNamespace as N
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        replacement=N(**vars(skin));replacement.serial+=1
        owner.scope._session._story_construction_resources.resources.load.side_effect=[owner.human,owner.clip]
        skeleton=N(index=40,serial=1,address=0x40000)
        owner._values.side_effect=[values,{'Skeleton':skeleton},{'Skeleton':skeleton}]
        owner._call.reset_mock()
        with patch('expedition33.story_facial.current_skin',return_value=replacement):owner.preflight(revalidate=True)
        self.assertIs(owner.preflight_skin,replacement)
        self.assertIs(owner._call.call_args.args[0],replacement)
        self.assertEqual(owner.scope._session._story_construction_resources.resources.load.call_count,4)
        self.assertEqual(owner.old,{})

    def test_revalidation_read_failure_retains_owner_and_rechecks_on_next_attempt(self):
        from types import SimpleNamespace as N
        from expedition33 import RuntimeQueryError
        from expedition33.story_preflight import PreflightReadDeferred
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        with patch('expedition33.story_facial.capture_selected_values',side_effect=RuntimeQueryError('skin read crossed GC')):
            with self.assertRaises(PreflightReadDeferred):owner.preflight(revalidate=True)
        self.assertIs(owner.preflight_face,face);self.assertFalse(owner.unknown);self.assertFalse(owner._preflighting)
        owner._values.side_effect=None;owner._values.return_value=values
        with patch('expedition33.story_facial.current_skin',return_value=skin) as fresh:owner.preflight(revalidate=True)
        fresh.assert_called_once();self.assertEqual(owner.old,{})
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()

    def test_revalidation_cannot_accept_an_already_mutated_face(self):
        owner,skin,face,values=self.preflight_owner();owner.prepared=True;owner.preflight_ready=True
        with self.assertRaisesRegex(RuntimeError,'active facial playback'):owner.preflight(revalidate=True)
        owner._call.assert_not_called();owner._void.assert_not_called()

    def test_changed_animation_instance_cannot_reuse_old_restoration_values(self):
        from types import SimpleNamespace as N
        from contextlib import nullcontext
        owner,skin,face,values=self.preflight_owner()
        with patch('expedition33.story_facial.current_skin',return_value=skin):owner.preflight()
        owner._call.side_effect=None;owner._call.return_value=nullcontext(N(outputs={'Face':face}))
        owner._values.side_effect=None;owner._values.return_value=dict(values,AnimScriptInstance=N(index=30,serial=1,address=0x30000))
        with self.assertRaisesRegex(RuntimeError,'AnimScriptInstance'):owner.prepare()
        owner._void.assert_not_called();owner._set_scalar.assert_not_called()
        self.assertEqual(owner.old,{})

    def test_missing_component_cannot_mutate_an_exploration_actor(self):
        from types import SimpleNamespace as N
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.actor=(1,2,3);owner.owned=False;owner.scope=N(pid=7);owner._call=Mock()
        with patch('expedition33.story_facial.capture_matching',return_value=N(objects=[])),patch('expedition33.story_facial.capture_selected',return_value=N(by_index={1:N(class_name='BP_Cine_Noah_C')})):
            with self.assertRaisesRegex(RuntimeError,'disposable cinematic Gustave'):owner._bind_owned_component()
        owner._call.assert_not_called()

    def test_created_facial_component_is_destroyed_after_face_restoration(self):
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.closed=False;owner.unknown=False;owner.prepared=False;owner.face=object()
        owner.old={'AnimClass':'original','bPauseAnims':False,'bDisablePostProcessBlueprint':False}
        owner.changed_class=True;owner.created_component=object();created=owner.created_component
        owner.actor=(1,2,3)
        owner.planners=[];owner.scope=object();owner._void=Mock();owner._set_scalar=Mock()
        from types import SimpleNamespace as N
        owner.scope=N(pid=7);actor=object()
        with patch('expedition33.story_facial.capture_selected',return_value=N(by_index={1:actor})),patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close())
        calls=owner._void.call_args_list
        self.assertEqual(calls[0].args[1],'/Script/Engine.SkeletalMeshComponent:SetAnimClass')
        self.assertEqual(calls[-1].args,(created,'/Script/Engine.ActorComponent:K2_DestroyComponent'))
        self.assertEqual(calls[-1].kwargs,{'Object':actor})
        self.assertIsNone(owner.created_component)

    def test_borrowed_companion_component_cannot_be_created_in_another_world(self):
        from types import SimpleNamespace as N
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.actor=(1,2,0x10000);owner.owned=False;owner._call=Mock()
        owner.scope=N(pid=7,_world_binding_token=((7,9,90,0x90000),(),(),1))
        actor=N(class_name='BP_Pawn_AICompanion_Noah_C')
        other=N(class_name='World',index=10,serial=100,address=0xa0000)
        catalog=N(by_index={1:actor},outer_chain=lambda _: (actor,other))
        with patch('expedition33.story_facial.capture_matching',return_value=N(objects=[])),patch('expedition33.story_facial.capture_selected',return_value=catalog):
            with self.assertRaisesRegex(RuntimeError,'disposable cinematic Gustave'):owner._bind_owned_component()
        owner._call.assert_not_called()
    def test_owned_cinematic_face_updates_original_animation_event_when_offscreen(self):
        from expedition33.story_facial import FACE
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.owned=True;owner.instance=object();owner.component=object()
        owner._stop_mouth=Mock();owner._set_scalar=Mock();owner._void=Mock()
        owner._apply(25,False)
        owner._void.assert_any_call(owner.instance,FACE+'BlueprintUpdateAnimation',DeltaTimeX=1./60.)
        self.assertEqual(owner.last,(25,False))

    def test_exploration_actor_does_not_receive_extra_cinematic_update_events(self):
        from expedition33.story_facial import FACE
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.owned=False;owner.instance=object();owner.component=object()
        owner._stop_mouth=Mock();owner._set_scalar=Mock();owner._void=Mock()
        owner._apply(25,False)
        self.assertFalse(any(call.args[1]==FACE+'BlueprintUpdateAnimation' for call in owner._void.call_args_list))

    def test_scalar_type_preflight_does_not_quarantine_an_untouched_face(self):
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner._values=Mock(return_value={'Expression_1':0});owner.unknown=False
        from types import SimpleNamespace as N
        owner.scope=N(assign_scalar=Mock(side_effect=ValueError('Unsupported scalar type')))
        with self.assertRaises(ValueError):owner._set_scalar(object(),'Expression_1',25)
        self.assertFalse(owner.unknown)

    def test_timer_returns_to_neutral_listening(self):
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.deadline=2.5;owner._apply=Mock()
        with patch('expedition33.story_facial.time.monotonic',return_value=2.49):owner.poll()
        owner._apply.assert_not_called()
        with patch('expedition33.story_facial.time.monotonic',return_value=2.5):owner.poll()
        owner._apply.assert_called_once_with(0,False)
    def test_world_retirement_never_calls_replacement_actor(self):
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.closed=False;owner.unknown=False;owner.prepared=True;owner.planners=[];owner.scope=object()
        owner._void=Mock(side_effect=AssertionError('No engine call after world retirement'))
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):
            self.assertTrue(owner.close(world_retired=True))
        self.assertTrue(owner._closed);owner._void.assert_not_called()
    def test_unknown_owner_cannot_claim_restoration(self):
        owner=DialogueFacialPerformance.__new__(DialogueFacialPerformance)
        owner.closed=False;owner.unknown=True
        self.assertFalse(owner.close());self.assertFalse(owner._closed)
