import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,MagicMock,patch
from expedition33 import file_audio as audio


def obj(index):return N(index=index,serial=index+1,address=0x10000+index*8,class_index=100,pid=7)


class FileAudioMetadataTests(unittest.TestCase):
    def metadata(self):
        session=N(pid=7,_check=Mock())
        scope=N(pid=7,_session=session,_check=Mock(),invocation_planner=Mock())
        resources=N(scope=scope,load=Mock(),hold=Mock(side_effect=lambda o:N(object=o)))
        owner=audio._FileAudioMetadata(resources)
        return owner,scope,resources

    def test_title_warm_retains_only_exact_static_dependencies_and_schema(self):
        owner,scope,resources=self.metadata()
        objects={path:obj(i) for i,path in enumerate(audio.MEDIA_OBJECTS+audio.MEDIA_FUNCTIONS)}
        found=N(find_path=objects.__getitem__)
        descriptor=N(object=obj(100));catalog=object()
        planner=MagicMock();planner.__enter__.return_value=planner
        scope.invocation_planner.return_value=planner
        with patch.object(audio,'capture_matching',return_value=found) as matching, \
                patch.object(audio,'describe_selected',return_value=object()), \
                patch('expedition33.story_performance_preflight._pod_closure',return_value=(catalog,{100:descriptor})):
            owner.prepare()
        self.assertTrue(owner.ready);self.assertEqual(set(owner.objects),set(objects))
        resources.load.assert_called_once_with(audio.VOICE)
        self.assertEqual(resources.hold.call_count,len(objects));matching.assert_called_once()
        planner.prepare.assert_not_called();planner.invoke.assert_not_called()
        self.assertIs(owner.observations,planner.observations.return_value)

    def test_failed_warm_is_journaled_and_never_retried_or_published(self):
        owner,scope,resources=self.metadata()
        with patch.object(audio._FileAudioMetadata,'prepare',side_effect=RuntimeError('partial acquisition')) as prepare, \
                patch.object(audio,'shared_operation',return_value=nullcontext()):
            with self.assertRaisesRegex(RuntimeError,'partial'):audio.warm_file_audio(resources)
            held=scope._session._file_audio_preparation
            with self.assertRaisesRegex(RuntimeError,'not replayed'):audio.warm_file_audio(resources)
        self.assertIs(held.resources,resources);self.assertFalse(held.ready)
        self.assertFalse(hasattr(scope._session,'_file_audio_metadata'));prepare.assert_called_once()

    def test_warm_reuses_metadata_but_rejects_changed_resource_owner(self):
        owner,scope,resources=self.metadata();owner.ready=True
        scope._session._file_audio_preparation=owner;scope._session._file_audio_metadata=owner
        self.assertIs(audio.warm_file_audio(resources),owner)
        with self.assertRaisesRegex(RuntimeError,'changed'):
            audio.warm_file_audio(N(scope=scope))

    def test_every_world_planner_reads_current_targets_and_closes_on_failed_read(self):
        owner,scope,resources=self.metadata();owner.ready=True;owner.observations=object()
        target=obj(77);first,second=Mock(),Mock()
        scope.invocation_planner.side_effect=(first,second)
        with patch.object(audio,'capture_selected',side_effect=(object(),RuntimeError('retired target'))) as read:
            self.assertIs(owner.planner(scope,(target,target)),first)
            with self.assertRaisesRegex(RuntimeError,'retired target'):owner.planner(scope,(target,))
        self.assertEqual(read.call_count,2)
        read.assert_called_with(7,((77,78,target.address),))
        first.adopt_observations.assert_called_once();first.close.assert_not_called()
        second.close.assert_called_once()
        self.assertIs(scope.invocation_planner.call_args.kwargs['observations'],owner.observations)

    def test_foreign_or_closed_scope_cannot_use_static_selectors(self):
        owner,scope,resources=self.metadata();owner.ready=True
        owner.objects={'/Script/Engine.CameraActor':obj(1)}
        foreign=N(_session=object(),_check=Mock())
        with patch.object(audio,'capture_selected') as read:
            with self.assertRaisesRegex(RuntimeError,'another session'):owner.catalog(foreign,('/Script/Engine.CameraActor',))
            scope._check.side_effect=RuntimeError('scope closed')
            with self.assertRaisesRegex(RuntimeError,'scope closed'):owner.catalog(scope,('/Script/Engine.CameraActor',))
        read.assert_not_called()

    def test_static_selectors_are_fresh_exact_and_do_not_use_registry_fallback(self):
        owner,scope,resources=self.metadata();owner.ready=True
        owner.objects={'/Script/Engine.CameraActor':obj(1)}
        with patch.object(audio,'capture_selected',side_effect=('first','second')) as read, \
                patch.object(audio,'capture_matching') as matching:
            self.assertEqual(owner.catalog(scope,('/Script/Engine.CameraActor',)),'first')
            self.assertEqual(owner.catalog(scope,('/Script/Engine.CameraActor',)),'second')
            with self.assertRaises(ValueError):owner.catalog(scope,('/Script/Engine.Actor',))
        self.assertEqual(read.call_count,2);matching.assert_not_called()

    def test_first_media_call_uses_prepared_metadata_without_dispatch_or_registry_scan(self):
        owner,scope,resources=self.metadata();owner.ready=True
        target=obj(15);function=obj(20);catalog=N(by_index={15:target},find_path=Mock(return_value=function))
        planner=Mock(_catalog=catalog);owner.planner=Mock(return_value=planner)
        scope._session._file_audio_metadata=owner
        player=audio.OwnedFileAudio.__new__(audio.OwnedFileAudio)
        player.scope=scope;player.calls={};player.planners=[]
        with patch.object(audio.Calls,'_prepare_call') as fallback,patch.object(audio,'capture_matching') as matching:
            call=player._prepare_call(target,audio.SYNTH+'Start')
        self.assertIs(call,planner.prepare.return_value);self.assertEqual(player.planners,[planner])
        call.invoke.assert_not_called();fallback.assert_not_called();matching.assert_not_called()

    def test_playback_warm_keeps_metadata_yield_and_never_opens_source(self):
        metadata,scope,resources=self.metadata();metadata.ready=True
        player=audio.OwnedFileAudio.__new__(audio.OwnedFileAudio)
        player.scope=scope;player.calls={};player.planners=[]
        player.player=obj(15);player.component=obj(16);player.source=obj(17)
        catalog=N(by_index={o.index:o for o in (player.player,player.component,player.source)},find_path=Mock())
        planner=Mock(_catalog=catalog);metadata.planner=Mock(return_value=planner)
        scope._session._file_audio_metadata=metadata
        with patch.object(audio,'capture_matching') as matching,patch.object(audio,'describe_selected') as describe:
            steps=player._prepare_playback_calls();next(steps)
            planner.prepare.assert_not_called()
            with self.assertRaises(StopIteration):next(steps)
        metadata.planner.assert_called_once_with(scope,(player.player,player.source,player.component))
        self.assertEqual(planner.prepare.call_count,10)
        planner.prepare.return_value.invoke.assert_not_called();matching.assert_not_called();describe.assert_not_called()

    def camera(self):
        from expedition33.cinematics.blueprint_actor import BlueprintActor
        ctx=dict(world=(7,1,2,0x10000),controller=(7,3,4,0x11000),world_path='/Game/Test.Test')
        cls=N(index=5,serial=6,address=0x12000,name='CameraActor')
        world=N(index=1,serial=2,address=0x10000,class_name='World')
        catalog=N(by_index={1:world,3:obj(3),8:N(class_name='CameraActor',class_index=5)},
            find_path=lambda path:cls if path=='/Script/Engine.CameraActor' else obj(10))
        catalog.with_observations=lambda other:catalog
        catalog.resolve=lambda obj:obj;catalog.outer_chain=lambda obj:(world,)
        construction=N(context=Mock(return_value=ctx),catalog=Mock(return_value=catalog))
        construction.anchor=N(identity=(12,13,0x14000));construction.observe=Mock(return_value=(catalog,{}))
        media=N(catalog=Mock(return_value=catalog))
        scope=N(pid=7,_check=Mock(),_parent=lambda:object(),_session=N(_story_construction_resources=construction,
            _file_audio_metadata=media,_transport=N(_executable='probe',sequence_flight_playback_protocol=1,timeline_current_world_protocol=1)))
        actor=BlueprintActor.__new__(BlueprintActor);actor.scope=scope;actor.state='new';actor.owner=Mock(actor_identity=(8,9,0x13000))
        values=N(values={(1,'Pawn'):obj(11)},errors={},truncated=False)
        return actor,construction,media,catalog,values,ctx

    def test_camera_reuses_exact_class_but_keeps_fresh_world_and_spawn_observations(self):
        actor,construction,media,catalog,values,ctx=self.camera()
        with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()), \
                patch('expedition33.cinematics.blueprint_actor.capture_matching') as scan, \
                patch('expedition33.cinematics.blueprint_actor.capture_selected_values',return_value=(catalog,{})) as read, \
                patch('expedition33.cinematics.blueprint_actor._construction_context',return_value=(catalog.by_index[3],obj(11),catalog.by_index[1])) as check:
            self.assertEqual(actor.prepare_camera((0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.)),actor.identity)
        media.catalog.assert_called_once_with(actor.scope,('/Script/Engine.CameraActor',))
        self.assertEqual(construction.context.call_count,1);self.assertEqual(read.call_count,1)
        construction.observe.assert_called_once();self.assertEqual(check.call_count,2)
        actor.owner.spawn_timeline_prepared.assert_called_once();scan.assert_not_called()

    def test_retained_camera_class_does_not_allow_spawn_after_world_change(self):
        actor,construction,media,catalog,values,ctx=self.camera()
        with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()), \
                patch('expedition33.cinematics.blueprint_actor._construction_context',side_effect=RuntimeError('World changed before Blueprint construction')):
            with self.assertRaisesRegex(RuntimeError,'World changed before'):
                actor.prepare_camera((0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.))
        actor.owner.spawn_timeline_prepared.assert_not_called();self.assertEqual(actor.state,'failed')


class AudioPlannerGenerationTests(unittest.TestCase):
    def setUp(self):
        import test_retained_results
        test_retained_results.RetainedResultTests.setUp(self)

    def test_new_setup_path_does_not_revoke_previous_real_prepared_call(self):
        from expedition33._scope import SessionScope
        from expedition33.catalog import Catalog
        scope=SessionScope(self.session);self.addCleanup(scope.close)
        with scope.invocation_planner(catalog=self.p.catalog) as base:observations=base.observations()
        metadata=audio._FileAudioMetadata.__new__(audio._FileAudioMetadata)
        metadata.ready=True;metadata.scope=scope;metadata.session=self.session
        metadata.paths=frozenset((audio.MEDIA+'Close',audio.MEDIA+'IsReady'));metadata.observations=observations
        self.session._file_audio_metadata=metadata
        player=audio.OwnedFileAudio.__new__(audio.OwnedFileAudio)
        player.scope=scope;player.calls={};player.planners=[]
        with patch.object(audio,'capture_selected',return_value=self.p.catalog), \
                patch.object(Catalog,'find_path',return_value=self.p.function):
            first=player._prepare_call(self.p.target,audio.MEDIA+'Close')
            second=player._prepare_call(self.p.target,audio.MEDIA+'IsReady')
        self.assertIsNot(first._planner(),second._planner())
        # Real PreparedInvocation generation checks: a mock planner would not
        # detect adoption revoking an already published stop/cleanup call.
        first._check();second._check()
        self.assertEqual(len(player.planners),2)
        self.assertNotIn('retained-invoke',self.transport.calls)
        for planner in player.planners:planner.close()
