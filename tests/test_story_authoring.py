import importlib
import tempfile
import unittest
from pathlib import Path
from test_story_packs import sample,storage
PackEditor=importlib.import_module('story_packs_test.authoring').PackEditor
WORLD='/Game/Test/Map.Map'

class StoryAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.editor=PackEditor(self.root);self.draft=self.editor.create(sample())
    def test_capture_move_and_remove_placement_preserve_dialogue_and_other_content(self):
        original=self.draft.document['dialogues']
        self.draft.place('boy-one',WORLD,[1,2,3],45,'boy','first-meeting')
        self.draft.move('boy-one',WORLD,[4,5,6],90)
        stored=storage.read_json(self.draft.path)
        self.assertEqual(stored['placements'][0]['position'],[4,5,6]);self.assertEqual(stored['dialogues'],original)
        self.draft.remove('boy-one');self.assertEqual(storage.read_json(self.draft.path)['placements'],[])
    def test_two_editors_cannot_overwrite_each_others_changes(self):
        other=self.editor.open(sample()['id']);self.draft.text('first-meeting','welcome','Edited sample')
        with self.assertRaisesRegex(ValueError,'changed on disk'):other.text('first-meeting','welcome','Old editor')
        self.assertEqual(storage.read_json(other.path)['dialogues']['first-meeting']['nodes']['welcome']['text'],'Edited sample')
    def test_invalid_unrelated_pack_does_not_block_editing_valid_story(self):
        damaged=self.root/'damaged'/'storypack.json'
        damaged.parent.mkdir();damaged.write_text('{broken',encoding='utf-8')
        draft=self.editor.open(sample()['id'])
        draft.text('first-meeting','welcome','Still editable')
        self.assertEqual(storage.read_json(draft.path)['dialogues']['first-meeting']['nodes']['welcome']['text'],'Still editable')
        self.assertEqual(damaged.read_text(encoding='utf-8'),'{broken')
    def test_duplicate_valid_pack_id_still_prevents_editing(self):
        duplicate=self.root/'duplicate'/'storypack.json'
        storage.write_json(duplicate,sample())
        before=self.draft.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Exactly one'):self.editor.open(sample()['id'])
        self.assertEqual(self.draft.path.read_bytes(),before)
    def test_invalid_placement_or_text_never_replaces_the_file(self):
        before=self.draft.path.read_bytes()
        with self.assertRaises(ValueError):self.draft.place('bad',WORLD,[float('nan'),0,0],0,'boy','first-meeting')
        with self.assertRaises(ValueError):self.draft.text('first-meeting','welcome','')
        self.assertEqual(self.draft.path.read_bytes(),before)
    def test_duplicate_ids_and_duplicate_placements_are_rejected(self):
        with self.assertRaises(ValueError):self.editor.create(sample())
        self.draft.place('boy-one',WORLD,[1,2,3],0,'boy','first-meeting')
        with self.assertRaises(ValueError):self.draft.place('boy-one',WORLD,[1,2,3],0,'boy','first-meeting')
    def test_story_can_use_another_reviewed_character_profile(self):
        self.draft.character('traveller','Traveller','lune')
        self.draft.place('traveller-here',WORLD,[1,2,3],0,'traveller','first-meeting')
        self.assertEqual(storage.read_json(self.draft.path)['characters']['traveller']['profile'],'lune')

    def test_choice_text_edit_preserves_branch_target_flags_and_other_choices(self):
        import copy
        expected=copy.deepcopy(self.draft.document)
        expected['dialogues']['first-meeting']['nodes']['welcome']['choices'][0]['text']='Ask about the journey'
        self.draft.choice_text('first-meeting','welcome','story','Ask about the journey')
        self.assertEqual(storage.read_json(self.draft.path),expected)
        before=self.draft.path.read_bytes()
        with self.assertRaises(ValueError):self.draft.choice_text('first-meeting','welcome','missing','No')
        with self.assertRaises(ValueError):self.draft.choice_text('first-meeting','welcome','story','')
        self.assertEqual(self.draft.path.read_bytes(),before)

    def test_new_conversation_branches_execute_through_existing_dialogue_engine(self):
        from test_story_packs import Conversation
        self.draft.conversation('journey','boy','Where shall we go?')
        self.draft.node('journey','forest','boy','Into the forest.')
        self.draft.node('journey','shore','boy','To the shore.')
        self.draft.choice('journey','welcome','forest','The forest','forest')
        self.draft.choice('journey','welcome','shore','The shore','shore')
        for branch,line in [('forest','Into the forest.'),('shore','To the shore.')]:
            flow=Conversation(storage.read_json(self.draft.path),'journey',{})
            self.assertEqual(len(flow.view()['choices']),2)
            self.assertEqual(flow.advance('welcome',branch)['text'],line)
            self.assertIsNone(flow.advance(branch))

    def test_graph_edits_reject_missing_targets_duplicates_and_mixed_routes(self):
        self.draft.conversation('journey','boy','Hello')
        self.draft.node('journey','reply','boy','Goodbye')
        self.draft.destination('journey','welcome',None,'reply')
        before=self.draft.path.read_bytes()
        for operation in [lambda:self.draft.choice('journey','welcome','answer','Go','reply'),
                          lambda:self.draft.destination('journey','welcome',None,'missing'),
                          lambda:self.draft.conversation('journey','boy','Duplicate'),
                          lambda:self.draft.node('journey','reply','boy','Duplicate')]:
            with self.assertRaises(ValueError):operation()
            self.assertEqual(self.draft.path.read_bytes(),before)
        self.draft.destination('journey','welcome',None,None)
        self.draft.choice('journey','welcome','answer','Go','reply')
        self.draft.destination('journey','welcome','answer',None)
        self.assertIsNone(self.draft.document['dialogues']['journey']['nodes']['welcome']['choices'][0]['next'])

    def test_new_stories_are_independent_and_invalid_titles_do_not_write(self):
        before=self.draft.path.read_bytes()
        first=self.editor.create_story('First story')
        second=self.editor.create_story('Second story')
        self.assertNotEqual(first.document['id'],second.document['id'])
        self.assertEqual(first.document['placements'],[])
        self.assertEqual(first.document['title'],'First story')
        self.assertEqual(self.draft.path.read_bytes(),before)
        paths=set(self.root.glob('*/storypack.json'))
        with self.assertRaises(ValueError):self.editor.create_story('')
        self.assertEqual(set(self.root.glob('*/storypack.json')),paths)

    def test_authored_flags_gate_choices_and_placements_and_persist_outcomes(self):
        from test_story_packs import Conversation
        from story_packs_test.schema import placements_for
        self.draft.place('boy-one',WORLD,[1,2,3],0,'boy','first-meeting')
        self.draft.flag(('placement','boy-one'),'quest-started',True)
        self.draft.flag(('line','first-meeting','welcome'),'quest-started',True)
        target=('choice','first-meeting','welcome','story')
        self.draft.flag(target+('requires',),'quest-started',True)
        self.draft.flag(target+('set',),'accepted',True)
        document=storage.read_json(self.draft.path)
        self.assertEqual(placements_for(document,WORLD,{}),())
        self.assertEqual(len(placements_for(document,WORLD,{'quest-started':True})),1)
        flow=Conversation(document,'first-meeting',{})
        self.assertTrue(flow.state['quest-started'])
        flow.advance('welcome','story')
        self.assertTrue(flow.state['accepted'])
        self.draft.flag(target+('requires',),'quest-started',False)
        flow=Conversation(self.draft.document,'first-meeting',{})
        self.assertNotIn('story',[c['id'] for c in flow.view()['choices']])
        self.draft.flag(target+('requires',),'quest-started',None)
        self.assertEqual(self.draft.document['dialogues']['first-meeting']['nodes']['welcome']['choices'][0]['requires'],{})

    def test_invalid_flag_edits_leave_pack_unchanged(self):
        before=self.draft.path.read_bytes()
        for target,key,value in [(('line','missing','welcome'),'flag',True),
                                 (('line','first-meeting','welcome'),'flag',1),
                                 (('line','first-meeting','welcome'),'bad key',True),
                                 (('choice','first-meeting','welcome','story','next'),'flag',True)]:
            with self.assertRaises(ValueError):self.draft.flag(target,key,value)
            self.assertEqual(self.draft.path.read_bytes(),before)

    def test_reassign_placement_conversation_preserves_pose_conditions_and_other_content(self):
        import copy
        self.draft.place('boy-one',WORLD,[1,2,3],45,'boy','first-meeting')
        self.draft.flag(('placement','boy-one'),'accepted',True)
        self.draft.conversation('another','boy','Another conversation')
        expected=copy.deepcopy(self.draft.document)
        expected['placements'][0]['dialogue']='another'
        self.draft.placement_dialogue('boy-one','another')
        self.assertEqual(storage.read_json(self.draft.path),expected)
        before=self.draft.path.read_bytes()
        for placement,dialogue in [('missing','another'),('boy-one','missing')]:
            with self.assertRaises(ValueError):self.draft.placement_dialogue(placement,dialogue)
            self.assertEqual(self.draft.path.read_bytes(),before)

    def test_entry_and_response_removal_preserve_other_graph_content(self):
        import copy
        self.draft.entry('first-meeting','story')
        expected=copy.deepcopy(self.draft.document)
        expected['dialogues']['first-meeting']['nodes']['welcome']['choices']=[c for c in expected['dialogues']['first-meeting']['nodes']['welcome']['choices'] if c['id']!='story']
        self.draft.remove_choice('first-meeting','welcome','story')
        self.assertEqual(storage.read_json(self.draft.path),expected)
        self.assertEqual(expected['dialogues']['first-meeting']['entry'],'story')
        before=self.draft.path.read_bytes()
        for operation in [lambda:self.draft.entry('first-meeting','missing'),lambda:self.draft.entry('missing','welcome'),lambda:self.draft.remove_choice('first-meeting','welcome','missing')]:
            with self.assertRaises(ValueError):operation()
            self.assertEqual(self.draft.path.read_bytes(),before)
