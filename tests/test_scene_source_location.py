import copy,time,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from test_runtime_scene_editor import package
from scene_editor_tests import source_location as source

PATH='/Game/Cinematics/Lumiere/Act03/AliciaAtelier/MCS_AliciaAtelier.MCS_AliciaAtelier'
WORLD=source.source_world(PATH)

class SourceLocationTests(unittest.TestCase):
    def document(self):return dict(source=dict(sequence=PATH,nodes={}),name='Draft',scene_position=[1,2,3],scene_yaw=90.,cast_edits=[{'keep':'edit'}])
    def test_original_placement_overrides_only_private_scene_offset(self):
        doc=self.document();before=copy.deepcopy(doc)
        with patch('scene_editor_tests.authored_preview.profile_for',return_value=NS(anchor=(10.,20.,30.))):r=source.destination(doc)
        self.assertEqual(doc,before);self.assertEqual(r['document']['scene_position'],[10.,20.,30.])
        self.assertEqual(r['document']['scene_yaw'],0.)
        self.assertEqual(r['document']['cast_edits'],before['cast_edits'])
    def test_missing_world_and_nonspatial_source_are_rejected_before_travel(self):
        doc=self.document();doc['source']['sequence']='/Game/Unknown.Unknown'
        with self.assertRaisesRegex(ValueError,'mapping'):source.destination(doc)
        with patch('scene_editor_tests.authored_preview.profile_for',return_value=NS(anchor=(0.,0.,0.))):
            with self.assertRaisesRegex(ValueError,'no decoded 3D'):source.destination(self.document())
    def test_route_rejects_missing_or_ambiguous_entrance(self):
        row={'asset_name':'Source','level_id':'Source','entrance_tag':'Main'}
        self.assertEqual(source.route_for('/Game/Levels/Source.Source',[row]),row)
        for rows in ([],[row,row]):
            with self.assertRaises(ValueError):source.route_for('/Game/Levels/Source.Source',rows)
    def editor(self,state='prepare'):
        r=dict(path=PATH,world=WORLD,anchor=(10.,20.,30.),document=self.document(),state=state,deadline=time.monotonic()+180)
        process=NS(_scene_source_trip=r)
        e=NS(session=NS(_session=process,pid=1),source_location_path=None,pending_authored=None,
             authored=NS(loading=None,graph={},source=PATH,close=Mock(return_value=True)),
             shared=Mock(),queue_authored=Mock(),queue_authored_preview=Mock(),message='')
        return e,r
    def test_cross_world_request_dispatches_once_and_uses_no_old_scope_on_arrival(self):
        e,r=self.editor();row={'asset_name':WORLD.rsplit('.',1)[1],'level_id':'Source','entrance_tag':'Main'}
        with patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world_path':'/Game/Elsewhere.Elsewhere'}),patch('expedition33.zone_travel.routes',return_value=[row]),patch('expedition33.zone_travel.travel_to_entrance') as travel:
            self.assertTrue(source.poll(e));self.assertEqual(r['state'],'traveling')
            source.poll(e);self.assertEqual(travel.call_count,2) # validation + one dispatch
            self.assertNotIn('session',r)
        new=NS(**vars(e));new.session=NS(_session=e.session._session,pid=1)
        with patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world_path':WORLD}):
            source.poll(new)
            self.assertEqual(r['state'],'importing');new.queue_authored.assert_called_once_with(PATH)
    def test_uncertain_travel_is_not_replayed(self):
        e,r=self.editor();row={'asset_name':WORLD.rsplit('.',1)[1]}
        with patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world_path':'other'}),patch('expedition33.zone_travel.routes',return_value=[row]),patch('expedition33.zone_travel.travel_to_entrance',side_effect=[None,RuntimeError('transport unknown')]) as travel:
            with self.assertRaises(RuntimeError):source.poll(e)
            self.assertEqual(r['state'],'unknown');source.poll(e);self.assertEqual(travel.call_count,2)
    def test_same_world_camera_visit_imports_and_opens_paused_timeline_without_travel(self):
        e,r=self.editor()
        with patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world_path':WORLD}),patch('expedition33.zone_travel.travel_to_entrance') as travel:
            source.poll(e);travel.assert_not_called()
            e.authored.graph={'valid':'source'};source.poll(e)
            self.assertEqual(r['state'],'complete');e.queue_authored_preview.assert_called_once_with(edited=True)
    def test_timeline_library_exposes_source_navigation_beside_load(self):
        from scene_editor_tests.timeline import TimelineView
        owner=NS(authored=NS(catalog=[{'path':PATH,'title':'Source'}]),go_to_source=Mock())
        preview=NS(sequence_timeline=True,owner=owner,editor=NS(workspace=owner.authored),message='Ready')
        view=TimelineView(None,preview);view.picker='sequences'
        frame=view.render();self.assertFalse(frame.controls[30].enabled)
        frame=view.activate(view.revision,19)
        self.assertEqual(frame.controls[30].label,'Go to source location')
        self.assertTrue(frame.controls[30].enabled)
        view.activate(view.revision,30);owner.go_to_source.assert_called_once_with(PATH)
    def test_source_visit_queues_preview_cleanup_before_world_actions(self):
        m=package.Mod();m.authored_preview=Mock()
        m.go_to_source(PATH)
        self.assertEqual(m.pending_source_visit,PATH)
        m.authored_preview.queue.assert_called_once_with('close')
        self.assertIsNone(m.pending_authored)

    def test_source_navigation_never_teleports_gameplay_pawn_to_cinematic_anchor(self):
        import inspect
        code=inspect.getsource(source)
        self.assertNotIn('K2_TeleportTo',code)
        self.assertNotIn('place_player',code)

    def test_world_retirement_requeues_only_import_not_map_travel(self):
        m=package.Mod();e,request=self.editor('importing')
        m.session=e.session;m.pending_authored=PATH
        m._revoke_world_intents()
        self.assertEqual(request['state'],'traveling');self.assertIsNone(m.pending_authored)

    def test_failed_import_opens_visible_feedback_and_preserves_original_reason(self):
        e,request=self.editor('importing');e.authored.graph=None
        e.message='Source import failed: source descriptor changed'
        with patch('expedition33.cinematics.original_game_action.controller_context',return_value={'world_path':WORLD}):source.poll(e)
        self.assertEqual(request['state'],'failed');self.assertTrue(e.want_open)
        self.assertIn('source descriptor changed',e.message)

    def test_import_in_progress_does_not_repeat_controller_discovery(self):
        e,request=self.editor('importing');e.pending_authored=PATH
        with patch('expedition33.cinematics.original_game_action.controller_context') as observe:source.poll(e)
        observe.assert_not_called();self.assertEqual(request['state'],'importing')

    def test_catalog_contains_only_explicit_world_identities(self):
        self.assertGreater(len(source._WORLDS),50)
        self.assertTrue(all(w.startswith('/Game/Levels/') and w.rsplit('.',1)[0].rsplit('/',1)[1]==w.rsplit('.',1)[1] for w in source._WORLDS.values()))

if __name__=='__main__':unittest.main()
