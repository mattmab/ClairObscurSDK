import math
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]
package=types.ModuleType('directional_test_builder');package.__path__=[str(ROOT/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from directional_test_builder.directional import offsets, DirectionalCopies
from directional_test_builder.library import Library

POSE=[0.,0.,0.,1.,10.,20.,30.,0.,2.,3.,4.,0.]

class DirectionalTests(unittest.TestCase):
    def test_all_six_directions_and_even_spacing(self):
        for axis in 'XYZ':
            for sign in (-1,1):
                result=offsets(POSE,axis,sign,3,25.)
                self.assertEqual(result,[tuple(sign*25*i if j=='XYZ'.index(axis) else 0. for j in range(3)) for i in (1,2,3)])
    def test_local_rotated_axis_ignores_scale(self):
        pose=POSE.copy();pose[:4]=[0.,0.,math.sqrt(.5),math.sqrt(.5)]
        result=offsets(pose,'X',1,1,100.,True)[0]
        for actual,expected in zip(result,(0,100,0)):self.assertAlmostEqual(actual,expected)
    def test_invalid_requests(self):
        for count,spacing in ((0,100),(251,100),(1.5,100),(1,0),(1,float('nan')),(1,float('inf'))):
            with self.assertRaises(ValueError):offsets(POSE,'X',1,count,spacing)
    def test_copy_preserves_pose_and_source(self):
        source=dict(id='original',asset='mesh',transform=POSE.copy())
        lib=Mock();lib.spawn.return_value={'id':'copy'}
        Library.duplicate(lib,'original',(5.,-10.,15.),source)
        pose=lib.spawn.call_args.args[1]
        self.assertEqual(pose[:4],POSE[:4]);self.assertEqual(pose[8:11],POSE[8:11])
        self.assertEqual(pose[4:7],[15.,10.,45.]);self.assertEqual(source['transform'],POSE)
    def test_queue_duplicates_only_fixed_source_and_tracks_progress(self):
        source=dict(id='original',asset='mesh',transform=POSE.copy())
        lib=Mock(owned={'original':{}},preview_key=None,world='map')
        lib.snapshot.return_value={'objects':[source,dict(id='other',transform=POSE)]}
        work=DirectionalCopies(lib);work.start('original','X',1,2,100.)
        work.poll();self.assertEqual(len(work.pending),1)
        lib.selected='other';work.poll()
        self.assertEqual([c.args[0] for c in lib.duplicate.call_args_list],['original','original'])
        self.assertEqual([c.args[1] for c in lib.duplicate.call_args_list],[(100.,0.,0.),(200.,0.,0.)])
        self.assertEqual(lib.selected,'original')
    def test_deleted_source_cancels_pending_copies(self):
        lib=Mock(owned={'original':{}},preview_key=None,world='map')
        lib.snapshot.return_value={'objects':[dict(id='original',transform=POSE)]}
        work=DirectionalCopies(lib);work.start('original','Z',1,2,100.)
        lib.owned.clear();work.poll();lib.duplicate.assert_not_called();self.assertFalse(work.pending)


class DraftTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        from directional_test_builder.directional import DuplicationDraft
        self.lib=Mock(owned={'source':{}},preview_key=None,world='map')
        self.lib.snapshot.return_value={'objects':[dict(id='source',asset='mesh',transform=POSE.copy())]}
        self.number=0
        def spawn(key,offset,source):
            self.number+=1;name='copy'+str(self.number);self.lib.owned[name]={};return {'id':name}
        self.lib.duplicate.side_effect=spawn
        def delete(lib,keys):
            for key in keys:lib.owned.pop(key,None)
        self.clean=patch('directional_test_builder.bulk.delete_many',side_effect=delete);self.clean.start();self.addCleanup(self.clean.stop)
        self.draft=DuplicationDraft(self.lib);self.draft.begin('source')
    def test_compound_preview_apply_and_close(self):
        self.draft.preview(2,[400.,400.,0.]);self.draft.poll()
        with self.assertRaises(ValueError):self.draft.apply()
        self.draft.poll()
        self.assertEqual([c.args[1] for c in self.lib.duplicate.call_args_list],[(400.,400.,0.),(800.,800.,0.)])
        self.assertTrue(self.lib.owned['copy1']['duplication_preview'])
        self.assertEqual(self.draft.apply(),2);self.draft.cancel()
        self.assertEqual(set(self.lib.owned),{'source','copy1','copy2'})
        self.assertNotIn('duplication_preview',self.lib.owned['copy1'])
    def test_adjust_replaces_draft_and_cancel_preserves_original(self):
        self.draft.preview(1,[400.,0.,0.]);self.draft.poll()
        self.draft.preview(1,[400.,400.,0.]);self.assertNotIn('copy1',self.lib.owned)
        self.draft.poll();self.draft.cancel()
        self.assertEqual(set(self.lib.owned),{'source'})
    def test_invalid_edit_keeps_existing_preview(self):
        self.draft.preview(1,[400.,0.,0.]);self.draft.poll()
        with self.assertRaises(ValueError):self.draft.preview(1,[float('nan'),0.,0.])
        self.assertIn('copy1',self.lib.owned)
