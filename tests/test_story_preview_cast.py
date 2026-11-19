import copy
import importlib
import unittest
from test_story_packs import sample

preview_document=importlib.import_module('story_packs_test.preview').preview_document
WORLD='/Game/Test/Map.Map'


class PreviewCastTests(unittest.TestCase):
    def setUp(self):
        self.document=sample()
        self.document['characters']['lune']=dict(name='Lune',profile='lune')
        self.owner=dict(id='boy-here',world=WORLD,character='boy',dialogue='first-meeting',
            position=[1,2,3],yaw=0,radius=200,requires={})
        self.other=dict(self.owner,id='lune-here',character='lune',position=[4,5,6])
        self.document['placements']=[self.owner,self.other]
        self.document['dialogues']['first-meeting']['nodes']['story']['speaker']='lune'

    def test_preview_keeps_reachable_cast_and_replaces_owner_without_mutating_saved_pack(self):
        before=copy.deepcopy(self.document)
        moved=dict(self.owner,position=[100,200,300])
        result=preview_document(self.document,moved)
        rows={p['id']:p for p in result['placements']}
        self.assertEqual(set(rows),{'boy-here','lune-here'})
        self.assertEqual(rows['boy-here']['position'],[100,200,300])
        self.assertEqual(rows['lune-here'],self.other)
        self.assertEqual(self.document,before)

    def test_missing_and_other_map_speakers_are_explained_before_native_construction(self):
        self.other['world']='/Game/Elsewhere.Map'
        with self.assertRaisesRegex(ValueError,'Place Lune on this map'):
            preview_document(self.document,self.owner)

    def test_conditional_placements_use_preview_flags_and_duplicate_active_cast_is_rejected(self):
        self.other['requires']={'met-lune':True}
        with self.assertRaisesRegex(ValueError,'Place Lune'):
            preview_document(self.document,self.owner)
        self.assertEqual(len(preview_document(self.document,self.owner,{'met-lune':True})['placements']),2)
        self.document['placements'].append(dict(self.other,id='duplicate'))
        with self.assertRaisesRegex(ValueError,'More than one placement for Lune'):
            preview_document(self.document,self.owner,{'met-lune':True})

    def test_unreachable_speakers_and_unused_placements_are_not_spawned(self):
        self.document['dialogues']['first-meeting']['nodes']['welcome']['choices']=[]
        result=preview_document(self.document,self.owner)
        self.assertEqual(result['placements'],[self.owner])

    def test_interacting_owner_wins_over_other_placements_of_same_character(self):
        self.document['placements'].append(dict(self.owner,id='other-boy'))
        result=preview_document(self.document,self.owner)
        self.assertEqual({p['id'] for p in result['placements']},{'boy-here','lune-here'})
