import importlib
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
import test_story_packs
from expedition33.management import ManagementError
StoryView=importlib.import_module('story_packs_test.view').StoryView

class StoryViewTests(unittest.TestCase):
    def test_warm_graph_paint_has_no_reader_process_startup(self):
        from unittest.mock import patch
        view=object.__new__(StoryView);view.screen='story_graph'
        with patch('expedition33._reader.shared_operation') as reader:
            with view.paint_operation(N(story_skin_ready=True)):pass
            reader.assert_not_called()

    def setUp(self):
        pack=test_story_packs.sample();self.request=dict(token=('save',1),world='map',visit=(1,),stories=())
        self.model=N(live=N(choices=lambda:self.request,error=None,choose=Mock()),
            library=N(packs={pack['id']:pack},get=lambda key:pack if key==pack['id'] else None),
            create_sample=lambda:pack['id'],place_boy=Mock(),edit_pack=Mock(),
            place_character=Mock(),move_placement_here=Mock(),character_profiles=lambda:('faceless-boy','lune'))
        self.view=StoryView(N(_check=lambda:None),self.model)
    def control(self,frame,label):return next(c for c in frame.controls if c.label.startswith(label))
    def test_selection_requires_confirmation_and_stale_frame_is_rejected(self):
        frame=self.view.render();select=self.control(frame,'Faceless Boy')
        updated=self.view.activate(frame.revision,select.token)
        self.model.live.choose.assert_not_called()
        with self.assertRaises(ManagementError):self.view.activate(frame.revision,select.token)
        confirm=self.control(updated,'Confirm:')
        self.view.activate(updated.revision,confirm.token)
        self.model.live.choose.assert_called_once_with(self.request,'sdk.faceless-boy-sample')
    def test_back_closes_workspace_without_rendering_closed_presenter(self):
        frame=self.view.render();back=self.control(frame,'Back')
        self.assertTrue(self.view.activate(frame.revision,back.token).closed)

    def test_selected_pack_controls_stay_in_right_inspector(self):
        frame=self.open_pack()
        for label in ('Confirm:','Saved placements','Open conversation graph','Place a character'):
            self.assertIn(self.control(frame,label).token,range(56,64))
        self.assertTrue(all(c.token>=48 or c.label.startswith(('Original game','> Faceless Boy')) for c in frame.controls if c.label))

    def test_fine_placement_controls_are_on_right_and_use_selected_actor(self):
        pack=self.model.library.get('sdk.faceless-boy-sample')
        pack['placements']=[dict(id='boy-here',world='/Game/Test.Test',position=[1,2,3],yaw=0,character='boy',dialogue='first-meeting',requires={})]
        self.model.nudge_placement=Mock()
        frame=self.click(self.click(self.click(self.open_pack(),'Saved placements'),'boy-here |'),'Fine placement controls')
        self.assertIn(self.control(frame,'X +').token,range(56,64))
        frame=self.click(frame,'X +')
        self.model.nudge_placement.assert_called_once_with('sdk.faceless-boy-sample','boy-here',0,1,10.)
        frame=self.click(frame,'Step:');frame=self.click(frame,'Step:')
        self.click(frame,'Yaw -')
        self.assertEqual(self.model.nudge_placement.call_args.args[-3:],(3,-1,1.))
    def test_already_bound_save_has_no_enabled_confirm(self):
        self.view.request=None;frame=self.view.render()
        self.assertFalse(self.control(frame,'Confirm:').enabled)

    def click(self,frame,label,**kwargs):
        return self.view.activate(frame.revision,self.control(frame,label).token,**kwargs)

    def open_pack(self):
        return self.click(self.view.render(),'Faceless Boy')

    def test_edit_native_line_and_response_labels_with_existing_text_field(self):
        frame=self.click(self.open_pack(),'Open conversation graph')
        frame=self.click(self.click(frame,'first-meeting'),'List / advanced');frame=self.click(frame,'welcome |')
        frame=self.click(frame,'Edit dialogue text')
        self.assertEqual(self.view.editing[1]['kind'],'text')
        old=frame
        frame=self.click(frame,'Apply text',value='A custom native line')
        self.model.edit_pack.assert_called_once_with('sdk.faceless-boy-sample','text','first-meeting','welcome','A custom native line')
        self.assertIsNone(self.view.editing)
        with self.assertRaises(ManagementError):self.click(old,'Apply text',value='stale')
        frame=self.click(frame,'Response: Tell me')
        frame=self.click(frame,'Apply text',value='A custom response')
        self.assertEqual(self.model.edit_pack.call_args.args,('sdk.faceless-boy-sample','choice_text','first-meeting','welcome','story','A custom response'))

    def test_character_placement_requires_both_character_and_conversation(self):
        frame=self.click(self.open_pack(),'Place a character')
        frame=self.click(frame,'Faceless Boy')
        self.model.place_character.assert_not_called()
        self.click(frame,'first-meeting')
        self.model.place_character.assert_called_once_with('sdk.faceless-boy-sample','boy','first-meeting')

    def test_create_and_link_new_conversation_through_workspace_and_real_storage(self):
        import tempfile
        from pathlib import Path
        from test_story_authoring import PackEditor
        from test_story_packs import Conversation
        with tempfile.TemporaryDirectory() as folder:
            draft=PackEditor(Path(folder)).create(test_story_packs.sample())
            pack=self.model.library.get('sdk.faceless-boy-sample')
            def edit(pack_id,operation,*args):
                getattr(draft,operation)(*args)
                pack.clear();pack.update(draft.document)
            self.model.edit_pack=edit
            frame=self.click(self.open_pack(),'Open conversation graph')
            frame=self.click(frame,'New conversation');dialogue=self.view.dialogue
            frame=self.click(frame,'Add conversation line');destination=self.view.node
            frame=self.click(frame,'Back');frame=self.click(frame,'welcome |')
            frame=self.click(frame,'Add response')
            frame=self.click(frame,'Destination:')
            frame=self.click(frame,destination+' |')
            saved=draft.document['dialogues'][dialogue]
            response=saved['nodes']['welcome']['choices'][0]
            self.assertEqual(response['next'],destination)
            flow=Conversation(draft.document,dialogue,{})
            self.assertEqual(flow.advance('welcome',response['id'])['node'],destination)

    def test_character_picker_uses_runtime_profiles_and_can_change_line_speaker(self):
        import tempfile
        from pathlib import Path
        from test_story_authoring import PackEditor
        with tempfile.TemporaryDirectory() as folder:
            draft=PackEditor(Path(folder)).create(test_story_packs.sample())
            pack=self.model.library.get('sdk.faceless-boy-sample')
            def edit(pack_id,operation,*args):
                getattr(draft,operation)(*args);pack.clear();pack.update(draft.document)
            self.model.edit_pack=edit
            frame=self.click(self.open_pack(),'Place a character')
            frame=self.click(frame,'Add character from Blueprint')
            self.assertEqual([c.label for c in frame.controls if c.label in ('Lune','Faceless Boy')],['Faceless Boy','Lune'])
            frame=self.click(frame,'Lune')
            character=next(k for k,c in pack['characters'].items() if c['profile']=='lune')
            frame=self.click(frame,'Back');frame=self.click(frame,'Open conversation graph')
            frame=self.click(self.click(frame,'first-meeting'),'List / advanced');frame=self.click(frame,'welcome |')
            frame=self.click(frame,'Speaker:');self.click(frame,'Lune')
            self.assertEqual(draft.document['dialogues']['first-meeting']['nodes']['welcome']['speaker'],character)

    def test_restored_save_opens_bound_pack_without_rebinding(self):
        pack_id='sdk.faceless-boy-sample'
        self.model.live.choices=lambda:None
        self.model.live.playthroughs=N(key='save',state=N(get=lambda key:dict(pack=pack_id)))
        view=StoryView(N(_check=lambda:None),self.model)
        self.assertEqual(view.pack,pack_id)
        title,description,rows=view._rows()
        self.assertIn('Selected for this save:',description)
        self.assertIn('Faceless Boy',description)
        self.assertFalse(self.control(view.render(),'Confirm:').enabled)
        self.model.live.choose.assert_not_called()

    def test_missing_bound_pack_is_reported_without_selecting_another(self):
        self.model.live.choices=lambda:None
        self.model.live.playthroughs=N(key='save',state=N(get=lambda key:dict(pack='missing.story')))
        view=StoryView(N(_check=lambda:None),self.model)
        self.assertEqual(view.pack,'missing.story')
        self.assertIn('Missing pack: missing.story',view._rows()[1])
        self.model.live.choose.assert_not_called()

    def test_new_story_title_uses_shared_edit_field_and_does_not_bind_save(self):
        self.model.create_story=Mock(return_value='new.story')
        frame=self.click(self.view.render(),'Create story pack')
        self.assertEqual(self.view.editing[1]['kind'],'text')
        frame=self.click(frame,'Create story pack',value='A new campaign')
        self.model.create_story.assert_called_once_with('A new campaign')
        self.assertEqual(self.view.pack,'new.story')
        self.assertIsNone(self.view.editing)
        self.model.live.choose.assert_not_called()

    def test_line_effect_flag_can_be_authored_changed_and_removed_in_workspace(self):
        import tempfile
        from pathlib import Path
        from test_story_authoring import PackEditor
        with tempfile.TemporaryDirectory() as folder:
            draft=PackEditor(Path(folder)).create(test_story_packs.sample())
            pack=self.model.library.get('sdk.faceless-boy-sample')
            def edit(pack_id,operation,*args):
                getattr(draft,operation)(*args);pack.clear();pack.update(draft.document)
            self.model.edit_pack=edit
            frame=self.click(self.open_pack(),'Open conversation graph')
            frame=self.click(self.click(frame,'first-meeting'),'List / advanced');frame=self.click(frame,'welcome |')
            frame=self.click(frame,'On line reached: story effects')
            frame=self.click(frame,'Add flag')
            frame=self.click(frame,'Add flag',value='quest-started')
            self.assertTrue(draft.document['dialogues']['first-meeting']['nodes']['welcome']['set']['quest-started'])
            frame=self.click(frame,'quest-started = true');frame=self.click(frame,'False')
            self.assertFalse(draft.document['dialogues']['first-meeting']['nodes']['welcome']['set']['quest-started'])
            frame=self.click(frame,'quest-started = false');frame=self.click(frame,'Remove rule')
            self.assertNotIn('quest-started',draft.document['dialogues']['first-meeting']['nodes']['welcome']['set'])
            frame=self.click(frame,'Back')
            self.assertEqual(self.view.screen,'story_node')

    def test_flight_placement_control_routes_selected_placement_only(self):
        pack=self.model.library.get('sdk.faceless-boy-sample')
        pack['placements']=[dict(id='boy-here',character='boy',dialogue='first-meeting',world='map',position=[1,2,3],yaw=0)]
        self.model.move_placement_from_flight=Mock()
        frame=self.click(self.open_pack(),'Saved placements')
        frame=self.click(frame,'boy-here |')
        self.click(frame,'Copy flight-camera pose')
        self.model.move_placement_from_flight.assert_called_once_with('sdk.faceless-boy-sample','boy-here')
        self.model.move_placement_here.assert_not_called()

    def test_confirm_immediately_displays_bound_story_instead_of_no_save_ready(self):
        frame=self.open_pack()
        self.click(frame,'Confirm:')
        description=self.view._rows()[1]
        self.assertIn('Selected for this save: Faceless Boy',description)
        self.assertNotIn('No save is ready',description)
        self.assertFalse(self.control(self.view.render(),'Confirm:').enabled)

    def test_saved_placement_conversation_picker_routes_to_selected_placement(self):
        pack=self.model.library.get('sdk.faceless-boy-sample')
        pack['placements']=[dict(id='boy-here',world='/Game/Test.Test',position=[1,2,3],yaw=0,character='boy',dialogue='first-meeting',requires={})]
        frame=self.click(self.open_pack(),'Saved placements')
        frame=self.click(frame,'boy-here |')
        frame=self.click(frame,'Change conversation')
        frame=self.click(frame,'Back')
        self.assertEqual(self.view.screen,'story_placement')
        frame=self.click(frame,'Change conversation')
        self.click(frame,'first-meeting')
        self.model.edit_pack.assert_called_once_with('sdk.faceless-boy-sample','placement_dialogue','boy-here','first-meeting')
        self.assertEqual(self.view.screen,'story_placement')

    def test_starting_line_picker_saves_entry_and_returns_to_lines(self):
        frame=self.click(self.open_pack(),'Open conversation graph')
        frame=self.click(self.click(frame,'first-meeting'),'List / advanced')
        frame=self.click(frame,'Choose starting line')
        self.click(frame,'story |')
        self.model.edit_pack.assert_called_once_with('sdk.faceless-boy-sample','entry','first-meeting','story')
        self.assertEqual(self.view.screen,'story_nodes')

    def test_removing_response_requires_confirmation_and_keeps_destination_line(self):
        pack=self.model.library.get('sdk.faceless-boy-sample')
        pack['dialogues']['first-meeting']['nodes']['welcome']['choices']=pack['dialogues']['first-meeting']['nodes']['welcome']['choices'][:1]
        frame=self.click(self.open_pack(),'Open conversation graph')
        frame=self.click(self.click(frame,'first-meeting'),'List / advanced');frame=self.click(frame,'welcome |')
        frame=self.click(frame,'Next')
        frame=self.click(frame,'Remove response:')
        self.model.edit_pack.assert_not_called()
        frame=self.click(frame,'Keep response')
        self.model.edit_pack.assert_not_called()
        frame=self.click(frame,'Next')
        frame=self.click(frame,'Remove response:')
        self.click(frame,'Remove response')
        self.model.edit_pack.assert_called_once_with('sdk.faceless-boy-sample','remove_choice','first-meeting','welcome','story')
        self.assertEqual(self.view.screen,'story_node')

    def test_remove_placement_confirmation_preserves_conversations_and_other_maps(self):
        import copy
        import tempfile
        from pathlib import Path
        from test_story_authoring import PackEditor
        pack=self.model.library.get('sdk.faceless-boy-sample')
        pack['placements']=[dict(id=key,world=world,position=[1,2,3],yaw=0,radius=200,
            character='boy',dialogue='first-meeting',requires={})
            for key,world in [('boy-here','/Game/Test.Test'),('boy-elsewhere','/Game/Other.Other')]]
        with tempfile.TemporaryDirectory() as folder:
            draft=PackEditor(Path(folder)).create(pack)
            original=copy.deepcopy(draft.document)
            def edit(pack_id,operation,*args):
                getattr(draft,operation)(*args);pack.clear();pack.update(draft.document)
            self.model.edit_pack=edit
            frame=self.click(self.open_pack(),'Saved placements')
            frame=self.click(frame,'boy-here |')
            frame=self.click(frame,'Remove saved placement')
            self.assertEqual(draft.document,original)
            frame=self.click(frame,'Keep placement')
            frame=self.click(frame,'Remove saved placement')
            frame=self.click(frame,'Remove saved placement')
            self.assertEqual(self.view.screen,'story_placements')
            self.assertIsNone(self.view.placement)
            self.assertEqual(draft.document['placements'],original['placements'][1:])
            self.assertEqual(draft.document['characters'],original['characters'])
            self.assertEqual(draft.document['dialogues'],original['dialogues'])
            self.assertEqual(PackEditor(Path(folder)).open(pack['id']).document,draft.document)

