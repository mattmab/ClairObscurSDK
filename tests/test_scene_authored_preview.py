import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from contextlib import nullcontext
from test_runtime_scene_editor import package
from scene_editor_tests.authored_preview import AuthoredPreview,profile_for,position
from scene_editor_tests.timeline import TimelineView,TimelinePanel,TimelineMenu
from expedition33.cinematics.portable import PROFILES


class AuthoredPreviewTests(unittest.TestCase):
    def test_nonzero_yaw_rejects_older_runtime_before_creating_owners(self):
        from test_authored_timeline import fixture
        p=object.__new__(AuthoredPreview);p.document=fixture();p.document['scene_yaw']=90.
        p.play_scope=None;p.scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0)))
        with patch('expedition33.cinematics.authored_media.source',return_value=None),\
             patch('scene_editor_tests.authored_preview.SessionScope') as factory,\
             self.assertRaisesRegex(ValueError,'newer native transform'):
            p._prepare_playback()
        factory.assert_not_called()
    def test_movie_yaw_is_rejected_before_creating_owners(self):
        from test_authored_timeline import fixture
        p=object.__new__(AuthoredPreview);p.document=fixture();p.document['scene_yaw']=90.
        p.play_scope=None;p.scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=1)))
        with patch('expedition33.cinematics.authored_media.source',return_value={'movie':'baked'}),\
             patch('scene_editor_tests.authored_preview.SessionScope') as factory,\
             self.assertRaisesRegex(ValueError,'prerecorded'):
            p._prepare_playback()
        factory.assert_not_called()
    def test_numpad_typing_in_the_value_field_does_not_move_the_scene(self):
        p=object.__new__(AuthoredPreview)
        p.closed=False;p.pending=None;p.ready=True;p.playing=False;p.next_sample=float('inf')
        p.start_frame=0;p.end_frame=300;p.frame=100;p.subframe=0.;p.sequence=Mock();p.menu=Mock()
        p.menu.poll_scrub.return_value=None;p.flight=N(active=True)
        p.scope=N(pid=42,_session=N(_transport=N(_executable='reader',sequence_placement_input_protocol=1)))
        p.menu.panel._planner.prepare.return_value=N(invoke=lambda:nullcontext(N(return_value=True)))
        with patch('expedition33._sequence_flight.SequenceFlight') as flight,\
             patch('scene_editor_tests.sequence_viewport.nudge_scene') as nudge,\
             patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()):
            flight.return_value.inputs.return_value=(0,(0.,15.,0.))
            self.assertFalse(p.poll())
        nudge.assert_not_called();p.menu.set_sequence_shown.assert_not_called()
    def test_scrub_camera_restore_updates_flight_controls_without_rebinding(self):
        from expedition33.management_view import MenuFrame,MenuControl
        menu=object.__new__(TimelineMenu);menu._feedback_binding_frame=None
        menu.model=N(sequence_timeline=True,flight=None);menu.view=N(picker=False)
        menu.panel=Mock();menu.panel.labels=list(range(20));menu.refresh=Mock();menu._revoke=Mock()
        menu.frame=MenuFrame(7,'Timeline','',
            (MenuControl(17,'Exit flight view'),MenuControl(18,'Place whole scene here',True)),0,1,'',False)
        menu.sync_sequence_flight_controls()
        self.assertEqual(menu.frame.revision,7)
        self.assertEqual(menu.frame.controls[0].label,'Flight editor')
        self.assertFalse(menu.frame.controls[1].enabled)
        menu.panel.set_enabled.assert_any_call(1,False)
        menu.refresh.assert_not_called();menu._revoke.assert_not_called()
        menu.panel.reset_mock();menu.sync_sequence_flight_controls()
        menu.panel.set_text.assert_not_called();menu.panel.set_enabled.assert_not_called()
    def test_hidden_movie_timeline_keeps_owned_video_canvas_visible(self):
        menu=object.__new__(TimelineMenu);menu.model=N(media=object())
        panel=Mock();menu.panel=panel;panel.timeline_layer=object()
        menu.set_sequence_shown(False)
        panel._render_call.assert_any_call(panel.timeline_layer,'Widget','SetRenderOpacity',InOpacity=0.)
        self.assertFalse(any(c.args[0] is panel.canvas and c.args[2]=='SetRenderOpacity' for c in panel._render_call.call_args_list))
        menu.set_sequence_shown(True)
        panel._render_call.assert_any_call(panel.timeline_layer,'Widget','SetRenderOpacity',InOpacity=1.)
        self.assertFalse(menu.hidden)

    def test_pointer_scrub_seeks_and_syncs_without_rebinding_menu(self):
        p=object.__new__(AuthoredPreview)
        p.closed=False;p.pending=None;p.ready=True;p.playing=True;p.next_sample=float('inf');p.npcs=None
        p.start_frame=100;p.end_frame=300;p.frame=100;p.subframe=0.;p.sequence=Mock();p.menu=Mock()
        p.menu.poll_scrub.return_value=.375;p._sync_npcs=Mock(return_value=True)
        p.menu.panel.labels=[object() for _ in range(36)]
        p.scope=N(pid=42,_session=N(_transport=N(_executable='reader')))
        with patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()):p.poll()
        p.sequence.seek_frame.assert_called_once_with(175,0.)
        p._sync_npcs.assert_called_once();self.assertFalse(p.playing)
        p.menu.refresh.assert_not_called();p.menu.draw_tracks.assert_called_once()

    def test_start_rewinds_and_plays_instead_of_only_seeking(self):
        p=object.__new__(AuthoredPreview)
        p.closed=False;p.pending='start';p.ready=True;p.playing=False;p.next_sample=float('inf');p.npcs=None
        p.start_frame=93;p.end_frame=2174;p.frame=800;p.subframe=.5;p.sequence=Mock();p.menu=Mock()
        p.scope=N(pid=42,_session=N(_transport=N(_executable='reader')))
        with patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()):p.poll()
        p.sequence.seek_frame.assert_called_once_with(93,0.)
        p.sequence.play.assert_called_once();self.assertTrue(p.playing)

    def test_edit_only_play_prepares_player_without_replacing_the_menu(self):
        from test_authored_timeline import fixture
        p=object.__new__(AuthoredPreview);p.editor=N(document=fixture());p.playback_available=lambda:True
        p.scope=N(_session=N(_transport=N()));p.frame=42;p.subframe=.25;p.menu=Mock();menu=p.menu
        p.editing_only=True;p._prepare_playback=Mock()
        with patch('scene_editor_tests.authored_preview.profile_for',return_value=N()) as profile,patch('expedition33._timeline_actor_channel.validate_count'):
            p._promote_playback()
        profile.assert_called_once_with(p.editor.document)
        self.assertFalse(p.editing_only);self.assertIs(p.menu,menu)
        self.assertEqual(p.initial_frame,42);self.assertEqual(p.initial_subframe,.25)

    def test_scene_world_position_edits_preserve_original_source(self):
        from test_authored_timeline import fixture
        from scene_editor_tests.sequence_properties import SequenceProperties
        editor=SequenceProperties(fixture());source=editor.document['source_sha256']
        editor.category_changed('scene');editor.select('origin');editor.edit('[1200, -400, 800]')
        self.assertEqual(editor.document['scene_position'],[1200,-400,800])
        self.assertEqual(editor.document['source_sha256'],source)
        with self.assertRaises(ValueError):editor.edit('[1, 2]')
        self.assertEqual(editor.document['scene_position'],[1200,-400,800])
        editor.edit('null');self.assertIsNone(editor.document['scene_position'])

    def test_unadapted_source_opens_existing_timeline_without_building_playback(self):
        from test_authored_timeline import fixture
        session=N(_session=N(_transport=N()))
        with patch('scene_editor_tests.authored_preview.SessionScope'), \
             patch('scene_editor_tests.authored_preview.profile_for',side_effect=AssertionError('Playback projection must be deferred')):
            preview=AuthoredPreview(session,fixture(),edited=True,editing_only=True)
        preview.scope=N(pid=42,_session=N(_transport=N(_executable='reader')))
        preview._prepare_playback=Mock()
        with patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()), \
             patch('scene_editor_tests.timeline.TimelineMenu') as menu:
            preview.prepare()
        self.assertTrue(preview.ready)
        self.assertIsNone(preview.sequence)
        preview._prepare_playback.assert_not_called()
        self.assertEqual(preview.menu.view.picker,'sequence')
        preview.queue('toggle');self.assertFalse(preview.poll())
        self.assertFalse(preview.playing)
        preview.editor.workspace.save=Mock()
        preview.queue('save');self.assertFalse(preview.poll())
        preview.editor.workspace.save.assert_called_once()
        self.assertIn('Edit mode',preview.detail())
        view=TimelineView(None,preview)
        frame=view.render()
        self.assertFalse(frame.controls[8].enabled)
        self.assertTrue(frame.controls[9].enabled)
        self.assertTrue(frame.controls[14].enabled)
        self.assertFalse(frame.controls[15].enabled)

    def test_dense_source_tracks_cannot_hide_audio_npc_or_selected_markers(self):
        from scene_editor_tests.timeline import visible_sequence_rows
        rows=[dict(key=str(i),lane='source') for i in range(200)]
        rows += [dict(key='audio',lane='audio'),dict(key='npc',lane='npc')]
        shown=visible_sequence_rows(rows,80,'199')
        self.assertEqual(len(shown),80)
        self.assertEqual({row['lane'] for row in shown},{'source','audio','npc'})
        self.assertIn('199',{row['key'] for row in shown})
        self.assertEqual(rows[0]['key'],'0')
        self.assertEqual(visible_sequence_rows(rows,0),[])

    def test_timeline_layer_restores_resolved_outer_canvas_after_mid_build_flush(self):
        from expedition33._ui_construction import Construction, Pending
        panel=object.__new__(TimelinePanel)
        recipe=Construction()
        panel.canvas=recipe.record('tree','spawn',{}).return_value
        panel._spawn=Mock(return_value=recipe.record('tree','spawn',{}).return_value)
        panel._place=Mock(return_value='slot');panel.anchor=Mock()
        outer=N(index=1);layer=N(index=2)
        def build_contents():
            self.assertIsInstance(panel.timeline_outer_canvas,Pending)
            recipe.results.update({0:outer,1:layer})
            for name,value in tuple(vars(panel).items()):
                setattr(panel,name,recipe.resolve(value))
        panel._build_timeline_contents=build_contents
        panel._build_contents()
        self.assertIs(panel.canvas,outer)
        self.assertIs(panel.timeline_layer,layer)

    def test_frame_field_uses_toolbar_and_library_restores_property_editor(self):
        panel=object.__new__(TimelinePanel)
        panel.field=N(index=1);panel.field_back=N(index=2)
        panel.placements={1:'field-slot',2:'back-slot'}
        panel.anchor=Mock();panel._render_call=Mock()
        panel.layout_sequence_field(False)
        panel.anchor.assert_any_call('field-slot',.72,.78,render=True)
        self.assertEqual(panel._render_call.call_args_list[0].kwargs['InSize'],dict(X=200,Y=42))
        panel.layout_sequence_field(False)
        self.assertEqual(panel.anchor.call_count,2)
        panel.layout_sequence_field(True)
        panel.anchor.assert_any_call('field-slot',.415,.495,render=True)
        self.assertEqual(panel._render_call.call_args_list[2].kwargs['InSize'],dict(X=1000,Y=42))

    def test_seek_field_keeps_fraction_and_does_not_replace_an_in_progress_entry(self):
        menu=object.__new__(TimelineMenu)
        menu.model=N(sequence_timeline=True,frame=742,subframe=.75,editor=None)
        menu.panel=Mock(count=0,labels=[])
        menu.panel.library_panes=[]
        menu.frame=N(controls=[]);menu.view=N(picker=None)
        menu._paint_panel()
        menu.panel.set_field.assert_called_once_with('742.75')
        menu.model.frame=800;menu._paint_panel()
        menu.panel.set_field.assert_called_once_with('742.75')
        menu.view.picker='sequence';menu.model.editor=Mock(revision=1)
        menu.model.editor.field.return_value=('key','0.125')
        menu._paint_panel()
        self.assertEqual(menu.panel.set_field.call_args.args,('0.125',))

    def test_editor_return_keeps_open_request_until_process_ui_is_ready(self):
        model=package.Mod();model.session=object()
        model.runtime=Mock(scope=None,authoring=False)
        model.shared=N(ui_ready=False,menu=None);model.native=Mock()
        model.want_open=True
        model.poll()
        self.assertTrue(model.want_open);model.native.open.assert_not_called()
        model.shared.ui_ready=True
        model.poll()
        self.assertFalse(model.want_open);model.native.open.assert_called_once()

    def test_observed_playback_stop_updates_detail_without_closing_editable_timeline(self):
        preview=object.__new__(AuthoredPreview)
        preview.closed=False;preview.pending=None;preview.ready=True;preview.playing=True
        preview.next_sample=0.;preview.npcs=None;preview.menu=Mock();preview.message='Playing'
        preview.scope=N(pid=42,_session=N(_transport=N(_executable='reader')))
        preview.sequence=Mock()
        current={'Time':{'FrameNumber':{'Value':2173},'SubFrame':.999}}
        preview.sequence._call.side_effect=lambda name:current if name=='GetCurrentTime' else False
        with patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()):
            self.assertFalse(preview.poll())
        self.assertFalse(preview.playing)
        self.assertEqual(preview.message,'Stopped; timeline remains editable')
        self.assertTrue(preview.ready)
        preview.menu.close.assert_not_called();preview.sequence.close.assert_not_called()
        preview.menu.refresh.assert_called_once()

    def test_original_preview_projects_source_without_applying_or_discarding_saved_edits(self):
        from test_authored_timeline import fixture,SECTION
        from expedition33.cinematics.authored_timeline import retime,set_npc
        document=retime(fixture(),SECTION,100,47000)
        document=set_npc(document,'a'*32,name='Extra actor',profile='lune',start=0,end=300,offset=[0.,0.,0.],yaw=0.)
        session=N(_session=N(_transport=N(sequence_seek_protocol=1)))
        with patch('scene_editor_tests.authored_preview.profile_for',return_value=next(iter(PROFILES.values()))),\
             patch('scene_editor_tests.authored_preview.available',return_value=True),\
             patch('scene_editor_tests.authored_preview.SessionScope'):
            preview=AuthoredPreview(session,document)
        self.assertEqual(preview.document['source'],document['source'])
        self.assertEqual(preview.document['section_edits'],{})
        self.assertEqual(preview.document['npc_tracks'],[])
        self.assertEqual(preview.editor.document,document)
        self.assertEqual(document['section_edits'][SECTION]['start'],100)
    def test_apply_reuses_exact_panel_and_waits_for_player_cleanup(self):
        preview=object.__new__(AuthoredPreview);preview.menu=Mock();menu=preview.menu
        preview._rebuilding=True;preview._rebuild_document={'name':'Changed'};preview.restart_frame=125;preview.restart_subframe=.75
        preview.scope=N(pid=42,_session=N(_transport=N(_executable='reader')))
        preview._close_player=Mock(side_effect=(False,True));preview._prepare_playback=Mock()
        with patch('scene_editor_tests.authored_preview.shared_operation',side_effect=lambda *a,**kw:nullcontext()) as worker:
            self.assertFalse(preview._apply_rebuild());preview._prepare_playback.assert_not_called()
            self.assertIs(preview.menu,menu);self.assertTrue(preview._rebuilding)
            self.assertFalse(preview._apply_rebuild())
            self.assertEqual(worker.call_count,2)
        self.assertIs(preview.menu,menu);menu.close.assert_not_called();menu.prepare.assert_not_called()
        self.assertEqual(preview.initial_frame,125);self.assertTrue(preview.edited)
        self.assertEqual(preview.initial_subframe,.75)
        preview._prepare_playback.assert_called_once();self.assertFalse(preview._rebuilding)
    def test_playback_child_releases_before_root_menu_and_keeps_deferred_scope(self):
        preview=object.__new__(AuthoredPreview);preview.npcs=None;preview.sequence=Mock();preview.services=Mock()
        preview.play_scope=object();scope=preview.play_scope;preview.menu=Mock();preview.playing=True
        with patch('scene_editor_tests.authored_preview.close_lease_only_scope',side_effect=(False,True)) as close:
            self.assertFalse(preview._close_player());self.assertIs(preview.play_scope,scope)
            preview.menu.close.assert_not_called();self.assertTrue(preview._close_player())
            self.assertIsNone(preview.play_scope);self.assertEqual(close.call_count,2)
    def test_rebuilt_fraction_reaches_native_seek_and_npc_interval_evaluation(self):
        for initial,expected in ((742,(742,.75)),(2174,(2173,0.)),(2200,(2173,0.)),(-1,(93,0.))):
            with self.subTest(initial=initial):
                preview=object.__new__(AuthoredPreview)
                preview.scope=N(pid=99,_session=N(_transport=N(_executable='reader')))
                preview.play_scope=None;preview.edited=True
                preview.document={'source':{'nodes':{}},'cast_edits':[],'npc_tracks':[{'fixture':'NPC'}]}
                preview.initial_frame=initial;preview.initial_subframe=.75
                preview.profile=N(anchor=(0.,0.,0.),sequence='/Game/Reviewed.Reviewed')
                preview.menu=Mock();preview.menu.panel.tree='tree'
                player=Mock();npcs=Mock();npcs.sync.return_value=True
                player._call.side_effect=lambda name:dict(Time=dict(FrameNumber=dict(Value=93 if name=='GetCurrentTime' else 2174)),Rate=dict(Numerator=30,Denominator=1))
                with patch('scene_editor_tests.authored_preview.SessionScope',return_value='play-scope'),\
                     patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()),\
                     patch('expedition33.simon_portable._snapshot',return_value=('context',None,(0.,0.,0.))),\
                     patch('expedition33.cinematics.controller_anchor.context_observer',return_value=lambda:'context'),\
                     patch('expedition33.cinematics.authored_copy.duplicate',return_value='copy'),\
                     patch('expedition33.cinematics.authored_copy.apply_key_edits'),\
                     patch('expedition33.cinematics.authored_copy.apply_section_edits'),\
                     patch('scene_editor_tests.authored_preview.OwnedSequenceContext'),\
                     patch('scene_editor_tests.authored_preview.OwnedLevelSequence',return_value=player),\
                     patch('expedition33.cinematics.blueprint_npc_tracks.BlueprintNpcTracks') as npc_type:
                    npc_type._from_snapshot.return_value=npcs
                    preview._prepare_playback()
                player.seek_frame.assert_called_once_with(*expected)
                npcs.sync.assert_called_once_with(sum(expected))
                self.assertEqual((preview.frame,preview.subframe),expected)
                self.assertTrue(preview.ready)
    def test_shared_panel_moves_cursor_without_repainting_unchanged_tracks(self):
        panel=object.__new__(TimelinePanel)
        panel.title=object();panel.detail=object();panel.playhead_slot=object()
        panel.set_text=Mock();panel.anchor=Mock();panel._render_call=Mock()
        panel.scrubber=object();panel.scrub_value=None;panel._paint_queue=None
        panel._planner=Mock();panel._function=Mock()
        panel._planner.prepare.return_value.invoke.return_value.__enter__=Mock(return_value=N(return_value=(100.25-93)/(2174-93)))
        panel._planner.prepare.return_value.invoke.return_value.__exit__=Mock(return_value=False)
        panel.markers=[(object(),object())];panel.clip_names=[object()]
        panel.track_labels=[(object(),'ANIM'),(object(),'AUDIO'),(object(),'CAM')]
        panel.rulers=[object()];panel.last_draw=None;panel.invisible=4;panel.collapsed=1
        model=N(start_frame=93,end_frame=2174,frame=100,subframe=.25,rate=(30,1),
                profile=N(saved_id='SimonIntro'),edited=True,document={'npc_tracks':[]},detail=lambda:'Frame')
        panel._draw_sequence(model);paint_count=panel._render_call.call_count
        model.frame=200;panel._draw_sequence(model)
        self.assertEqual(panel._render_call.call_count,paint_count)  # Only the separate playhead moves.
        self.assertEqual(panel.anchor.call_count,2)
        self.assertNotEqual(panel.anchor.call_args_list[0],panel.anchor.call_args_list[1])
    def test_playhead_paint_preserves_unread_mouse_drag(self):
        panel=object.__new__(TimelinePanel)
        panel.scrubber=object();panel.scrub_value=.2;panel._paint_queue=[]
        panel._function=Mock();panel._render_call=Mock();panel._planner=Mock()
        panel._planner.prepare.return_value.invoke.return_value=nullcontext(N(return_value=.7))
        panel.position_scrub(.21)
        panel._render_call.assert_not_called()
        panel._planner.prepare.assert_not_called()  # No read/write window for a later drag to race.
        self.assertEqual(panel.scrub_value,.2)
        panel._planner.prepare.return_value.invoke.return_value=nullcontext(N(return_value=.7))
        self.assertEqual(panel.read_scrub(),.7)
    def test_sequence_projection_cache_follows_applied_document_and_rate(self):
        panel=object.__new__(TimelinePanel)
        first={'source':'first'};second={'source':'second'}
        model=N(rate=(30,1),projection_snapshot=True)
        rows=({'path':'shot'},)
        with patch('scene_editor_tests.sequence_projection.project_sections',return_value=(rows,())) as project:
            self.assertEqual(panel._sequence_projection(model,first),(rows,None))
            self.assertEqual(panel._sequence_projection(model,first),(rows,None))
            self.assertEqual(project.call_count,1)
            self.assertEqual(panel._sequence_projection(model,second),(rows,None))
            self.assertEqual(project.call_count,2)
            model.rate=(24,1);panel._sequence_projection(model,second)
            self.assertEqual(project.call_count,3)
            model.projection_snapshot=False
            panel._sequence_projection(model,second);panel._sequence_projection(model,second)
            self.assertEqual(project.call_count,5)
    def test_sequence_projection_cache_preserves_omission_and_error_feedback(self):
        panel=object.__new__(TimelinePanel);model=N(rate=(30,1),projection_snapshot=True)
        first={'source':'first'};second={'source':'second'}
        with patch('scene_editor_tests.sequence_projection.project_sections',side_effect=[((),('unsupported shot',)),ValueError('Bad source')]) as project:
            self.assertEqual(panel._sequence_projection(model,first),((), '1 shot mappings unavailable; see source properties'))
            self.assertEqual(panel._sequence_projection(model,first),((), '1 shot mappings unavailable; see source properties'))
            self.assertEqual(panel._sequence_projection(model,second),((), 'Bad source'))
            self.assertEqual(panel._sequence_projection(model,second),((), 'Bad source'))
            self.assertEqual(project.call_count,2)
    def test_npc_transition_pauses_before_construction_and_waits_for_cleanup_ack(self):
        preview=object.__new__(AuthoredPreview)
        preview.frame=10;preview.subframe=0.;preview.playing=True
        preview.npcs=Mock();preview.npcs.needs_sync.return_value=True;preview.npcs.sync.side_effect=(False,True)
        preview.sequence=Mock();preview.sequence._call.return_value={'Time':{'FrameNumber':{'Value':11},'SubFrame':.25}}
        self.assertFalse(preview._sync_npcs());self.assertFalse(preview.playing)
        preview.sequence.pause.assert_called_once();preview.sequence.play.assert_not_called()
        preview.npcs.sync.assert_called_once_with(11.25)
        self.assertTrue(preview._sync_npcs());preview.sequence.play.assert_not_called()
    def test_bound_actor_retirement_follows_native_consumer_ack(self):
        preview=object.__new__(AuthoredPreview);preview.pending=None;preview.ready=True;preview.closed=False;preview.scope=object()
        events=[];preview.sequence=Mock();preview.services=None;preview.menu=None
        preview.sequence.owner.retire_world.side_effect=lambda:events.append('consumer') or True
        actor=Mock();actor.retire_world.side_effect=lambda:events.append('actor') or True
        preview.replacements=(actor,);preview.sequence.retire_world.side_effect=lambda **kw:events.append('scope') or True
        with patch('scene_editor_tests.authored_preview.close_lease_only_scope',return_value=True):self.assertEqual(preview.retire_world(),'ack')
        self.assertEqual(events,['consumer','actor','scope']);actor.close.assert_not_called()
    def test_bound_actor_close_retries_deferred_cleanup_before_scope_close(self):
        preview=object.__new__(AuthoredPreview);preview.sequence=Mock();preview.services=None;preview.play_scope=None
        preview.npcs=None;preview.replacements=(Mock(),);preview.flight=None;preview.media=None
        events=[];player=preview.sequence;actor=preview.replacements[0]
        player.owner.close.side_effect=lambda:events.append('consumer') or True
        actor.close.side_effect=[False,True]
        player.close.side_effect=lambda:events.append('scope')
        self.assertFalse(preview._close_player())
        self.assertIs(preview.sequence,player);player.close.assert_not_called()
        self.assertTrue(preview._close_player())
        self.assertEqual(events,['consumer','consumer','scope'])
        self.assertEqual(actor.close.call_count,2)
        self.assertIsNone(preview.sequence)
    def test_partial_cast_prepare_is_retained_through_world_retirement(self):
        preview=object.__new__(AuthoredPreview)
        preview.scope=N(pid=99,_session=N(_transport=N(_executable='reader')))
        preview.play_scope=None;preview.edited=True;preview.pending=None;preview.ready=False;preview.closed=False
        preview.document={'source':{'nodes':{}},'cast_edits':[{'profile':'sciel'}]}
        preview.profile=N(anchor=(0.,0.,0.),sequence='/Game/Reviewed.Reviewed')
        preview.menu=Mock();preview.menu.panel.tree='owned-tree';preview.npcs=None
        player=Mock();actor=Mock();events=[]
        def failed_apply(sequence,document,anchor,yaw,*,owners,latency):
            self.assertIs(latency,preview.latency)
            owners.append(actor)
            raise RuntimeError('binding failed')
        with patch('scene_editor_tests.authored_preview.SessionScope',return_value='play-scope'), \
             patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()), \
             patch('expedition33.simon_portable._snapshot',return_value=('context',None,(0.,0.,0.))), \
             patch('scene_editor_tests.authored_preview.OwnedSequenceContext'), \
             patch('scene_editor_tests.authored_preview.OwnedLevelSequence',return_value=player), \
             patch('expedition33.cinematics.authored_replacement._apply_snapshot',side_effect=failed_apply):
            with self.assertRaisesRegex(RuntimeError,'binding failed'):preview._prepare_playback()
        self.assertEqual(preview.replacements,[actor])
        player.owner.retire_world.side_effect=lambda:events.append('consumer') or True
        actor.retire_world.side_effect=lambda:events.append('actor') or True
        player.retire_world.side_effect=lambda **kw:events.append('scope') or True
        preview.services=None;preview.menu=None
        with patch('scene_editor_tests.authored_preview.close_lease_only_scope',return_value=True):
            self.assertEqual(preview.retire_world(),'ack')
        self.assertEqual(events,['consumer','actor','scope'])
    def test_edited_preview_is_explicit_and_never_silently_ignores_curve_edits(self):
        model=package.Mod();model.authored.document=self.document()
        model.queue_authored_preview(edited=True)
        self.assertTrue(model.pending_authored_preview);self.assertTrue(model.pending_authored_edited)
        model.pending_authored_preview=False;model.authored.document['key_edits']=[{'index':0}]
        with self.assertRaisesRegex(ValueError,'curve-key playback capability'):model.queue_authored_preview(edited=True)
        self.assertFalse(model.pending_authored_preview)
        model.queue_authored_preview();self.assertFalse(model.pending_authored_edited)
        with patch('expedition33.cinematics.authored_timeline.validate',return_value=model.authored.document),\
             patch('scene_editor_tests.authored_preview.SessionScope') as scope:
            with self.assertRaisesRegex(ValueError,'curve-key playback capability'):AuthoredPreview(Mock(),model.authored.document,edited=True)
        scope.assert_not_called()
    def test_private_keys_and_sections_finish_before_player_creation(self):
        self.check_private_edit_preparation(with_keys=True)

    def test_section_only_preview_skips_empty_curve_application(self):
        self.check_private_edit_preparation(with_keys=False)

    def test_movie_activity_suppression_skips_empty_key_and_range_passes(self):
        self.check_private_edit_preparation(with_keys=False,movie_only=True)

    def check_private_edit_preparation(self,*,with_keys,movie_only=False):
        preview=object.__new__(AuthoredPreview);preview.scope=N(pid=99,_session=N(_transport=N(_executable='reader')))
        preview.play_scope=None;preview.edited=True;preview.document={'source':{'nodes':{}},'section_edits':{'fixture':{}},'key_edits':[{'fixture':True}] if with_keys else []}
        if movie_only:
            preview.document['section_edits']={}
            preview.scope._session._transport.media_seek_protocol=1
        preview.profile=N(anchor=(0.,0.,0.),sequence='/Game/Reviewed.Reviewed')
        preview.menu=N(panel=N(tree='owned-tree'));events=[]
        player=Mock();player.build.side_effect=lambda *args,**kwargs:(_ for _ in ()).throw(RuntimeError('player boundary'))
        def keys(*args):events.append('keys')
        def sections(*args):events.append('sections')
        with patch('scene_editor_tests.authored_preview.SessionScope',return_value='play-scope'),\
             patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()),\
             patch('expedition33.simon_portable._snapshot',return_value=('context',None,(0.,0.,0.))),\
             patch('expedition33.cinematics.authored_copy.duplicate',return_value='private-copy'),\
             patch('expedition33.cinematics.authored_copy.apply_key_edits',side_effect=keys) as apply_keys,\
             patch('expedition33.cinematics.authored_copy.apply_section_edits',side_effect=sections),\
             patch('expedition33.cinematics.authored_media.source',return_value='/Game/Movie.Movie' if movie_only else None),\
             patch('expedition33.cinematics.authored_media.playback_document',return_value=preview.document),\
             patch('expedition33.cinematics.authored_media.suppression_sections',return_value=('movie-spawn',)),\
             patch('expedition33.cinematics.authored_activity.disable_sections') as suppress,\
             patch('scene_editor_tests.authored_preview.OwnedSequenceContext'),\
             patch('scene_editor_tests.authored_preview.OwnedLevelSequence',return_value=player):
            with self.assertRaisesRegex(RuntimeError,'player boundary'):preview._prepare_playback()
        self.assertEqual(events,[] if movie_only else ['keys','sections'] if with_keys else ['sections'])
        if with_keys:apply_keys.assert_called_once_with('play-scope','private-copy','owned-tree',preview.document)
        else:apply_keys.assert_not_called()
        if movie_only:suppress.assert_called_once_with('play-scope','private-copy','owned-tree',preview.document,('movie-spawn',))
        self.assertEqual(player.build.call_args.kwargs['asset'],'private-copy')
    def test_unsupported_movie_runtime_rejects_before_allocating_playback_scope(self):
        preview=object.__new__(AuthoredPreview)
        preview.play_scope=None;preview.document={}
        preview.scope=N(_session=N(_transport=N(media_seek_protocol=0)))
        with patch('expedition33.cinematics.authored_media.source',return_value='/Game/Movie.Movie'),patch('scene_editor_tests.authored_preview.SessionScope') as scope:
            with self.assertRaisesRegex(ValueError,'media Seek runtime'):preview._prepare_playback()
        scope.assert_not_called();self.assertIsNone(preview.play_scope)

    def test_movie_opening_preserves_transport_request_without_starting_audio(self):
        preview=object.__new__(AuthoredPreview)
        preview.closed=False;preview.pending='start';preview.ready=True;preview.editing_only=False
        preview.sequence=Mock();preview._sync_media=Mock(return_value=False)
        self.assertFalse(preview.poll())
        self.assertEqual(preview.pending,'start');preview.sequence.play.assert_not_called()
    def test_movie_cleanup_deferral_preserves_player_scope_and_parent_ui(self):
        preview=object.__new__(AuthoredPreview)
        preview.media=Mock();preview.media.close.return_value=False
        preview.sequence=Mock();preview.services=Mock();preview.play_scope=object();preview.menu=Mock()
        scope=preview.play_scope
        self.assertFalse(preview._close_player())
        self.assertIs(preview.play_scope,scope)
        preview.sequence.close.assert_not_called();preview.menu.close.assert_not_called()

    def test_frame_field_reads_return_value_and_releases_result(self):
        panel=object.__new__(TimelinePanel);panel.field=object();panel._function=Mock(return_value='GetText')
        result=Mock();result.__enter__=Mock(return_value=N(return_value='600.25'));result.__exit__=Mock(return_value=False)
        panel._planner=Mock();panel._planner.prepare.return_value.invoke.return_value=result
        self.assertEqual(panel.read_field(),'600.25');result.__exit__.assert_called_once()
    def document(self):return dict(source=dict(sequence=next(iter(PROFILES.values())).sequence))
    def test_only_exact_reviewed_source_paths_select_an_adapter(self):
        self.assertIsNotNone(profile_for(self.document()))
        self.assertIsNone(profile_for(None));self.assertIsNone(profile_for(dict(source=dict(sequence='/Game/Other.Other'))))
        self.assertEqual(position('-0.25'),(-1,.75));self.assertEqual(position('300.25'),(300,.25))
        for text in ('true','null','[1,2]','NaN','1e309','2147483648'):
            with self.assertRaises(ValueError):position(text)
    def test_pending_close_overrides_other_toolbar_intents(self):
        preview=object.__new__(AuthoredPreview);preview.pending=None
        preview.queue('forward');preview.queue('close');preview.queue('toggle')
        self.assertEqual(preview.pending,'close')
        with self.assertRaises(ValueError):preview.queue('execute')
    def test_sequence_uses_existing_timeline_controls_and_rejects_stale_input(self):
        preview=N(sequence_timeline=True,profile=N(saved_id='SimonIntro'),message='Ready',ready=True,playing=False,queue=Mock())
        view=TimelineView(None,preview);frame=view.render()
        self.assertEqual(len(frame.controls),36)
        self.assertEqual(next(c.label for c in frame.controls if c.token==8),'Play')
        view.activate(frame.revision,0);preview.queue.assert_called_once_with('seek')
        with self.assertRaises(RuntimeError):view.activate(frame.revision,8)
        with self.assertRaises(RuntimeError):view.activate(view.revision,True)
    def test_normal_close_is_sequence_services_then_menu_and_preserves_deferral(self):
        from expedition33._sequence_owner import SequenceCleanupDeferred
        preview=object.__new__(AuthoredPreview);preview.pending=None;preview.ready=True;preview.closed=False
        preview.scope=object();events=[]
        preview.sequence=N(close=Mock(side_effect=SequenceCleanupDeferred('deferred')))
        preview.services=N(close=lambda:events.append('services'))
        preview.menu=N(_accept_input=True,close=lambda:events.append('menu') or True)
        self.assertFalse(preview.close());self.assertEqual(events,[]);self.assertEqual(preview.pending,'close')
        preview.sequence.close=Mock(side_effect=lambda:events.append('sequence'))
        with patch('scene_editor_tests.authored_preview.close_lease_only_scope',return_value=True):self.assertTrue(preview.close())
        self.assertEqual(events,['sequence','services','menu']);self.assertTrue(preview.closed)
    def test_retirement_never_uses_normal_close_and_retains_unacknowledged_owner(self):
        preview=object.__new__(AuthoredPreview);preview.pending='seek';preview.ready=True;preview.closed=False;preview.scope=object()
        sequence=Mock();sequence.retire_world.return_value=False
        preview.sequence=sequence;preview.services=Mock();preview.menu=Mock()
        self.assertEqual(preview.retire_world(),'deferred');self.assertIs(preview.sequence,sequence)
        preview.services.retire_world.assert_not_called();sequence.close.assert_not_called()
        sequence.retire_world.return_value=True;preview.services.retire_world.return_value=True;preview.menu.retire_world.return_value='ack'
        with patch('scene_editor_tests.authored_preview.close_lease_only_scope',return_value=True):self.assertEqual(preview.retire_world(),'ack')
        self.assertTrue(preview.closed);sequence.close.assert_not_called()
    def test_editor_queues_preview_without_entering_game_and_end_closes_it(self):
        model=package.Mod();model.authored.document=self.document();model.queue_authored_preview()
        self.assertTrue(model.pending_authored_preview);self.assertIsNone(model.authored_preview)
        with self.assertRaises(ValueError):model.queue_authored_preview()
        model.authored_preview=N(queue=Mock());self.assertEqual(model.stop(),'Closing authored preview')
        model.authored_preview.queue.assert_called_once_with('close');self.assertFalse(model.pending_authored_preview)
