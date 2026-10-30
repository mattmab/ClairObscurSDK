import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch

from test_runtime_scene_editor import package
from scene_editor_tests.loading import LoadingPreview,validate_dependencies
from scene_editor_tests.authored_preview import AuthoredPreview
from expedition33.ui_shell_proof import UiProofPending


class LoadingPreviewTests(unittest.TestCase):
    def setUp(self):
        self.mod=N(authored_preview=None)
        self.session=object()
        self.scope=N(_session=self.session)
        self.context=N(gi=('gi',1),signature=('title',))

    def prepare(self,*,ready=True):
        dependencies=Mock(gi=self.context.gi,ready=ready)
        dependencies.close.return_value=True
        with patch('scene_editor_tests.loading.CinematicDependencies',return_value=dependencies) as factory:
            owner=LoadingPreview(self.mod,self.session);owner.prepare(self.context)
            factory.assert_called_once_with(self.session,self.context.gi)
        return owner,dependencies

    def test_prepared_owner_is_independent_and_fallback_is_available(self):
        owner,deps=self.prepare()
        self.assertIs(owner.available(self.scope),deps)
        self.assertIsNone(owner.available(N(_session=object())))
        deps.ready=False;self.assertIsNone(owner.available(self.scope))
        deps.ready=True;owner.released=True;self.assertIsNone(owner.available(self.scope))

    def test_failed_partial_preparation_is_journalled_before_dispatch(self):
        deps=Mock(gi=self.context.gi,ready=False);deps.prepare.side_effect=RuntimeError('preparation failed')
        deps.close.return_value=True
        with patch('scene_editor_tests.loading.CinematicDependencies',return_value=deps):
            owner=LoadingPreview(self.mod,self.session)
            with self.assertRaisesRegex(RuntimeError,'preparation failed'):owner.prepare(self.context)
        self.assertIs(self.mod._scene_loading,owner)
        self.assertIsNone(owner.available(self.scope));owner.close();deps.close.assert_called_once()

    def test_changed_game_instance_never_adopts_old_selectors(self):
        owner,deps=self.prepare()
        with self.assertRaises(UiProofPending):owner.bind(N(gi=('different',2),signature=('world',)))
        self.assertTrue(owner.released);self.assertIsNone(owner.available(self.scope))
        owner.close();deps.close.assert_called_once()

    def test_changed_title_or_world_waits_for_preview_before_releasing(self):
        for callback in ('observe_title','bind'):
            with self.subTest(callback=callback):
                owner,deps=self.prepare()
                self.mod.authored_preview=N(closed=False,dependencies=deps)
                with self.assertRaises(UiProofPending):
                    getattr(owner,callback)(N(gi=('different',2),signature=('next',)))
                self.assertFalse(owner.released);deps.close.assert_not_called()
                self.mod.authored_preview.closed=True
                if callback=='bind':
                    with self.assertRaises(UiProofPending):owner.bind(N(gi=('different',2),signature=('next',)))
                else:owner.observe_title(N(gi=('different',2),signature=('next',)))
                self.assertTrue(owner.released);owner.close()

    def test_consumer_and_deferred_cleanup_prevent_release(self):
        owner,deps=self.prepare()
        self.mod.authored_preview=N(closed=False,dependencies=deps)
        with self.assertRaises(UiProofPending):owner.close()
        deps.close.assert_not_called();self.assertFalse(owner.released)
        self.mod.authored_preview.closed=True;deps.close.side_effect=(False,True)
        with self.assertRaises(UiProofPending):owner.close()
        self.assertFalse(owner.closed);owner.close()
        self.assertTrue(owner.released);self.assertIsNone(self.mod._scene_loading)

    def test_partial_release_and_cancelled_disable_never_lend_dependencies(self):
        model=package.Mod();raw=object();scope=N(_session=raw)
        deps=Mock(gi=self.context.gi,ready=True);deps.close.side_effect=(False,True)
        with patch('scene_editor_tests.loading.CinematicDependencies',return_value=deps):
            owner=LoadingPreview(model,raw);owner.prepare(self.context)
        self.assertFalse(model.prepare_disable())
        self.assertTrue(owner.retiring);self.assertFalse(owner.released)
        model.cancel_disable_preparation()
        self.assertFalse(model._disable_preparing)
        self.assertIsNone(owner.available(scope))
        with self.assertRaises(UiProofPending):owner.bind(self.context)
        self.assertTrue(owner.released);self.assertIsNone(model._scene_loading)

    def test_world_retirement_closes_preview_before_loading_owner(self):
        model=package.Mod();model._retirement_token='old'
        preview=Mock();preview.retire_world.side_effect=('deferred','ack');model.authored_preview=preview
        owner=Mock();owner.release.side_effect=(UiProofPending('wait'),None);model._scene_loading=owner
        model.authored.close=Mock(return_value=True)
        context=N(previous_token='old')
        self.assertEqual(model.poll_world_retirement(context),'pending')
        owner.release.assert_not_called()
        self.assertEqual(model.poll_world_retirement(context),'pending')
        self.assertIsNone(model.authored_preview);owner.release.assert_called_once()
        self.assertEqual(model.poll_world_retirement(context),'ack')
        self.assertEqual(owner.release.call_count,2)

    def test_loader_disable_waits_for_preview_and_dependency_ack_then_runs_once(self):
        from pathlib import Path
        import tempfile
        from expedition33.mods import ModLoader,ModDisablePending
        from test_mods import FakeSession
        from test_world_lifecycle import SOURCE,ready
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'World').mkdir();(root/'World/mod.py').write_text(SOURCE)
            session=FakeSession();session._transport=object();session._closed=False
            loader=ModLoader(root,session=session);coordinator=loader.install_world_lifecycle()
            try:
                loader.load('World');coordinator.observe(ready());loader.enable('World')
                record=loader._loaded['World'];scope=record[2]
                model=package.Mod();model.session=scope;model.runtime.session=scope
                record[1]=model;coordinator.bindings['World'].instance=model
                preview=Mock();preview.close.side_effect=(False,True);model.authored_preview=preview
                owner=Mock()
                attempts=[]
                def release():
                    attempts.append(1)
                    if len(attempts)==1:raise UiProofPending('wait')
                    model._scene_loading=None
                owner.release.side_effect=release;model._scene_loading=owner
                model.disable=Mock(wraps=model.disable)
                for attempt in range(2):
                    with self.assertRaises(ModDisablePending):loader.disable('World')
                    self.assertEqual(coordinator.bindings['World'].state,'bound')
                    self.assertNotIn('World',loader._cleanup_failures)
                    self.assertIs(record[2],scope);model.disable.assert_not_called()
                loader.disable('World')
                model.disable.assert_called_once();self.assertIsNone(record[2])
            finally:
                if not loader._closed:loader.close()
                session.close()

    def test_coordinator_changed_gi_defers_close_before_publishing_released(self):
        from expedition33.loading_preparation import LoadingPreparation
        for kind in ('title','world'):
            with self.subTest(kind=kind):
                mod=package.Mod();session=object()
                old=Mock(gi='old',ready=True);old.close.side_effect=(False,True)
                new=Mock(gi='new',ready=True);new.close.return_value=True
                loader=N(_startup_preparations={'SceneEditor':object()},_loaded={'SceneEditor':(None,mod)},
                    world_lifecycle=N(cleanup_ready=False))
                loader.registry=N(views=lambda:[{'folder':'SceneEditor','id':'editor'}],
                    _settings=N(get=lambda key:{'enabled':True}))
                coordinator=LoadingPreparation(session,loader)
                old_context=N(kind='title',gi='old',signature=('old',))
                new_context=N(kind=kind,gi='new',signature=('new',),world='new')
                packet=lambda context:N(ui_context=context,admission=N(activation_ready=False))
                with patch('scene_editor_tests.loading.CinematicDependencies',side_effect=(old,new)):
                    self.assertTrue(coordinator.observe(packet(old_context)))
                    owner=coordinator.owners['SceneEditor']
                    coordinator.observe(packet(new_context))
                    self.assertFalse(owner.released);self.assertIs(coordinator.owners['SceneEditor'],owner)
                    coordinator.observe(packet(new_context))
                    self.assertTrue(owner.released)
                    if kind=='world':coordinator.observe(packet(new_context))
                    self.assertIsNot(coordinator.owners['SceneEditor'],owner)
                    self.assertFalse(coordinator.failed)
                    coordinator.close()


class PreviewWiringTests(unittest.TestCase):
    def preview(self,dependencies):
        p=object.__new__(AuthoredPreview)
        p.dependencies=dependencies;p.scope=N(pid=9,_session=N(_transport=N(_executable='reader')))
        p.play_scope=None;p.edited=True;p.document={'source':{'nodes':{}},'cast_edits':[],'npc_tracks':[]}
        p.profile=N(anchor=(0.,0.,0.),sequence='/Game/Test.Test')
        p.menu=Mock();return p

    def run_until_sequence(self,dependencies):
        p=self.preview(dependencies)
        with patch('scene_editor_tests.authored_preview.SessionScope',return_value='play-scope'), \
             patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()), \
             patch('expedition33.simon_portable._snapshot',return_value=('context',None,(0.,0.,0.))), \
             patch('expedition33.cinematics.authored_media.source',return_value=None), \
             patch('scene_editor_tests.authored_preview.OwnedSequenceContext') as services, \
             patch('scene_editor_tests.authored_preview.OwnedLevelSequence',side_effect=RuntimeError('sequence boundary')) as sequence:
            with self.assertRaisesRegex(RuntimeError,'sequence boundary'):p._prepare_playback()
        return services,sequence

    def test_fresh_context_precedes_passing_prepared_selectors(self):
        gi=N(pid=9,index=1,serial=2,address=3,class_name='BP_jRPG_GI_Custom_C',name='CurrentGI')
        widgets=Mock();music=Mock()
        widgets.capture.return_value=music.capture.return_value=N(objects=(gi,))
        deps=Mock(gi=(9,1,2,3),routing_class='routing',widget_dependencies=widgets,music_dependencies=music,
                  asset_loader='loader',sequence_metadata='metadata')
        services,sequence=self.run_until_sequence(deps)
        deps.validate.assert_called_once_with('play-scope','context')
        services.assert_called_once_with('play-scope',unittest.mock.ANY,routing_class='routing',
                                         widget_dependencies=widgets,music_dependencies=music)
        sequence.assert_called_once_with('play-scope',asset_loader='loader',metadata='metadata')

    def test_both_service_game_instances_must_match_current_world(self):
        current=N(pid=9,index=1,serial=2,address=3,class_name='BP_jRPG_GI_Custom_C',name='CurrentGI')
        other=N(pid=9,index=4,serial=5,address=6,class_name='BP_jRPG_GI_Custom_C',name='StaleGI')
        for wrong in ('widget_dependencies','music_dependencies'):
            with self.subTest(wrong=wrong):
                widget=Mock();music=Mock()
                widget.capture.return_value=music.capture.return_value=N(objects=(current,))
                deps=Mock(gi=(9,1,2,3),widget_dependencies=widget,music_dependencies=music)
                getattr(deps,wrong).capture.return_value=N(objects=(other,))
                with self.assertRaisesRegex(RuntimeError,'service GameInstance changed'):
                    validate_dependencies(deps,'scope','context')

    def test_missing_preparer_preserves_original_path(self):
        services,sequence=self.run_until_sequence(None)
        services.assert_called_once_with('play-scope',unittest.mock.ANY)
        sequence.assert_called_once_with('play-scope')

    def test_context_mismatch_fails_before_music_or_sequence_dispatch(self):
        deps=Mock();deps.validate.side_effect=RuntimeError('GameInstance changed')
        p=self.preview(deps)
        with patch('scene_editor_tests.authored_preview.SessionScope',return_value='play-scope'), \
             patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()), \
             patch('expedition33.simon_portable._snapshot',return_value=('context',None,(0.,0.,0.))), \
             patch('expedition33.cinematics.authored_media.source',return_value=None), \
             patch('scene_editor_tests.authored_preview.OwnedSequenceContext') as services, \
             patch('scene_editor_tests.authored_preview.OwnedLevelSequence') as sequence:
            with self.assertRaisesRegex(RuntimeError,'GameInstance changed'):p._prepare_playback()
        services.assert_not_called();sequence.assert_not_called()


if __name__=='__main__':unittest.main()
