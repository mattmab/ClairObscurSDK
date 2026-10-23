import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import sys,tempfile,unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('map_prepare_candidate',ROOT/'mods/MapTravel/mod.py',submodule_search_locations=[str(ROOT/'mods/MapTravel')])
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.path=self.root/'Manifest_UFSFiles_Win64.txt';self.path.write_text('Sandfall/Content/Levels/Test/Level_Test.umap\tdate\n')
  self.patch=patch.object(m,'game_root',return_value=self.root);self.patch.start();self.addCleanup(self.patch.stop)
 def test_prepare_reads_only_manifest_without_process_or_session(self):
  model=m.Mod()
  with patch.object(m,'routes',side_effect=AssertionError('no engine reads')):
   model.prepare_startup(object())
  self.assertEqual(len(model._prepared_maps),1);self.assertIsNone(model.session)
 def test_activation_copies_prepared_rows_and_still_reads_routes_fresh(self):
  model=m.Mod();model.prepare_startup(object());session=Mock(pid=7)
  with patch.object(m,'available',return_value=True),patch.object(m,'routes',return_value=()) as routes,patch.object(model,'_new_pause_entry'),patch.object(m,'installed_maps',side_effect=AssertionError('no repeated manifest parse')):
   model.enable(session);model.maps[0]['normal_route']='old';model.enable(session)
  self.assertEqual(routes.call_count,2);self.assertIsNone(model.maps[0]['normal_route'])
  self.assertNotIn('normal_route',dict(model._prepared_maps[0]))
 def test_changed_manifest_refreshes_before_activation(self):
  model=m.Mod();model.prepare_startup(object())
  self.path.write_text('Sandfall/Content/Levels/Test/Level_LongReplacement.umap\tdate\n')
  maps=model._activation_maps();self.assertTrue(maps[0]['package'].endswith('Level_LongReplacement'))
 def test_legacy_enable_without_preparation_still_discovers_maps(self):
  model=m.Mod();self.assertEqual(len(model._activation_maps()),1)
if __name__=='__main__':unittest.main()
