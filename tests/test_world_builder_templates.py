import importlib, math, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mods'))
# Import pure helpers without executing the SDK mod entry point.
import types
pkg=types.ModuleType('template_test_pkg');pkg.__path__=[str(Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder')]
sys.modules['template_test_pkg']=pkg
t=importlib.import_module('template_test_pkg.templates')

class TemplateTests(unittest.TestCase):
    def test_live_bounds_move_resize_and_rotation(self):
        tool=object.__new__(t.Templates)
        tool.job=None;tool.points=[[0,0,0],[100,200,300]];tool.angles=[0,0,90]
        tool.library=SimpleNamespace(message='');tool.update_box=lambda:None
        tool.adjust_bounds('Resize',0,100)
        self.assertEqual(tool.points,[[-50,0,0],[150,200,300]])
        tool.adjust_bounds('Move',1,25)
        self.assertEqual(tool.points,[[-50,25,0],[150,225,300]])
        tool.adjust_bounds('Rotate',2,15)
        self.assertEqual(tool.angles,[0,0,105])
        original=[p[:] for p in tool.points]
        with self.assertRaises(ValueError):tool.adjust_bounds('Resize',0,-200)
        self.assertEqual(tool.points,original)
        tool.job={'scanning':True}
        with self.assertRaises(ValueError):tool.adjust_bounds('Move',0,10)

    def test_rotated_corner_move_keeps_opposite_corner_fixed(self):
        tool=object.__new__(t.Templates);tool.job=None;tool.angles=[15,25,40]
        tool.points=[[0,0,0],[100,200,300]];tool.library=SimpleNamespace(message='');tool.update_box=lambda:None
        q=t.region_quaternion(tool.angles)
        original=t.rotate_point([0,0,0],[50,100,150],q)
        selected=t.rotate_point([100,200,300],[50,100,150],q)
        tool.adjust_bounds('Move',0,10,7)
        low,high=tool.points;center=[(a+b)/2 for a,b in zip(low,high)]
        for actual,want in zip(t.rotate_point(low,center,q),original):self.assertAlmostEqual(actual,want)
        for actual,want in zip(t.rotate_point(high,center,q),[selected[0]+10,*selected[1:]]):self.assertAlmostEqual(actual,want)
        tool.adjust_bounds('Scale',3,10,7)
        low,high=tool.points;center=[(a+b)/2 for a,b in zip(low,high)]
        for actual,want in zip(t.rotate_point(low,center,q),original):self.assertAlmostEqual(actual,want)

    def test_bounds_transform_reuses_edge_objects(self):
        from unittest.mock import patch
        tool=object.__new__(t.Templates);tool.lines=[str(i) for i in range(12)]
        tool.points=[[0,0,0],[100,200,300]];tool.angles=[0,0,45]
        tool.library=SimpleNamespace(owned={key:{} for key in tool.lines})
        module=types.ModuleType('template_test_pkg.bulk');module.prepare=lambda library:None
        with patch.dict(sys.modules,{'template_test_pkg.bulk':module}):tool.update_box()
        self.assertEqual([key for key,_ in tool.line_moves],tool.lines)
        self.assertEqual(tool.line_queue,[])
        self.assertEqual(len(tool.line_moves),12)

    def test_reposition_accepts_new_target_during_initial_placement(self):
        tool=object.__new__(t.Templates);tool.queue=[{'pending':True}]
        tool.moves=[('old',[])];tool.origin=[0,0,0]
        row={'transform':[0,0,0,1,10,20,30,0,1,1,1,0]}
        tool.draft=[('existing',row)];tool.library=SimpleNamespace(message='')
        tool.reposition([400,400,0],15)
        self.assertEqual(tool.delta,[400,400,0]);self.assertEqual(tool.yaw,15)
        self.assertEqual(len(tool.moves),1);self.assertEqual(tool.moves[0][0],'existing')
        self.assertTrue(tool.queue)

    def test_group_yaw_preserves_spacing_rotation_and_scale(self):
        p=[0.,0.,0.,1.,400.,400.,25.,0.,2.,3.,4.,0.]
        q=t.placed(p,[100.,200.,300.],[10.,20.,30.],90.)
        for a,b in zip(q[4:7],[-290.,620.,355.]):self.assertAlmostEqual(a,b)
        self.assertEqual(q[8:11],[2.,3.,4.]);self.assertAlmostEqual(q[2],math.sqrt(.5));self.assertAlmostEqual(q[3],math.sqrt(.5))
        self.assertEqual(p[4:7],[400.,400.,25.])
    def test_reposition_is_absolute_not_cumulative(self):
        p=[0.,0.,0.,1.,1.,2.,3.,0.,1.,1.,1.,0.]
        self.assertEqual(t.placed(p,[0.,0.,0.],[400.,400.,0.],0.),t.placed(p,[0.,0.,0.],[400.,400.,0.],0.))
        with self.assertRaises(ValueError):t.placed(p,[0.,0.,0.],[float('nan'),0.,0.],0.)
    def test_region_boundary_inclusive(self):
        self.assertTrue(t.inside([0,10,5],[0,0,0],[10,10,10]))
        self.assertFalse(t.inside([11,10,5],[0,0,0],[10,10,10]))
    def test_template_roundtrip_preserves_transform_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            store=t.MapStore(d);p=[0.,0.,0.,1.,1.,2.,3.,0.,-2.,3.,4.,0.]
            data=dict(format=t.FORMAT,version=1,name='Structure',world='/Game/Test.Test',objects=[dict(id='a'*32,kind='mesh',asset='/Game/Chair.Chair',transform=p)],assets=['/Game/Chair.Chair'])
            key=store.save(data);self.assertEqual(store.read(key),data)
            with self.assertRaises(ValueError):store.read('../outside')
    def test_apply_only_commits_current_draft(self):
        with tempfile.TemporaryDirectory() as d:
            lib=SimpleNamespace(mod=None,store=SimpleNamespace(root=Path(d)/'maps'),owned={'original':{},'copy':{'duplication_preview':True}})
            tool=t.Templates(lib);tool.draft=[('copy',{})];tool.apply()
            self.assertEqual(lib.owned,{'original':{},'copy':{}});self.assertFalse(tool.draft)
    def test_apply_waits_for_all_group_moves(self):
        with tempfile.TemporaryDirectory() as d:
            lib=SimpleNamespace(mod=None,store=SimpleNamespace(root=Path(d)/'maps'))
            tool=t.Templates(lib);tool.moves=[('copy',[])];tool.draft=[('copy',{})]
            with self.assertRaises(ValueError):tool.apply()
    def test_failed_partial_placement_cannot_be_applied(self):
        with tempfile.TemporaryDirectory() as d:
            lib=SimpleNamespace(mod=None,store=SimpleNamespace(root=Path(d)/'maps'),owned={'copy':{'duplication_preview':True}})
            tool=t.Templates(lib);tool.draft=[('copy',{})];tool.failed=True
            with self.assertRaises(ValueError):tool.apply()
            self.assertTrue(lib.owned['copy']['duplication_preview'])
    def test_cancel_discovery_preserves_corners(self):
        with tempfile.TemporaryDirectory() as d:
            lib=SimpleNamespace(mod=None,store=SimpleNamespace(root=Path(d)/'maps'))
            tool=t.Templates(lib);tool.points=[[1,2,3],[4,5,6]];tool.job={'objects':None}
            tool.cancel_scan()
            self.assertIsNone(tool.job);self.assertEqual(tool.points,[[1,2,3],[4,5,6]])
            tool.scan_worker.shutdown(wait=False)
    def test_scan_drains_cached_hits_in_one_batch(self):
        from unittest.mock import patch
        values=types.ModuleType('expedition33.values');values.read_values_with_references=lambda *a,**k:None;values.read_values_many=lambda *a,**k:{}
        with tempfile.TemporaryDirectory() as d,patch.dict(sys.modules,{'expedition33.values':values}):
            lib=SimpleNamespace(mod=None,store=SimpleNamespace(root=Path(d)/'maps'))
            tool=t.Templates(lib);ident=(1,2,3);p=[0.,0.,0.,1.,1.,2.,3.,0.,1.,1.,1.,0.]
            tool.catalog=SimpleNamespace(by_index={1:object()})
            tool.job=dict(objects=[1],index=1,pending=[(ident,p)]*64,assets={ident:'/Game/Test.Test'},rows=[],low=[0,0,0],high=[10,10,10])
            tool.scan_one()
            self.assertEqual(len(tool.job['pending']),0);self.assertEqual(len(tool.job['rows']),64)
            tool.scan_worker.shutdown(wait=False)
    def test_rotated_region_rejects_surrounding_aabb_space(self):
        low,high=[-10,-1,-1],[10,1,1]
        self.assertTrue(t.region_contains([0,9,0],low,high,[0,0,90]))
        self.assertFalse(t.region_contains([9,0,0],low,high,[0,0,90]))
        self.assertTrue(t.region_contains([0,0,9],low,high,[0,90,0]))
        self.assertFalse(t.region_contains([0,9,0],low,high,[0,90,0]))
    def test_region_rotation_inverse_all_axes(self):
        q=t.region_quaternion([23,37,61]);center=[5,6,7];p=[8,9,10]
        v=t.rotate_point(p,center,q);q[:3]=[-x for x in q[:3]]
        restored=t.rotate_point(v,center,q)
        for a,b in zip(p,restored):self.assertAlmostEqual(a,b)
if __name__=='__main__':unittest.main()
