import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
package=types.ModuleType('story_packs_test');package.__path__=[str(ROOT/'mods/StoryPacks')]
sys.modules[package.__name__]=package
schema=importlib.import_module('story_packs_test.schema')
storage=importlib.import_module('story_packs_test.storage')
Conversation=importlib.import_module('story_packs_test.dialogue').Conversation


def sample():
    return schema.validate(json.loads((ROOT/'mods/StoryPacks/sample/storypack.json').read_text(encoding='utf-8')))


class StoryPackTests(unittest.TestCase):
    def test_dialogue_validation_matches_native_utf16_capacity(self):
        pack=sample();node=pack['dialogues']['first-meeting']['nodes']['welcome']
        for value in ('x'*4096,'\U0001f600'*2048,'bad\ud800'):
            node['text']=value
            with self.assertRaises(ValueError):schema.validate(pack)
        node['text']='\U0001f600'*2047+'x'
        self.assertEqual(schema.validate(pack)['dialogues']['first-meeting']['nodes']['welcome']['text'],node['text'])
        node['choices']=[dict(id='choice-'+str(i),text='x'*512,next=None,requires={},set={}) for i in range(16)]
        with self.assertRaisesRegex(ValueError,'Combined response'):schema.validate(pack)
        for choice in node['choices']:choice['text']='x'*511
        self.assertEqual(len(schema.validate(pack)['dialogues']['first-meeting']['nodes']['welcome']['choices']),16)

    def test_thirty_installed_stories_are_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            for number in range(30):
                pack=sample();pack['id']='story.'+str(number);pack['title']='Story '+str(number)
                storage.write_json(Path(folder)/str(number)/'storypack.json',pack)
            library=storage.PackLibrary(folder)
            self.assertEqual(len(library.refresh()),30)
            pack=library.get('story.0');pack['title']='changed'
            self.assertNotEqual(library.get('story.0')['title'],'changed')
            self.assertIsNone(library.get('uninstalled.pack'))

    def test_duplicate_ids_are_rejected_without_hiding_other_stories(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('a','b','c'):storage.write_json(Path(folder)/name/'storypack.json',sample())
            good=sample();good['id']='unique.story'
            storage.write_json(Path(folder)/'good'/'storypack.json',good)
            library=storage.PackLibrary(folder)
            self.assertEqual([p['id'] for p in library.refresh()],['unique.story'])
            self.assertTrue(library.errors)

    def test_dialogue_choices_and_flags_survive_a_state_reload(self):
        pack=sample();key=uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stories.json';state=storage.StoryState(path)
            state.bind(key,pack)
            conversation=Conversation(pack,'first-meeting',state.get(key)['flags'])
            self.assertEqual(conversation.view()['speaker'],'Faceless Boy')
            conversation.advance('welcome','story')
            state.update_flags(key,conversation.state)
            restored=storage.StoryState(path).get(key)
            self.assertEqual(restored['pack'],pack['id'])
            self.assertEqual(restored['flags'],{'met-boy':True,'heard-story':True})
            with self.assertRaises(ValueError):conversation.advance('welcome','leave')

    def test_one_pack_per_playthrough_and_explicit_vanilla_are_persistent(self):
        first,second=uuid.uuid4().hex,uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as folder:
            state=storage.StoryState(Path(folder)/'state.json')
            state.bind(first,sample());state.bind(second,None)
            with self.assertRaises(ValueError):state.bind(first,None)
            self.assertIsNone(state.get(second)['pack'])
            self.assertEqual(state.get(first)['flags'],{})
            with self.assertRaises(ValueError):state.get('EXPEDITION_2')
            with self.assertRaises(ValueError):state.get('0'*32)

    def test_missing_selected_pack_never_chooses_another_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            state=storage.StoryState(Path(folder)/'state.json');key=uuid.uuid4().hex
            state.bind(key,sample())
            other=sample();other['id']='other.story'
            storage.write_json(Path(folder)/'packs/other/storypack.json',other)
            library=storage.PackLibrary(Path(folder)/'packs');library.refresh()
            self.assertIsNone(library.get(state.get(key)['pack']))
            self.assertEqual(state.get(key)['pack'],'sdk.faceless-boy-sample')

    def test_map_and_story_conditions_filter_placements_without_mutating_content(self):
        pack=sample();map_path='/Game/Levels/WorldMap/Level_WorldMap_Main_V2.Level_WorldMap_Main_V2'
        pack['placements']=[dict(id='boy-one',world=map_path,character='boy',dialogue='first-meeting',
            position=[100.,200.,300.],yaw=90.,radius=180.,requires={'heard-story':True})]
        pack=schema.validate(pack)
        self.assertEqual(schema.placements_for(pack,map_path,{}),())
        result=schema.placements_for(pack,map_path,{'heard-story':True})
        self.assertEqual(len(result),1)
        result[0]['position'][0]=999
        self.assertEqual(pack['placements'][0]['position'][0],100.)

    def test_invalid_destinations_or_transforms_cannot_reach_runtime(self):
        for mutate in (
            lambda p:p['dialogues']['first-meeting']['nodes']['welcome'].update(next='missing',choices=[]),
            lambda p:p['dialogues']['first-meeting']['nodes']['welcome']['set'].update(bad=1),
            lambda p:p.update(schema=True),
            lambda p:p.update(python='exec code'),
        ):
            pack=sample();mutate(pack)
            with self.assertRaises(ValueError):schema.validate(pack)

    def test_hidden_choice_is_not_executable_by_stale_or_fabricated_ui_input(self):
        pack=sample()
        pack['dialogues']['first-meeting']['nodes']['welcome']['choices'][0]['requires']={'unlocked':True}
        conversation=Conversation(schema.validate(pack),'first-meeting',{})
        self.assertEqual([c['id'] for c in conversation.view()['choices']],['leave'])
        before=copy.deepcopy(conversation.state)
        with self.assertRaises(ValueError):conversation.advance('welcome','story')
        self.assertEqual(conversation.state,before)


if __name__=='__main__':unittest.main()
