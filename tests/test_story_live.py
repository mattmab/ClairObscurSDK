import importlib
import unittest
from types import SimpleNamespace
from test_story_runtime import WORLD
import test_story_runtime as fixtures
from test_story_conversations import AvailableDriver
live=importlib.import_module('story_packs_test.live')

class LiveStoryTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp
    def owner(self):
        self.reads=0;self.drivers=[]
        def read():self.reads+=1;return self.key
        def driver(key,npc):
            value=AvailableDriver();self.drivers.append(value);return value
        return live.LiveStory(self.library,self.state,SimpleNamespace(read=read,close=lambda:True),self.backend,driver)

    def test_read_once_per_admitted_visit_and_restore_on_same_map_reload(self):
        owner=self.owner();self.assertTrue(owner.reconcile(WORLD,(1,),ready=True))
        self.assertTrue(owner.reconcile(WORLD,(1,),ready=True));self.assertEqual(self.reads,1)
        self.assertEqual(len(self.backend.spawned),1)
        self.assertTrue(owner.reconcile(WORLD,(2,),ready=True));self.assertEqual(self.reads,2)
        self.assertEqual(len(self.backend.spawned),2);self.assertEqual(len(self.backend.retired),1)

    def test_dialogue_cleanup_blocks_actor_retirement_and_new_world(self):
        owner=self.owner();owner.reconcile(WORLD,(1,),ready=True);self.drivers[0].hold=True
        self.assertFalse(owner.reconcile('/Game/Other.Other',(2,),ready=True))
        self.assertFalse(self.backend.retired);self.assertEqual(self.reads,1)
        self.drivers[0].hold=False
        self.assertTrue(owner.reconcile('/Game/Other.Other',(2,),ready=True));self.assertEqual(self.reads,2)

    def test_disabled_or_loading_world_never_reads_a_save(self):
        owner=self.owner();self.assertTrue(owner.reconcile(None,None,ready=False))
        self.assertEqual(self.reads,0);self.assertFalse(self.backend.spawned)

    def test_failed_placement_reports_owner_without_replaying_construction(self):
        owner=self.owner();self.backend.fail=True
        self.assertFalse(owner.reconcile(WORLD,(1,),ready=True))
        self.assertIn('boy-here: partial construction',owner.error)
        self.assertFalse(owner.reconcile(WORLD,(1,),ready=True))
        self.assertEqual(len(self.backend.spawned),1)
        self.backend.fail=False
        self.assertTrue(owner.reconcile(WORLD,(2,),ready=True))
        self.assertIsNone(owner.error)
        self.assertEqual(len(self.backend.retired),1)

    def unbound_owner(self):
        self.bound=None
        def bind(key):self.bound=key;return key
        identity=SimpleNamespace(read=lambda:self.bound,bind=bind,close=lambda:True)
        return live.LiveStory(self.library,self.state,identity,self.backend,lambda key,npc:AvailableDriver())

    def test_unassigned_save_offers_selection_without_writing_until_choice(self):
        owner=self.unbound_owner();owner.reconcile(WORLD,(1,),ready=True)
        request=owner.choices();self.assertIsNotNone(request);self.assertIsNone(self.bound)
        self.assertFalse(self.backend.spawned)
        owner.choose(request,self.pack['id']);self.assertIsNotNone(self.bound)
        self.assertEqual(self.state.get(self.bound)['pack'],self.pack['id'])
        owner.reconcile(WORLD,(1,),ready=True);self.assertEqual(len(self.backend.spawned),1)

    def test_old_world_selection_cannot_bind_the_next_save(self):
        owner=self.unbound_owner();owner.reconcile(WORLD,(1,),ready=True);request=owner.choices()
        owner.reconcile(WORLD,(2,),ready=True)
        with self.assertRaises(ValueError):owner.choose(request,self.pack['id'])
        self.assertIsNone(self.bound)

    def test_missing_pack_and_changed_identity_do_not_create_selection(self):
        owner=self.unbound_owner();owner.reconcile(WORLD,(1,),ready=True);request=owner.choices()
        with self.assertRaises(ValueError):owner.choose(request,'not-installed')
        self.assertIsNone(self.bound)
        self.bound='e33c5701'+'ffffffff'*3
        with self.assertRaises(ValueError):owner.choose(request,self.pack['id'])
        self.assertIsNone(self.state.get(self.bound))
