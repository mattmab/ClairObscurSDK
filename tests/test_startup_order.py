import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from expedition33.startup_order import StartupOrder,StartupGate,DEFAULT_ORDER

class OrderTests(unittest.TestCase):
 def test_defaults_skip_absent_and_preserve_other_order(self):
  with tempfile.TemporaryDirectory() as root:
   s=StartupOrder(Path(root)/'startup-order.json')
   self.assertEqual(s.ordered(['other','e33.map-overlays','e33.world-builder','last']),[*DEFAULT_ORDER,'other','last'])
   self.assertEqual(s.ordered(['other']),['other'])
   self.assertEqual(json.loads(s.path.read_text())['order'],list(DEFAULT_ORDER))
 def test_custom_persistence_dependency_and_unknown_ids(self):
  with tempfile.TemporaryDirectory() as root:
   s=StartupOrder(Path(root)/'order.json');s.save(['custom','e33.map-overlays','missing','e33.world-builder'])
   self.assertEqual(StartupOrder(s.path).ordered(['e33.world-builder','other','custom','e33.map-overlays']),['custom',*DEFAULT_ORDER,'other'])
   self.assertIn('missing',s.read())
 def test_bad_file_preserved_and_falls_back(self):
  with tempfile.TemporaryDirectory() as root:
   s=StartupOrder(Path(root)/'order.json');s.path.write_text('{bad')
   with self.assertLogs(level='WARNING'):self.assertEqual(s.read(),list(DEFAULT_ORDER))
   self.assertEqual(s.path.read_text(),'{bad')
 def test_readiness_releases_on_complete_failure_or_deadline(self):
  gate=StartupGate();self.assertFalse(gate.pending(0))
  mod=NS(startup_pending=lambda:True);gate.arm(mod,0)
  self.assertTrue(gate.pending(2));self.assertFalse(gate.pending(10))
  gate.arm(mod,11);mod.startup_pending=lambda:False;gate.arm(mod,12)
  self.assertFalse(gate.pending(13))
  def fail():raise RuntimeError('failed')
  gate.arm(NS(startup_pending=fail),20)
  with self.assertLogs(level='ERROR'):self.assertFalse(gate.pending(21))
