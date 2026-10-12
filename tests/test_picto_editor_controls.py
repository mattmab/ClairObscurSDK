import sys, importlib.util, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('picto_control_test', ROOT / 'mods/PictoEditor/mod.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Controls(unittest.TestCase):
    def editor(self):
        e = mod.StockEditor.__new__(mod.StockEditor)
        e.selection = object(); e.character = object()
        e.multipliers = {1: .9, 6: 0., 8: 1.2, 9: .8}
        e.stats = {1: 3389, 8: 917, 9: 35}
        e.stat_rows = {k: (object(), k, n) for k, n in ((1,'Health'),(6,'Defense'),(8,'Speed'),(9,'Crit Rate'))}
        e.stat_key = 1; e.pending = None; e.timings = {}
        e.mode='stat';e.level=33;e.extra={'cost':40,'steps':246,'threshold':4,'mastered':True}
        e.progression_available=True;e.cost_available=True
        e.level_label='level';e.mastery_label='mastery';e.cost_label='cost';e.adjust_labels=['minus','plus','apply']
        e.value_label = 'value'; e.status_label = 'status'; e.rendered = {}
        e.text = lambda label, text: e.rendered.update({label: text})
        e.operation = lambda: self.fail('Draft unexpectedly started a native reader')
        return e
    def test_direct_selection_and_zero_stat(self):
        e = self.editor(); e.activate(1)
        self.assertEqual(e.stat_key, 6)
        self.assertEqual(e.rendered[6], '> Defense: 0')
    def test_draft_is_local_and_bounded(self):
        e = self.editor(); e.stat_key = 6
        e.activate(4); self.assertEqual(e.pending, 0)
        e.activate(5); self.assertEqual(e.pending, .1)
        self.assertEqual(e.multipliers[6], 0)
        e.pending = 10; e.activate(5); self.assertEqual(e.pending, 10)
    def test_row_switch_discards_draft(self):
        e = self.editor(); e.pending = 5
        e.activate(3)
        self.assertIsNone(e.pending)
        self.assertEqual(e.rendered[9], '> Crit Rate: 35%')
    def test_no_selection_cannot_stage(self):
        e = self.editor(); e.selection = None; e.activate(5)
        self.assertIsNone(e.pending); self.assertEqual(e.rendered, {})
    def test_cost_selection_and_local_draft(self):
        e=self.editor();e.activate(9);e.activate(4)
        self.assertEqual((e.mode,e.pending),('cost',39))
        self.assertEqual(e.extra['cost'],40)
        e.pending=0;e.activate(4);self.assertEqual(e.pending,0)
        e.pending=100;e.activate(5);self.assertEqual(e.pending,100)
        e.activate(0);self.assertIsNone(e.pending)
    def test_cost_unavailable_is_not_selectable(self):
        e=self.editor();e.cost_available=False;e.activate(9)
        self.assertEqual(e.mode,'stat')
    def test_mastery_reset_and_master_with_large_progress(self):
        e=self.editor();e.activate(8);e.activate(4);self.assertEqual(e.pending,0)
        e.activate(5);self.assertEqual(e.pending,4)

if __name__ == '__main__': unittest.main()
