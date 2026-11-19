import importlib
import copy
import tempfile
import unittest
import uuid
from pathlib import Path
from test_story_packs import sample,storage
from test_story_runtime import Backend,WORLD

runtime=importlib.import_module('story_packs_test.runtime')
playthrough=importlib.import_module('story_packs_test.playthrough')


class PlaythroughTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name);self.pack=sample()
        self.pack['placements']=[dict(id='boy-here',world=WORLD,character='boy',dialogue='first-meeting',position=[10,20,30],yaw=0,radius=200,requires={})]
        storage.write_json(self.root/'packs/sample/storypack.json',self.pack)
        self.library=storage.PackLibrary(self.root/'packs');self.library.refresh()
        self.state=storage.StoryState(self.root/'state.json');self.backend=Backend()
        self.runtime=runtime.StoryRuntime(self.library,self.state,self.backend)
        self.controller=playthrough.Playthroughs(self.library,self.state,self.runtime)
        self.key=uuid.uuid4().hex

    def test_selection_persists_then_restores_on_a_fresh_controller(self):
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        self.assertFalse(self.backend.spawned)
        request=self.controller.choices()
        self.controller.choose(request['token'],self.pack['id'])
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        self.assertEqual(len(self.backend.spawned),1)
        self.runtime.retire()
        state=storage.StoryState(self.state.path)
        restored=runtime.StoryRuntime(self.library,state,self.backend)
        controller=playthrough.Playthroughs(self.library,state,restored)
        controller.admit(self.key,WORLD,(2,),ready=True)
        self.assertIsNone(controller.choices());self.assertEqual(len(self.backend.spawned),2)

    def test_stale_selection_cannot_bind_a_different_save(self):
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        old=self.controller.choices()['token'];other=uuid.uuid4().hex
        self.controller.admit(other,WORLD,(1,),ready=True)
        with self.assertRaises(ValueError):self.controller.choose(old,self.pack['id'])
        self.assertIsNone(self.state.get(other));self.assertIsNone(self.state.get(self.key))

    def test_cleanup_barrier_keeps_new_save_content_out(self):
        self.state.bind(self.key,self.pack)
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        self.backend.hold=True;other=uuid.uuid4().hex
        self.assertFalse(self.controller.admit(other,WORLD,(2,),ready=True))
        self.assertEqual(self.controller.key,self.key);self.assertIsNone(self.controller.choices())
        self.backend.hold=False
        self.assertTrue(self.controller.admit(other,WORLD,(2,),ready=True))
        self.assertEqual(self.controller.choices()['token'][0],other)

    def test_missing_selected_pack_does_not_offer_a_silent_replacement(self):
        self.state.bind(self.key,self.pack);self.library.packs.clear()
        self.assertFalse(self.controller.admit(self.key,WORLD,(1,),ready=True))
        self.assertIn('not installed',self.controller.error)
        self.assertIsNone(self.controller.choices());self.assertFalse(self.backend.spawned)

    def test_vanilla_selection_never_spawns_story_actors(self):
        self.controller.admit(self.key,WORLD,(1,),ready=False)
        self.controller.choose(self.controller.choices()['token'],None)
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        self.assertFalse(self.backend.spawned);self.assertIsNone(self.controller.choices())

    def test_thirty_installed_stories_restore_distinct_save_and_map_conversations(self):
        other_world='/Game/Other.Other'
        ids=[];keys=[]
        for index in range(30):
            pack=copy.deepcopy(self.pack);pack['id']=f'story.test-{index}';pack['title']=f'Story {index}'
            pack['dialogues']={name:dict(entry='hello',nodes={'hello':dict(speaker='boy',
                text=f'Story {index}: {name}',next=None,choices=[],set={f'visited-{name}':True})})
                for name in ('first-map','second-map')}
            pack['placements']=[dict(id=name,world=world,character='boy',dialogue=name,
                position=[10,20,30],yaw=0,radius=200,requires={})
                for name,world in [('first-map',WORLD),('second-map',other_world)]]
            storage.write_json(self.root/f'packs/story-{index}/storypack.json',pack)
            ids.append(pack['id']);keys.append(uuid.uuid4().hex)
        self.library.refresh()
        for index,(key,pack_id) in enumerate(zip(keys,ids)):
            self.assertTrue(self.controller.admit(key,WORLD,(index+1,),ready=True))
            request=self.controller.choices()
            self.assertTrue(set(ids).issubset({s['id'] for s in request['stories']}))
            self.controller.choose(request['token'],pack_id)
            self.assertTrue(self.controller.admit(key,WORLD,(index+1,),ready=True))
            self.assertEqual(set(self.runtime.actors),{'first-map'})
            view=self.runtime.interact_placement('first-map')
            self.assertEqual(view['text'],f'Story {index}: first-map')
            self.runtime.advance(view['node'])
            self.assertEqual(self.state.get(key)['flags'],{'visited-first-map':True})
        self.assertTrue(self.runtime.retire())
        # Recreate all persistence/runtime objects, as after a process restart.
        library=storage.PackLibrary(self.root/'packs');library.refresh()
        state=storage.StoryState(self.state.path)
        restored=runtime.StoryRuntime(library,state,Backend())
        controller=playthrough.Playthroughs(library,state,restored)
        for index,(key,pack_id) in enumerate(zip(keys,ids)):
            self.assertTrue(controller.admit(key,other_world,(index+100,),ready=True))
            self.assertIsNone(controller.choices())
            self.assertEqual(state.get(key)['pack'],pack_id)
            self.assertEqual(set(restored.actors),{'second-map'})
            view=restored.interact_placement('second-map')
            self.assertEqual(view['text'],f'Story {index}: second-map')
            restored.advance(view['node'])
            self.assertEqual(state.get(key)['flags'],{'visited-first-map':True,'visited-second-map':True})
        self.assertTrue(restored.retire())


class SaveAdmissionTests(unittest.TestCase):
    setUp=PlaythroughTests.setUp
    def adapter(self, read):
        from types import SimpleNamespace
        return playthrough.SaveAdmission(SimpleNamespace(read=read),self.controller)

    def test_loaded_marker_restores_selected_pack_without_slot_identity(self):
        key='e33c5701'+'12345678'*3
        self.state.bind(key,self.pack)
        self.assertTrue(self.adapter(lambda:key).reconcile(WORLD,(1,),ready=True))
        self.assertEqual(self.controller.key,key)
        self.assertEqual(len(self.backend.spawned),1)

    def test_read_failure_retires_previous_save_actors(self):
        key='e33c5701'+'12345678'*3
        self.state.bind(key,self.pack)
        self.controller.admit(key,WORLD,(1,),ready=True)
        def failed():raise RuntimeError('Save is changing')
        adapter=self.adapter(failed)
        self.assertFalse(adapter.reconcile(WORLD,(2,),ready=True))
        self.assertIsNone(self.controller.key)
        self.assertEqual(adapter.error,'Save is changing')

    def test_title_does_not_read_or_bind_identity(self):
        def forbidden():raise AssertionError('Title must not read a save')
        self.adapter(forbidden).reconcile(None,None,ready=False)
        self.assertIsNone(self.controller.key)
        self.assertIsNone(self.controller.choices())

    def test_absent_identity_does_not_inherit_previous_selection(self):
        self.state.bind(self.key,self.pack)
        self.controller.admit(self.key,WORLD,(1,),ready=True)
        self.adapter(lambda:None).reconcile(WORLD,(2,),ready=True)
        self.assertIsNone(self.controller.key)
        self.assertIsNone(self.controller.choices())
