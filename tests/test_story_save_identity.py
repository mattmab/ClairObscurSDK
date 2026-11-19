import importlib
import unittest
import uuid
from test_story_packs import storage

identity=importlib.import_module('story_packs_test.save_identity')


class SaveIdentityTests(unittest.TestCase):
    def test_normal_history_is_preserved_and_only_one_marker_is_planned(self):
        entries=[(uuid.uuid4().hex,3),(uuid.uuid4().hex,0),('0'*32,0)]
        before=list(entries);key=identity.new_identity()
        self.assertEqual(identity.resolve(entries),None)
        addition=identity.plan(entries,key)
        self.assertEqual(entries,before)
        self.assertEqual(identity.resolve(entries+[addition]),key)
        self.assertIsNone(identity.plan(entries+[addition],key))

    def test_save_copy_retains_identity_without_slot_or_process_identity(self):
        key=identity.new_identity();copied=list([identity.marker(key)])
        self.assertEqual(identity.resolve(copied),key)
        self.assertEqual(storage.playthrough_key(key),key)

    def test_conflicting_markers_cannot_select_a_story_or_be_overwritten(self):
        one=identity.new_identity();two=identity.new_identity()
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            identity.resolve([identity.marker(one),identity.marker(two)])
        with self.assertRaisesRegex(ValueError,'different'):
            identity.plan([identity.marker(one)],two)

    def test_malformed_marker_and_duplicate_entries_are_not_new_saves(self):
        key=identity.new_identity()
        for entries in ([(key,0)],[(key,True)],[(key,1<<31)],
                        [identity.marker(key),identity.marker(key)]):
            with self.assertRaises(ValueError):identity.resolve(entries)
        with self.assertRaises(ValueError):identity.marker(uuid.uuid4().hex)
