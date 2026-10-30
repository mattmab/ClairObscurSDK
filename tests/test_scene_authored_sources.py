import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from test_runtime_scene_editor import package
from scene_editor_tests.authored import AuthoredWorkspace
from scene_editor_tests.view import SceneView

class AuthoredWorkspaceTests(unittest.TestCase):
    def test_import_context_observes_current_world_through_its_own_retained_selector(self):
        workspace=AuthoredWorkspace();scope=NS(_session=NS(_transport=NS(stable_lease_protocol=1)))
        workspace.scope=scope
        observe=Mock(side_effect=({'world':'first'},{'world':'second'},RuntimeError('inactive lease')))
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=observe) as factory,\
             patch('scene_editor_tests.authored.controller_context') as legacy:
            self.assertEqual(workspace._context(object()),{'world':'first'})
            self.assertEqual(workspace._context(object()),{'world':'second'})
            with self.assertRaisesRegex(RuntimeError,'inactive lease'):workspace._context(object())
        self.assertEqual(factory.call_args_list,[((scope,),)]*3)
        legacy.assert_not_called()

    def test_import_context_legacy_runtime_retains_fresh_fallback(self):
        workspace=AuthoredWorkspace();session=object()
        for capability in (0,True,None):
            workspace.scope=NS(_session=NS(_transport=NS(stable_lease_protocol=capability)))
            with patch('scene_editor_tests.authored.controller_context',return_value={'world':'legacy'}) as legacy,\
                 patch('expedition33.cinematics.controller_anchor.context_observer') as stable:
                self.assertEqual(workspace._context(session),{'world':'legacy'})
                legacy.assert_called_once_with(session,project=True);stable.assert_not_called()

    def test_scene_editor_enables_background_import_only_for_its_workspace(self):
        self.assertTrue(package.Mod().authored.background_import)
        self.assertFalse(AuthoredWorkspace().background_import)

    def test_authored_timeline_uses_same_source_picker_and_waits_for_close(self):
        from scene_editor_tests.timeline import TimelineView
        from test_authored_timeline import fixture
        owner=package.Mod();owner.timeline_return=dict(photo=False,at=3.5,selected=0)
        preview=NS(sequence_timeline=True,owner=owner,playing=False,ready=True,message='',queue=Mock(),
                   editor=NS(workspace=owner.authored,document=fixture()))
        owner.authored_preview=preview
        view=TimelineView(None,preview);view.render();view.activate(view.revision,16)
        self.assertEqual(view.picker,'sequences');view.activate(view.revision,19)
        source=view.selected_source;view.activate(view.revision,31)
        self.assertEqual(owner.pending_timeline_source,source);preview.queue.assert_called_once_with('close')
        self.assertIs(owner.authored_preview,preview)
        owner._finish_authored_preview(None)
        self.assertIsNone(owner.authored_preview);self.assertFalse(owner.want_author)
        self.assertFalse(owner.want_open);self.assertEqual(owner.timeline_return['at'],3.5)

    def test_switching_sources_recovers_edits_without_overwriting_explicit_save(self):
        import tempfile
        from expedition33.cinematics.authored_timeline import TimelineStore
        from test_authored_timeline import fixture,SECTION
        workspace=AuthoredWorkspace()
        with tempfile.TemporaryDirectory() as directory:
            workspace.store=TimelineStore(directory);workspace.document=fixture();original=workspace.save()
            workspace.retime(SECTION,1000,2000);draft=workspace.document
            workspace.preserve_draft();workspace.preserve_draft()
            rows=workspace.store.list();self.assertEqual(len(rows),2)
            self.assertEqual(workspace.store.read(original)['section_edits'],{})
            recovered=next(row for row in rows if row['id']!=original)
            self.assertTrue(recovered['name'].endswith('(Recovered)'))
            self.assertEqual(workspace.store.read(recovered['id'])['section_edits'],draft['section_edits'])
            self.assertIs(workspace.document,draft);self.assertTrue(workspace.dirty)
            self.assertEqual(workspace.key,original)

    def test_recovery_failure_does_not_retire_or_replace_current_workspace(self):
        from test_authored_timeline import fixture,SECTION
        workspace=AuthoredWorkspace();workspace.document=fixture();workspace.retime(SECTION,1000,2000)
        workspace.store=Mock();workspace.store.save.side_effect=OSError('disk full')
        workspace.close=Mock();document=workspace.document
        with self.assertRaisesRegex(OSError,'disk full'):workspace.begin_load(None,workspace.catalog[0]['path'])
        workspace.close.assert_not_called();self.assertIs(workspace.document,document)

    def test_normal_stop_cancels_pending_source_work_without_restarting_it(self):
        model=package.Mod()
        model.authored.loading=(n for n in range(2));reader=Mock();model.authored.load_reader=reader
        model.pending_authored='source';model.pending_timeline_source='source';model.timeline_return={'at':3.5}
        document={'name':'Draft'};model.authored.document=document
        self.assertIn('cancelled',model.stop())
        self.assertIsNone(model.pending_authored);self.assertIsNone(model.pending_timeline_source)
        self.assertIsNone(model.timeline_return);self.assertIs(model.authored.document,document)
        reader.close.assert_called_once();self.assertTrue(model.want_open)

    def test_cancelled_incremental_import_closes_worker_and_preserves_draft(self):
        workspace=AuthoredWorkspace();document={'name':'Unsaved draft'};workspace.document=document
        closed=[]
        def steps():
            try:yield 1;yield 2
            finally:closed.append(True)
        workspace.loading=steps();next(workspace.loading)
        reader=Mock();workspace.load_reader=reader
        self.assertTrue(workspace.close())
        self.assertEqual(closed,[True]);reader.close.assert_called_once()
        self.assertIs(workspace.document,document);self.assertIsNone(workspace.loading)

    def _background_workspace(self):
        from expedition33.cinematics.authored_import_job import ImportSnapshot
        import time
        workspace=AuthoredWorkspace(background_import=True);source=workspace.catalog[0]
        identity=(12,34,0x10000);token=('world',1)
        graph=dict(sequence=source['path'],nodes={source['path']:dict(class_name='LevelSequence',fields={},errors={},truncated=[])},pending=[],editable=False)
        job=Mock();job.poll.return_value=ImportSnapshot('completed',1,graph,{'read_ms':10.})
        job.close.return_value=True
        scope=NS(pid=42,_session=NS(_transport=NS(_executable='candidate')),
                 _world_binding_token=token,_callbacks_ready=Mock(return_value=True),_check=Mock())
        workspace.scope=scope;workspace.source=source['path'];workspace.context={'world':'test'}
        workspace.load_job=workspace.loading=job;workspace.load_job_generation=workspace.load_generation=9
        workspace.load_job_token=token;workspace.load_job_identity=identity
        workspace.load_draft_guard=(workspace.document,None,workspace.key,workspace.dirty)
        workspace.load_started=time.perf_counter();workspace.load_work=0.
        return workspace,job,scope,identity,graph

    def test_background_import_commits_only_after_owner_world_and_identity_checks(self):
        from contextlib import nullcontext
        workspace,job,scope,identity,graph=self._background_workspace()
        asset=NS(index=identity[0],serial=identity[1],address=identity[2],class_name='LevelSequence')
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=NS(by_index={identity[0]:asset})) as observed,\
             patch('scene_editor_tests.authored.controller_context',return_value=workspace.context):
            self.assertTrue(workspace.poll_load(None))
        self.assertIs(workspace.graph,graph);self.assertEqual(workspace.document['source']['sequence'],workspace.source)
        self.assertEqual(observed.call_count,2);observed.assert_called_with(42,(identity,));self.assertEqual(scope._check.call_count,2)
        self.assertIsNone(workspace.load_job);self.assertIsNone(workspace.loading)

    def test_background_import_rejects_stale_generation_world_and_source_identity(self):
        from contextlib import nullcontext
        for kind in ('generation','world_token','admission','context','identity'):
            with self.subTest(kind=kind):
                workspace,job,scope,identity,graph=self._background_workspace()
                old={'name':'Draft'};workspace.document=old
                asset=NS(index=identity[0],serial=identity[1],address=identity[2],class_name='LevelSequence')
                if kind=='generation':workspace.load_generation+=1
                if kind=='world_token':scope._world_binding_token=('world',2)
                if kind=='admission':scope._callbacks_ready.return_value=False
                if kind=='identity':asset.serial+=1
                context={'world':'other'} if kind=='context' else workspace.context
                with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
                     patch('expedition33.catalog.capture_selected',return_value=NS(by_index={identity[0]:asset})),\
                     patch('scene_editor_tests.authored.controller_context',return_value=context),\
                     patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
                    with self.assertRaises(RuntimeError):workspace.poll_load(None)
                self.assertIs(workspace.document,old);self.assertIsNone(workspace.graph)

    def test_background_cancel_defers_lease_release_and_never_restarts_worker(self):
        workspace,job,scope,_,_=self._background_workspace();old={'name':'Draft'};workspace.document=old
        job.close.side_effect=[False,True]
        with patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True) as close:
            self.assertFalse(workspace.close());self.assertTrue(workspace.cleanup_pending)
            close.assert_not_called();self.assertIs(workspace.scope,scope);self.assertIs(workspace.loading,job)
            self.assertTrue(workspace.close());close.assert_called_once_with(scope)
        self.assertFalse(workspace.cleanup_pending);self.assertIsNone(workspace.loading)
        self.assertIs(workspace.document,old);job.start.assert_not_called()

    def test_target_exit_during_active_import_cleanup_is_terminal_not_pending(self):
        from expedition33 import TargetExitedError
        from expedition33._scope import SessionScope
        session=NS(_check=Mock(),_transport=NS(lease_policy_protocol=0,target_exit_code=None),
                   console=NS(),_abort_ownership=Mock())
        workspace,job,_,_,_=self._background_workspace();scope=SessionScope(session)
        lease=NS(release=Mock(return_value=False));scope._leases.append(lease);workspace.scope=scope
        job.close.side_effect=[False,True]
        self.assertFalse(workspace.close());self.assertIs(workspace.scope,scope)
        session._transport.target_exit_code=7
        with self.assertRaises(TargetExitedError) as error:workspace.close()
        self.assertEqual(error.exception.exit_code,7)
        self.assertIs(workspace.scope,scope);self.assertFalse(scope._closed)
        self.assertEqual(scope._leases,[lease]);lease.release.assert_not_called()
        session._abort_ownership.assert_not_called()

    def test_background_world_change_during_document_creation_rejects_commit(self):
        from contextlib import nullcontext
        workspace,_,_,identity,_=self._background_workspace();old={'name':'Draft'};workspace.document=old
        asset=NS(index=identity[0],serial=identity[1],address=identity[2],class_name='LevelSequence')
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=NS(by_index={identity[0]:asset})),\
             patch('scene_editor_tests.authored.controller_context',side_effect=[workspace.context,workspace.context,workspace.context,{'world':'other'}]),\
             patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'World changed'):workspace.poll_load(None)
        self.assertIs(workspace.document,old);self.assertIsNone(workspace.graph)

    def test_background_admission_loss_during_asset_check_rejects_commit(self):
        from contextlib import nullcontext
        workspace,_,scope,identity,_=self._background_workspace();old={'name':'Draft'};workspace.document=old
        asset=NS(index=identity[0],serial=identity[1],address=identity[2],class_name='LevelSequence')
        scope._callbacks_ready.side_effect=[True,False]
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=NS(by_index={identity[0]:asset})),\
             patch('scene_editor_tests.authored.controller_context',return_value=workspace.context),\
             patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'World changed'):workspace.poll_load(None)
        self.assertIs(workspace.document,old)

    def test_background_begin_requires_admission_before_and_after_asset_load(self):
        from contextlib import nullcontext
        for admission in ([False],[True,False]):
            with self.subTest(admission=admission):
                workspace=AuthoredWorkspace(background_import=True)
                scope=NS(pid=42,_session=NS(_transport=NS(_executable='candidate')),
                         _callbacks_ready=Mock(side_effect=admission))
                asset=NS(index=12,serial=34,address=0x10000,class_name='LevelSequence')
                with patch('scene_editor_tests.authored.SessionScope',return_value=scope),\
                     patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
                     patch('expedition33.assets.load_asset',return_value=NS(return_value=asset)),\
                     patch('scene_editor_tests.authored.controller_context',return_value={'world':'A'}),\
                     patch('expedition33.cinematics.authored_import_job.AuthoredImportJob') as create,\
                     patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
                    with self.assertRaises(RuntimeError):workspace.begin_load(None,workspace.catalog[0]['path'])
                    create.assert_not_called()

    def test_background_import_rejects_editor_mutation_and_preserves_changed_draft(self):
        from contextlib import nullcontext
        from expedition33.cinematics.authored_timeline import digest
        workspace,_,_,identity,_=self._background_workspace();old={'name':'Draft'};workspace.document=old
        workspace.load_draft_guard=(old,digest(old),None,False)
        with self.assertRaisesRegex(ValueError,'finish or cancel'):workspace.add_npc('lune')
        old['name']='Changed while loading'
        asset=NS(index=identity[0],serial=identity[1],address=identity[2],class_name='LevelSequence')
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=NS(by_index={identity[0]:asset})),\
             patch('scene_editor_tests.authored.controller_context',return_value=workspace.context),\
             patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'draft changed'):workspace.poll_load(None)
        self.assertIs(workspace.document,old);self.assertEqual(old['name'],'Changed while loading')

    def test_background_world_revocation_invalidates_result_immediately(self):
        workspace,job,_,_,_=self._background_workspace()
        model=package.Mod();model.authored=workspace
        model.revoke_world(NS(previous_token='old'))
        job.cancel.assert_called_once();self.assertNotEqual(workspace.load_job_generation,workspace.load_generation)

    def test_stop_reports_cancellation_and_polls_deferred_worker_cleanup(self):
        workspace,job,scope,_,_=self._background_workspace();job.close.side_effect=[False,True]
        model=package.Mod();model.authored=workspace;model.session=object()
        model.pending_authored='source';model.pending_timeline_source='source'
        model.shared=NS(ui_ready=False);model.runtime.poll=Mock()
        old={'name':'Draft'};workspace.document=old
        with patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True) as release:
            self.assertIn('Cancelling',model.stop());release.assert_not_called()
            self.assertTrue(workspace.cleanup_pending)
            model.poll();release.assert_called_once_with(scope)
        self.assertIn('cancelled',model.message);self.assertFalse(workspace.cleanup_pending)
        self.assertIs(workspace.document,old)

    def test_incremental_import_preserves_draft_until_complete_and_releases_reader(self):
        from contextlib import nullcontext
        workspace=AuthoredWorkspace();old={'name':'Existing draft'};workspace.document=old
        source=workspace.catalog[0];workspace.source=source['path'];workspace.context={'world':'QA'}
        workspace.scope=NS(_session=NS(_transport=NS(stable_lease_protocol=0)))
        reader=Mock();reader.bind.side_effect=lambda:nullcontext();workspace.load_reader=reader
        graph={'sequence':source['path'],'nodes':{}}
        def steps():
            yield 1;yield 2;yield 3
            return graph
        workspace.loading=steps();replacement={'name':'Imported'}
        with patch('scene_editor_tests.authored.controller_context',return_value=workspace.context),patch('scene_editor_tests.authored.authored_timeline.create',return_value=replacement):
            self.assertFalse(workspace.poll_load(None,nodes=2))
            self.assertIs(workspace.document,old);reader.close.assert_not_called()
            self.assertTrue(workspace.poll_load(None,nodes=2))
        self.assertIs(workspace.document,replacement);self.assertIs(workspace.graph,graph)
        reader.close.assert_called_once();self.assertIsNone(workspace.load_reader)
        self.assertIsNone(workspace.loading)

    def test_existing_timeline_can_request_sequence_library_without_inline_teardown(self):
        from scene_editor_tests.timeline import TimelineView
        model=package.Mod();model.runtime=NS(scope=object(),authoring=True,photo_mode=False,last={'state':'timeline_paused','playhead':3.5,'selected':1})
        model.document={'actors':[],'events':[],'mute_game_music':False}
        model.stop=Mock()
        view=TimelineView(None,model);frame=view.render()
        control=next(c for c in frame.controls if c.token==18)
        self.assertEqual(control.label,'Game sequences')
        view.activate(frame.revision,18)
        self.assertEqual(view.picker,'sequences');model.stop.assert_not_called()
        source=model.authored.catalog[0]['path'];view.selected_source=source
        view.activate(view.revision,31)
        self.assertEqual(model.pending_timeline_source,source);model.stop.assert_not_called()
        self.assertEqual(model.timeline_return,dict(photo=False,at=3.5,selected=1))

    def test_source_close_returns_to_custom_timeline_only_after_successful_cleanup(self):
        model=package.Mod();document={'name':'Unsaved custom scene'};model.document=document
        model.timeline_return=dict(photo=True,at=3.5,selected=1);model.authored_preview=object()
        model._finish_authored_preview(None)
        self.assertIsNone(model.authored_preview);self.assertTrue(model.want_author)
        self.assertFalse(model.want_open);self.assertTrue(model.photo_author)
        self.assertIs(model.document,document)
        model.want_author=False;model._finish_authored_preview('Cleanup failed')
        self.assertFalse(model.want_author);self.assertTrue(model.want_open)
        self.assertIsNone(model.timeline_return)

    def test_independent_npc_tracks_have_saved_interval_and_placement_controls(self):
        from test_authored_timeline import fixture
        model=package.Mod();model.authored.document=fixture()
        view=SceneView(None,model);view.screen='scene_authored_npcs'
        self.assertEqual([r[2] for r in view._rows()[2] if r[1]=='scene_authored_npc_add'],['lune','sciel','verso'])
        key=model.authored.add_npc('sciel');model.authored.edit_npc(key,'start',100)
        model.authored.edit_npc(key,'X',120.);model.authored.edit_npc(key,'yaw',90.)
        view.authored_npc=key;view.screen='scene_authored_npc'
        fields=[r[2] for r in view._rows()[2] if r[1]=='scene_edit']
        self.assertIn(('authored_npc:start',100,'int'),fields)
        self.assertIn(('authored_npc:X',120.,'float'),fields)
        self.assertEqual(model.authored.document['npc_tracks'][0]['placement']['yaw'],90.)
        model.authored.remove_npc(key);self.assertEqual(model.authored.document['npc_tracks'],[])
    def test_extended_character_menus_follow_native_capability(self):
        from types import SimpleNamespace
        from test_authored_cast import fixture
        from expedition33.cinematics.authored_timeline import create
        source=fixture();model=package.Mod();model.authored.document=create(source,'Cast test')
        view=SceneView(None,model);view.screen='scene_authored_npcs'
        def options(op):return [r[2] for r in view._rows()[2] if r[1]==op]
        self.assertEqual(options('scene_authored_npc_add'),['lune','sciel','verso'])
        model.session=SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(timeline_extended_characters_protocol=1)))
        self.assertEqual(options('scene_authored_npc_add'),['lune','sciel','verso','maelle','monoco'])
        view.screen='scene_authored_cast_binding'
        view.authored_cast=(source['sequence'],'00000001000000000000000000000000')
        self.assertEqual(options('scene_authored_replace'),[None,'lune','sciel','verso','maelle','monoco'])
    def test_actor_replacement_controls_edit_and_restore_the_saved_cast(self):
        from test_authored_cast import fixture
        from expedition33.cinematics.authored_timeline import create
        source=fixture();model=package.Mod();model.authored.document=create(source,'Cast test')
        view=SceneView(None,model);view.screen='scene_authored_cast_binding'
        view.authored_cast=(source['sequence'],'00000001000000000000000000000000')
        rows=view._rows()[2]
        self.assertEqual([r[2] for r in rows if r[1]=='scene_authored_replace'],[None,'lune','sciel','verso'])
        model.authored.replace_cast(*view.authored_cast,'sciel')
        self.assertIn('Replacement: Sciel',view._rows()[1]);self.assertTrue(model.authored.dirty)
        model.authored.place_cast(*view.authored_cast,[120.,-50.,25.],90.)
        edits=[r[2] for r in view._rows()[2] if r[1]=='scene_edit']
        self.assertIn(('authored_cast:X',120.,'float'),edits)
        self.assertIn(('authored_cast:yaw',90.,'float'),edits)
        model.authored.replace_cast(*view.authored_cast,None)
        self.assertIn('Original character',view._rows()[1]);self.assertFalse(model.authored.document['cast_edits'])
        view.authored_cast=(source['sequence'],'00000002000000000000000000000000')
        self.assertFalse(any(r[1]=='scene_authored_replace' for r in view._rows()[2]))
    def test_cast_browser_uses_saved_source_without_runtime_handles(self):
        from test_authored_cast import fixture
        from expedition33.cinematics.authored_timeline import create
        source=fixture()
        for node in source['nodes'].values():node.update(errors={},truncated=[])
        model=package.Mod();model.authored.document=create(source,'Cast test')
        view=SceneView(None,model);view.screen='scene_authored_cast'
        rows=view._rows()[2];self.assertEqual(len(rows),3)
        view.authored_cast=rows[1][2];view.screen='scene_authored_cast_binding'
        self.assertIn('BP_Cine_Test_C',view._rows()[1])
        self.assertIsNone(model.authored.scope)
        view.screen='scene_authored_cast';view.query='body'
        self.assertEqual(len(view._rows()[2]),2)
    def test_curve_key_controls_show_saved_edits_without_native_source_leases(self):
        from test_authored_timeline import fixture,SECTION
        model=package.Mod();model.authored.document=fixture()
        view=SceneView(None,model);view.screen='scene_authored_section';view.authored_section=SECTION
        rows=view._rows()[2]
        self.assertTrue(any(row[1]=='scene_authored_channel' and row[2]==['Translation',0] for row in rows))
        view.screen='scene_authored_channel';view.authored_channel=['Translation',0]
        self.assertEqual(view._rows()[2][1][2],0)
        view.screen='scene_authored_key';view.authored_key=0
        self.assertEqual(view._rows()[2][1][2],('authored_key:at',0,'int'))
        model.authored.edit_key(SECTION,['Translation',0],0,at=500,value=12.5)
        self.assertEqual(view._rows()[2][2][2],('authored_key:value',12.5,'float'))
        self.assertIsNone(model.authored.scope)
    def test_catalog_and_browser_are_file_only_and_searchable(self):
        model=package.Mod();view=SceneView(None,model);view.screen='scene_authored'
        view.query='SimonIntro';title,detail,rows=view._rows()
        self.assertIn('Game-authored',title);self.assertIn('without starting playback',detail)
        self.assertEqual(len(rows),1);self.assertTrue(rows[0][3]);self.assertIn('SimonIntro',rows[0][0])
        view.authored_path=next(row['path'] for row in model.authored.catalog if row['title']=='SimonIntro')
        self.assertTrue(view._rows()[2][0][3]);self.assertIsNone(model.authored.scope)
    def test_library_selection_exposes_actions_in_inspector_without_loading_or_navigation(self):
        model=package.Mod();model.queue_authored=Mock();model.load_timeline_source=Mock()
        view=SceneView(Mock(),model);view.screen='scene_authored';view.query='SimonIntro'
        frame=view.render()
        self.assertFalse(frame.controls[56].enabled);self.assertFalse(frame.controls[57].enabled)
        frame=view.activate(view._revision,0)
        selected=view.authored_path
        self.assertEqual(view.screen,'scene_authored');self.assertEqual(view.query,'SimonIntro')
        self.assertIn(selected,frame.description)
        self.assertTrue(frame.controls[56].enabled);self.assertTrue(frame.controls[57].enabled)
        self.assertFalse(frame.controls[58].enabled)
        model.queue_authored.assert_not_called();model.load_timeline_source.assert_not_called()
        view.activate(view._revision,57)
        model.load_timeline_source.assert_called_once_with(selected,editing_only=True)

    def test_retained_import_is_world_checked_and_deferred_release_preserved(self):
        workspace=AuthoredWorkspace();scope=NS(_session=NS(_transport=NS(stable_lease_protocol=0)));path=workspace.catalog[0]['path']
        graph=dict(sequence=path,nodes={path:dict(class_name='LevelSequence',fields={},errors={},truncated=[])},pending=[],editable=False)
        with patch('scene_editor_tests.authored.SessionScope',return_value=scope),patch('scene_editor_tests.authored.controller_context',return_value={'world':'QA'}),patch('scene_editor_tests.authored.inspect_graph',return_value=graph) as inspect,patch('scene_editor_tests.authored.close_lease_only_scope',return_value=False):
            self.assertIs(workspace.load(object(),path),graph);inspect.assert_called_once_with(scope,path)
            self.assertFalse(workspace.close());self.assertIs(workspace.scope,scope)
            with self.assertRaisesRegex(RuntimeError,'pending'):workspace.load(object(),path)
            inspect.assert_called_once()
        with patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True):
            self.assertTrue(workspace.close());self.assertIsNone(workspace.scope);self.assertIsNone(workspace.graph)
    def test_world_change_rejects_import_and_releases_only_source_leases(self):
        workspace=AuthoredWorkspace();path=workspace.catalog[0]['path']
        with patch('scene_editor_tests.authored.SessionScope'),patch('scene_editor_tests.authored.controller_context',side_effect=[{'world':'A'},{'world':'B'}]),patch('scene_editor_tests.authored.inspect_graph',return_value={}),patch('scene_editor_tests.authored.close_lease_only_scope',return_value=True) as close:
            with self.assertRaisesRegex(RuntimeError,'World changed'):workspace.load(object(),path)
            close.assert_called_once();self.assertIsNone(workspace.graph)
    def test_deferred_mod_retirement_retains_workspace_and_revokes_queue(self):
        model=package.Mod();model.pending_authored='source';model._retirement_token='old'
        model.authored.close=Mock(return_value=False)
        model.revoke_world(NS(previous_token='old'))
        self.assertIsNone(model.pending_authored)
        self.assertEqual(model.poll_world_retirement(NS(previous_token='old')),'pending')
        self.assertIsNotNone(model.authored)

    def test_lifecycle_keeps_background_import_pending_until_lease_release(self):
        from expedition33.world_lifecycle import WorldLifecycle,Binding,RetirementContext
        workspace,job,_,_,_=self._background_workspace();job.close.side_effect=[False,True]
        child=NS(_closed=False,_children=[],_leases=[])
        root=NS(_closed=False,_children=[child],_leases=[])
        root.close=Mock(side_effect=lambda:setattr(root,'_closed',True))
        workspace.scope=child
        old={'name':'Draft'};workspace.document=old
        model=package.Mod();model.authored=workspace;model.pending_timeline_source='source'
        loader=NS(_loaded={'SceneEditor':[None,model,root]},registry=NS(changed=Mock()))
        lifecycle=WorldLifecycle(loader);context=RetirementContext('old',None,'loading_world_changed')
        row=Binding('old',model,root,state='retiring',context=context)
        lifecycle.bindings['SceneEditor']=row
        def release(scope):
            self.assertIs(scope,child);scope._closed=True;return True
        with patch('scene_editor_tests.authored.close_lease_only_scope',side_effect=release) as release_scope:
            lifecycle.poll_cleanup()
            self.assertEqual(row.state,'retiring');self.assertIsNone(row.error)
            self.assertFalse(row.domain_ack);self.assertIs(workspace.scope,child)
            self.assertFalse(child._closed);self.assertFalse(root._closed)
            self.assertIsNone(model.pending_timeline_source);release_scope.assert_not_called()
            self.assertIs(workspace.document,old)
            lifecycle.poll_cleanup()
        self.assertEqual(row.state,'retired');self.assertIsNone(row.error)
        self.assertTrue(child._closed);self.assertTrue(root._closed)
        self.assertIsNone(loader._loaded['SceneEditor'][2]);release_scope.assert_called_once_with(child)

    def test_preview_deferred_state_is_normalized_at_lifecycle_boundary(self):
        model=package.Mod();model._retirement_token='old'
        model.authored_preview=NS(retire_world=Mock(return_value='deferred'))
        self.assertEqual(model.poll_world_retirement(NS(previous_token='old')),'pending')
        self.assertIsNotNone(model.authored_preview)

    def test_loader_disable_and_shutdown_wait_for_background_worker_without_unknown(self):
        from pathlib import Path
        import tempfile
        from expedition33.mods import ModLoader,ModDisablePending
        from expedition33._scope import SessionScope
        from test_mods import FakeSession
        from test_world_lifecycle import SOURCE,ready
        for operation in ('disable','close'):
            with self.subTest(operation=operation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'World').mkdir();(root/'World/mod.py').write_text(SOURCE)
                session=FakeSession();session._transport=object();session._closed=False
                loader=ModLoader(root,session=session);coordinator=loader.install_world_lifecycle()
                try:
                    loader.load('World');coordinator.observe(ready());loader.enable('World')
                    record=loader._loaded['World'];scope=record[2]
                    model=package.Mod();model.session=scope;model.runtime.session=scope
                    record[1]=model;coordinator.bindings['World'].instance=model
                    child=SessionScope(scope);model.authored.scope=child
                    job=Mock();job.close.side_effect=[False,True,True]
                    model.authored.load_job=model.authored.loading=job
                    model.authored.load_job_generation=model.authored.load_generation=1
                    model.pending_authored='source';model.authored.document={'name':'Draft'}
                    action=(lambda:loader.disable('World')) if operation=='disable' else loader.close
                    with self.assertRaises(ModDisablePending):action()
                    self.assertEqual(coordinator.bindings['World'].state,'bound')
                    self.assertIs(record[2],scope);self.assertIs(model.authored.scope,child)
                    self.assertFalse(scope._closed);self.assertFalse(child._closed)
                    self.assertNotIn('World',loader._cleanup_failures)
                    model.poll();job.start.assert_not_called()
                    action()
                    self.assertTrue(child._closed);self.assertTrue(scope._closed)
                    self.assertIsNone(record[2]);self.assertEqual(model.authored.document,{'name':'Draft'})
                    if operation=='close':self.assertTrue(loader._closed)
                finally:
                    if not loader._closed:loader.close()
                    session.close()

    def test_registry_pending_disable_retries_and_honors_enable_or_world_retirement(self):
        from pathlib import Path
        import tempfile
        from expedition33.mods import ModLoader
        from expedition33._scope import SessionScope
        from expedition33.settings import SettingsStore
        from test_mods import FakeSession
        from test_world_lifecycle import SOURCE,ready,token
        for outcome in ('complete','enable','retirement','readmission','enable_uncertain','stage_enable_uncertain','bulk_enable','details_enable','scroll_enable'):
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'World').mkdir();(root/'World/mod.py').write_text(SOURCE)
                settings=SettingsStore(root/'settings.json')
                session=FakeSession();session._transport=object();session._closed=False
                loader=ModLoader(root,settings=settings,session=session);coordinator=loader.install_world_lifecycle()
                try:
                    loader.load('World');coordinator.observe(ready());loader.enable('World')
                    record=loader._loaded['World'];scope=record[2]
                    model=package.Mod();model.session=scope;model.runtime.session=scope
                    record[1]=model;coordinator.bindings['World'].instance=model
                    child=SessionScope(scope);model.authored.scope=child
                    job=Mock();job.close.side_effect=[False,True,True,True]
                    model.authored.load_job=model.authored.loading=job
                    model.authored.load_job_generation=model.authored.load_generation=1
                    model.pending_authored='source';model.authored.document={'name':'Draft'}
                    model.disable=Mock(wraps=model.disable)
                    sel=loader.registry.select('test.world')
                    sel=loader.registry.set_enabled(sel,False);view=loader.registry.view(sel)
                    self.assertTrue(view['enabled']);self.assertTrue(view['disable_pending'])
                    self.assertFalse(view['desired_enabled']);self.assertFalse(settings.get('test.world')['enabled'])
                    if outcome in ('enable','enable_uncertain','stage_enable_uncertain','bulk_enable','details_enable','scroll_enable'):
                        if outcome in ('enable_uncertain','stage_enable_uncertain'):coordinator.observe(None)
                        if outcome=='stage_enable_uncertain':
                            sel=loader.registry.stage_enabled(sel,True)
                            loader.registry.poll_pending_disables()
                            sel=loader.registry.select('test.world')
                        elif outcome=='scroll_enable':
                            from expedition33.mods_workspace_scroll import ScrollWorkspaceView
                            menu=ScrollWorkspaceView(loader.registry);frame=menu.render()
                            self.assertIn('DISABLING',frame.description)
                            self.assertIn('WAIT',[c.label for c in frame.controls])
                            control=next(c for c in frame.controls if c.label=='Enable' and c.enabled)
                            menu.activate(frame.revision,control.token)
                            sel=loader.registry.select('test.world')
                        elif outcome in ('bulk_enable','details_enable'):
                            from expedition33.mods_workspace import ModsWorkspaceView
                            menu=ModsWorkspaceView(loader.registry)
                            if outcome=='bulk_enable':
                                menu.screen='bulk';frame=menu.render()
                                control=next(c for c in frame.controls if c.label=='Enable all')
                                frame=menu.activate(frame.revision,control.token)
                                control=next(c for c in frame.controls if c.label=='Confirm enable 1 mods')
                            else:
                                menu.screen='details';menu.selection=sel;frame=menu.render()
                                control=next(c for c in frame.controls if c.label=='Enable')
                            menu.activate(frame.revision,control.token)
                            sel=loader.registry.select('test.world')
                        else:sel=loader.registry.set_enabled(sel,True)
                        view=loader.registry.view(sel)
                        self.assertTrue(view['enabled']);self.assertTrue(view['desired_enabled'])
                        self.assertFalse(view['disable_pending']);self.assertFalse(model._disable_preparing)
                        self.assertTrue(settings.get('test.world')['enabled'])
                        loader.registry.poll_pending_disables();model.disable.assert_not_called()
                        if outcome in ('enable_uncertain','stage_enable_uncertain'):coordinator.observe(ready())
                        loader.disable('World')
                    elif outcome=='retirement':
                        coordinator.observe_loading_world(token(9)[0],token(9)[1])
                        loader.poll()
                        self.assertEqual(coordinator.bindings['World'].state,'retired')
                        model.disable.assert_not_called();self.assertIsNone(record[2])
                        self.assertFalse(loader.registry._pending_disables)
                    else:
                        if outcome=='readmission':
                            coordinator.observe(None);loader.poll()
                            self.assertTrue(loader.registry.view(loader.registry.select('test.world'))['disable_pending'])
                            model.disable.assert_not_called();self.assertIs(record[2],scope)
                            coordinator.observe(ready())
                        loader.poll();view=loader.registry.view(loader.registry.select('test.world'))
                        self.assertFalse(view['enabled']);self.assertFalse(view['disable_pending'])
                        self.assertFalse(view['desired_enabled']);model.disable.assert_called_once()
                        self.assertTrue(child._closed);self.assertIsNone(record[2])
                finally:
                    if not loader._closed:loader.close()
                    session.close()
    def test_authored_range_ui_saves_and_reloads_a_separate_edit_document(self):
        from test_authored_timeline import fixture,SECTION
        from expedition33.cinematics.authored_timeline import TimelineStore
        import tempfile
        model=package.Mod();model.authored.document=fixture();model.authored.dirty=True
        view=SceneView(None,model);view.screen='scene_authored_timeline'
        self.assertTrue(any(row[1]=='scene_authored_section' for row in view._rows()[2]))
        view.screen='scene_authored_section';view.authored_section=SECTION
        rows=view._rows()[2];self.assertEqual(rows[1][2],('authored:start',0,'int'))
        model.edit_authored_range(SECTION,'start',1000)
        with tempfile.TemporaryDirectory() as directory:
            model.authored.store=TimelineStore(directory);key=model.authored.save()
            model.authored.document=None;model.authored.load_saved(key)
            self.assertEqual(model.authored.sections()[0]['start'],1000)
            self.assertFalse(model.authored.dirty)
            self.assertEqual(model.authored.source,model.authored.document['source']['sequence'])
            self.assertEqual(dict(model.authored.nodes()),model.authored.document['source']['nodes'])
            self.assertIn('source objects',model.authored.summary())
            self.assertIsNone(model.authored.scope)
