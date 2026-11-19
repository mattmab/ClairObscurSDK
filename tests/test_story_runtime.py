import importlib
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from test_story_packs import sample,storage
runtime=importlib.import_module('story_packs_test.runtime')
WORLD='/Game/Test/Map.Map'

class Backend:
    def __init__(self):self.created=[];self.spawned=[];self.retired=[];self.hold=False;self.fail=False
    def create(self):
        actor=object();self.created.append(actor);return actor
    def spawn(self,actor,profile,pose,*,name):
        self.spawned.append((actor,profile,pose))
        if self.fail:raise RuntimeError('partial construction')
    def retire(self,actor):
        self.retired.append(actor);return not self.hold

class StoryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        root=Path(self.folder.name);self.pack=sample()
        self.pack['placements']=[dict(id='boy-here',world=WORLD,character='boy',dialogue='first-meeting',position=[10,20,30],yaw=90,radius=200,requires={})]
        storage.write_json(root/'packs/sample/storypack.json',self.pack)
        self.library=storage.PackLibrary(root/'packs');self.library.refresh()
        self.state=storage.StoryState(root/'state.json');self.key=uuid.uuid4().hex;self.state.bind(self.key,self.pack)
        self.backend=Backend();self.runtime=runtime.StoryRuntime(self.library,self.state,self.backend);self.runtime.select_playthrough(self.key)
    def test_placements_spawn_once_and_only_in_the_admitted_map(self):
        self.runtime.reconcile(WORLD,(1,),ready=False);self.assertFalse(self.backend.created)
        self.runtime.reconcile('/Game/Other.Other',(1,),ready=True);self.assertFalse(self.backend.created)
        self.runtime.reconcile(WORLD,(2,),ready=True);self.runtime.reconcile(WORLD,(2,),ready=True)
        self.assertEqual(len(self.backend.created),1)
        pose=self.backend.spawned[0][2];self.assertEqual(pose[4:7],(10,20,30));self.assertAlmostEqual(sum(x*x for x in pose[:4]),1)
    def test_old_visit_cleanup_must_finish_before_spawning_in_the_new_visit(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);self.backend.hold=True
        self.assertFalse(self.runtime.reconcile(WORLD,(2,),ready=True));self.assertEqual(len(self.backend.created),1)
        self.backend.hold=False;self.assertTrue(self.runtime.reconcile(WORLD,(2,),ready=True));self.assertEqual(len(self.backend.created),2)
    def test_partial_spawn_is_owned_and_never_replayed_on_ticks(self):
        self.backend.fail=True;self.runtime.reconcile(WORLD,(1,),ready=True)
        self.runtime.reconcile(WORLD,(1,),ready=True);self.assertEqual(len(self.backend.spawned),1)
        self.assertIsNone(self.runtime.nearest([10,20,30]));self.assertIn('boy-here',self.runtime.errors)
        self.runtime.retire();self.assertEqual(self.backend.retired,self.backend.created)
    def test_conversation_is_nearby_only_and_flags_persist(self):
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertIsNone(self.runtime.interact([999,999,999]))
        view=self.runtime.interact([10,20,30]);self.assertEqual(view['node'],'welcome')
        self.assertTrue(self.state.get(self.key)['flags']['met-boy'])
        view=self.runtime.advance('welcome','story');self.assertEqual(view['node'],'story')
        self.assertTrue(storage.StoryState(self.state.path).get(self.key)['flags']['heard-story'])
        self.runtime.reconcile(WORLD,(2,),ready=True)
        with self.assertRaisesRegex(ValueError,'No active'):self.runtime.advance('story')
    def test_failed_persistence_does_not_advance_the_visible_node(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);self.runtime.interact([10,20,30])
        with patch.object(self.state,'update_flags',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.runtime.advance('welcome','story')
        self.assertEqual(self.runtime.conversation.node,'welcome')
        self.assertNotIn('heard-story',self.runtime.conversation.state)
    def test_switching_saves_requires_cleanup_and_vanilla_never_spawns(self):
        self.runtime.reconcile(WORLD,(1,),ready=True)
        key=uuid.uuid4().hex;self.state.bind(key,None)
        with self.assertRaises(RuntimeError):self.runtime.select_playthrough(key)
        self.runtime.retire();self.runtime.select_playthrough(key);self.runtime.reconcile(WORLD,(2,),ready=True)
        self.assertEqual(len(self.backend.created),1)

    def test_flags_remove_placements_without_replaying_existing_spawns(self):
        self.runtime.document['placements'][0]['requires']={'met-boy':False}
        self.runtime.reconcile(WORLD,(1,),ready=True);self.runtime.interact([10,20,30])
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertTrue(self.runtime.actors);self.assertIsNotNone(self.runtime.conversation)
        self.runtime.advance('welcome','leave')
        self.runtime.reconcile(WORLD,(1,),ready=True)
        self.assertFalse(self.runtime.actors);self.assertIsNone(self.runtime.conversation)
        self.assertEqual(len(self.backend.spawned),1)
    def test_changed_revision_requires_review_instead_of_silently_switching_content(self):
        self.runtime.document=None;self.library.packs[self.pack['id']]['revision']=2
        with self.assertRaisesRegex(ValueError,'revision changed'):self.runtime.select_playthrough(self.key)
    def test_loading_retirement_dismisses_conversation_even_if_cleanup_is_pending(self):
        self.runtime.reconcile(WORLD,(1,),ready=True);self.runtime.interact([10,20,30]);self.backend.hold=True
        self.assertFalse(self.runtime.reconcile(WORLD,(1,),ready=False))
        self.assertIsNone(self.runtime.conversation);self.assertIsNone(self.runtime.nearest([10,20,30]))
