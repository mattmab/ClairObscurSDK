import unittest
import copy
from types import SimpleNamespace as N
from unittest.mock import Mock
from test_runtime_scene_editor import package
from scene_editor_tests.sequence_properties import SequenceProperties
from scene_editor_tests.timeline import TimelineView
from test_authored_timeline import fixture,SECTION


class SequencePropertiesTests(unittest.TestCase):
    def test_scene_yaw_is_editable_and_bounded_in_existing_property_panel(self):
        editor=SequenceProperties(fixture());editor.category_changed('scene');editor.select('origin')
        editor.move_property(1);self.assertEqual(editor.field(),('scene yaw (degrees)','0.0'))
        editor.edit('90');self.assertEqual(editor.document['scene_yaw'],90.)
        before=editor.document
        with self.assertRaises(ValueError):editor.edit('181')
        self.assertIs(editor.document,before)
    def test_open_section_bounds_can_be_set_together_without_an_invalid_intermediate_range(self):
        from expedition33.cinematics.authored_timeline import create
        graph=fixture()['source']
        bounds=graph['nodes'][SECTION]['fields']['SectionRange']['frame_range']
        bounds['lower']={'kind':'open','value':None}
        editor=SequenceProperties(create(graph,'Unbounded section'));editor.select(SECTION)
        self.assertEqual(editor.field(),('range (source ticks)','[null, 48000]'))
        before=editor.document
        for text in ('[null, 48000]','[true, 48000]','[1]','[1, 2, 3]','[48000, 0]'):
            with self.assertRaises(ValueError):editor.edit(text)
            self.assertIs(editor.document,before)
        editor.edit('[0, 48000]')
        self.assertEqual(editor.field(),('start (source ticks)','0'))
        self.assertEqual(editor.document['section_edits'][SECTION],dict(start=0,end=48000))
        self.assertEqual(editor.document['source'],before['source'])

    def test_shared_timeline_key_picker_preserves_source_and_rejects_neighbor_crossing(self):
        editor=SequenceProperties(fixture());source=copy.deepcopy(editor.document['source'])
        p=N(sequence_timeline=True,editor=editor,ready=True,playing=False,message='',queue=Mock())
        view=TimelineView(None,p);frame=view.render();frame=view.activate(frame.revision,14)
        frame=view.activate(frame.revision,19);frame=view.activate(frame.revision,11)
        self.assertEqual(editor.category,'keys');self.assertEqual(len(view.choices),2)
        frame=view.activate(frame.revision,19)
        frame=view.activate(frame.revision,27,value='500')
        frame=view.activate(frame.revision,30)
        frame=view.activate(frame.revision,27,value='12.5')
        self.assertEqual(editor.document['key_edits'],[dict(section=SECTION,path=['Translation',0],index=0,at=500,value=12.5)])
        self.assertEqual(editor.document['source'],source)
        self.assertFalse(next(c.enabled for c in frame.controls if c.token==15))
        p.scope=N(_session=N(_transport=N(authored_curve_patch_protocol=1)))
        frame=view.render()
        self.assertTrue(next(c.enabled for c in frame.controls if c.token==15))
        frame=view.activate(frame.revision,29);before=editor.document
        frame=view.activate(frame.revision,27,value='24000')
        self.assertIs(editor.document,before);self.assertIn('neighbor',view.sequence_error)
        frame=view.activate(frame.revision,28)
        self.assertEqual(editor.document['key_edits'],[])
        self.assertTrue(next(c.enabled for c in frame.controls if c.token==15))
        frame=view.activate(frame.revision,11)
        self.assertEqual(editor.category,'sections');self.assertEqual(editor.selected,SECTION)
        p.queue.assert_not_called()
    def test_boolean_key_field_roundtrips_json_and_rejects_numeric_substitution(self):
        from expedition33.cinematics.authored_timeline import create
        graph=fixture()['source'];curve=graph['nodes'][SECTION]['fields']['Translation']['static_array'][0]
        curve['struct']='/Script/MovieScene.MovieSceneBoolChannel'
        curve['fields']['Values']['array']=[True,False]
        editor=SequenceProperties(create(graph,'Boolean curve'));editor.select(SECTION);editor.open_keys()
        editor.select(editor.rows()[0][0]);editor.move_property(1)
        self.assertEqual(editor.field(),('value','true'));editor.edit('false')
        self.assertEqual(editor.field(),('value','false'));before=editor.document
        with self.assertRaisesRegex(ValueError,'Boolean'):editor.edit('1')
        self.assertIs(editor.document,before)
    def test_section_edits_keep_native_ticks_and_reject_invalid_ranges_atomically(self):
        editor=SequenceProperties(fixture());editor.select(SECTION)
        editor.edit('10');self.assertEqual(editor.document['section_edits'][SECTION]['start'],10)
        before=editor.document;editor.move_property(1)
        with self.assertRaises(ValueError):editor.edit('9')
        self.assertIs(editor.document,before)
        with self.assertRaises(ValueError):editor.edit('true')
    def test_shared_cast_properties_replace_position_and_restore_original(self):
        from test_authored_cast import fixture as cast_fixture
        from expedition33.cinematics.authored_timeline import create
        editor=SequenceProperties(create(cast_fixture(),'Cast'))
        editor.category_changed('cast');editor.select(editor.rows()[0][0]);editor.edit('sciel')
        editor.move_property(1);editor.edit('120.5')
        self.assertEqual(editor.document['cast_edits'][0]['placement']['offset'][0],120.5)
        editor.property_index=0;editor.edit('original');self.assertEqual(editor.document['cast_edits'],[])
    def test_npc_properties_and_existing_timeline_picker_share_document(self):
        workspace=package.Mod().authored;workspace.document=fixture()
        editor=SequenceProperties(workspace.document,workspace)
        p=N(sequence_timeline=True,editor=editor,ready=True,playing=False,message='',queue=Mock())
        view=TimelineView(None,p);frame=view.render();frame=view.activate(frame.revision,14)
        frame=view.activate(frame.revision,34);frame=view.activate(frame.revision,35)
        self.assertEqual(len(workspace.document['npc_tracks']),1)
        self.assertEqual(editor.field()[0],'name')
        frame=view.activate(frame.revision,27,value='Named NPC')
        self.assertEqual(workspace.document['npc_tracks'][0]['name'],'Named NPC')
        frame=view.activate(frame.revision,15);p.queue.assert_called_once_with('apply')
        frame=view.activate(frame.revision,28);self.assertEqual(workspace.document['npc_tracks'],[])
        with self.assertRaises(ValueError):editor.select('missing')
    def test_library_reports_npc_actions_and_hides_irrelevant_remove_control(self):
        editor=SequenceProperties(fixture())
        p=N(sequence_timeline=True,editor=editor,ready=True,playing=False,message='',queue=Mock())
        view=TimelineView(None,p);frame=view.render();frame=view.activate(frame.revision,14)
        self.assertEqual(frame.controls[28].label,'')
        frame=view.activate(frame.revision,34)
        frame=view.activate(frame.revision,31)
        self.assertIn('Sciel',frame.status)
        frame=view.activate(frame.revision,35)
        self.assertIn('NPC track added',frame.status)
        self.assertEqual(editor.document['npc_tracks'][0]['profile'],'sciel')
        frame=view.activate(frame.revision,28)
        self.assertIn('NPC removed',frame.status)
        self.assertFalse(frame.controls[28].enabled)
        frame=view.activate(frame.revision,32)
        frame=view.activate(frame.revision,19)
        self.assertNotIn('NPC removed',frame.status)
        self.assertTrue(all(len(line)<=50 for line in frame.controls[19].label.splitlines()))

    def test_npc_picker_exposes_all_character_blueprints_and_wraps(self):
        editor=SequenceProperties(fixture())
        p=N(sequence_timeline=True,editor=editor,ready=True,playing=False,message='',queue=Mock(),
            scope=N(_session=N(_transport=N(timeline_extended_characters_protocol=1))))
        view=TimelineView(None,p);frame=view.render();frame=view.activate(frame.revision,14)
        frame=view.activate(frame.revision,34)
        for label in ('Sciel','Verso','Maelle','Monoco'):
            frame=view.activate(frame.revision,31)
            self.assertIn(label,frame.status)
        self.assertEqual(frame.controls[35].label,'Add Monoco')
        frame=view.activate(frame.revision,35)
        self.assertEqual(editor.document['npc_tracks'][0]['profile'],'monoco')
        frame=view.activate(frame.revision,31)
        self.assertEqual(frame.controls[35].label,'Add Lune')

    def test_new_cast_profiles_can_be_staged_and_saved_in_timeline(self):
        from test_authored_cast import fixture as cast_fixture
        from expedition33.cinematics.authored_timeline import create,validate
        editor=SequenceProperties(create(cast_fixture(),'Cast'))
        editor.category_changed('cast');editor.select(editor.rows()[0][0])
        for profile in ('maelle','monoco'):
            editor.edit(profile)
            self.assertEqual(validate(editor.document)['cast_edits'][0]['profile'],profile)
        with self.assertRaises(ValueError):editor.edit('unreviewed')

    def test_closed_preview_returns_to_existing_editor_without_queuing_another_preview(self):
        model=package.Mod();model.session=object()
        model.shared=N(menu=None);view=N(closed=False,status='Preparing')
        model.native=N(menu=N(view=view),open=Mock())
        preview=N(error=None,restart_requested=True,restart_frame=125,poll=Mock(return_value=False))
        model.authored_preview=preview;model.poll()
        self.assertIs(model.authored_preview,preview);self.assertFalse(model.pending_authored_preview)
        preview.poll.return_value=True;model.poll()
        self.assertIsNone(model.authored_preview);self.assertFalse(model.pending_authored_preview)
        self.assertEqual(model.next_screen,'scene_authored_timeline')
        self.assertFalse(model.pending_authored_edited)
        self.assertTrue(view.closed)
        model.native.open.assert_called_once_with()
    def test_reopen_without_destination_preserves_page_and_updates_status_before_paint(self):
        model=package.Mod();model.session=object();model.want_open=True;model.message='Playback closed'
        view=N(closed=False,status='Preparing',screen='scene_authored_cast')
        model.shared=N(menu=None)
        def paint():
            self.assertEqual(view.status,'Playback closed')
            self.assertFalse(view.closed)
            self.assertEqual(view.screen,'scene_authored_cast')
        model.native=N(menu=N(view=view),open=Mock(side_effect=paint))
        model.poll();model.native.open.assert_called_once_with()


if __name__=='__main__':unittest.main()
