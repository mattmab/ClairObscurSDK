import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('overlay_state',ROOT/'mods/E33MapOverlays/state.py')
state=importlib.util.module_from_spec(spec);spec.loader.exec_module(state)

class OverlayTests(unittest.TestCase):
    def test_independent_world_assignments_persist_and_clear(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            p=pathlib.Path(folder)/'settings.json';a=state.Assignments(p)
            a.select('/Game/A.A','a'*32);a.select('/Game/B.B','b'*32)
            a=state.Assignments(p);self.assertEqual(a.values,{'/Game/A.A':'a'*32,'/Game/B.B':'b'*32})
            a.select('/Game/A.A',None)
            self.assertEqual(state.Assignments(p).values,{'/Game/B.B':'b'*32})
    def test_invalid_id_does_not_change_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            p=pathlib.Path(folder)/'settings.json';a=state.Assignments(p);a.select('/Game/A.A','a'*32)
            before=p.read_bytes()
            with self.assertRaises(ValueError):a.select('/Game/A.A','../save')
            self.assertEqual(p.read_bytes(),before)
    def test_once_per_visit_same_world_reload_and_travel(self):
        v=state.Visits();a=dict(world='/Game/A.A',visit=[1,2,3],ready=True)
        self.assertFalse(v.observe(a,0));self.assertFalse(v.observe(a,1));self.assertTrue(v.observe(a,2))
        v.attempted=True
        self.assertFalse(v.observe(a,10));self.assertFalse(v.observe(None,11));self.assertFalse(v.observe(a,20))
        reload=dict(a,visit=[1,4,5])
        self.assertFalse(v.observe(reload,21));self.assertTrue(v.observe(reload,23))
        b=dict(world='/Game/B.B',visit=[6,7,8],ready=True)
        self.assertFalse(v.observe(b,24));self.assertTrue(v.observe(b,26))
    def test_loading_or_mounted_pawn_delays_attempt(self):
        v=state.Visits();a=dict(world='/Game/A.A',visit=[1,2,3],ready=True)
        v.observe(a,0);self.assertFalse(v.observe(dict(a,ready=False),5))
        self.assertFalse(v.observe(a,6));self.assertTrue(v.observe(a,7))

class OverlayIntegrationTests(unittest.TestCase):
    def test_companion_filters_saves_and_refuses_foreign_assignment(self):
        import sys,types
        from unittest.mock import Mock
        sys.path.insert(0,str(ROOT/'src'))
        name='overlay_companion_test'
        spec=importlib.util.spec_from_file_location(name,ROOT/'mods/E33MapOverlays/mod.py',submodule_search_locations=[str(ROOT/'mods/E33MapOverlays')])
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
        mod=module.Mod()
        current=dict(world='/Game/A.A',visit=[1,2,3],ready=True)
        wb=types.SimpleNamespace(overlay_context=lambda:current,library=types.SimpleNamespace(store=types.SimpleNamespace(list=lambda:[dict(id='a'*32,world='/Game/A.A'),dict(id='b'*32,world='/Game/B.B')])))
        mod.builder=lambda:wb
        mod.refresh()
        self.assertEqual([r['id'] for r in mod.rows],['a'*32])
        mod.assignments=Mock()
        with self.assertRaises(ValueError):mod.choose('b'*32)
        mod.assignments.select.assert_not_called()
        wb.load_overlay=Mock(side_effect=RuntimeError('unavailable'))
        mod.apply('a'*32)
        self.assertTrue(mod.visits.attempted)
        self.assertIn('unavailable',mod.message)
        self.assertFalse(mod.visits.observe(current,1))
        mod.visits.attempted=True
        self.assertFalse(mod.visits.observe(current,10))
