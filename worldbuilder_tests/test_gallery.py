import importlib.util,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
s=importlib.util.spec_from_file_location('gallery',Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/gallery.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class GalleryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/"build");self.owned={};self.serial=0
  def spawn(asset,pose):
   if asset=='bad':raise ValueError('bad asset')
   self.serial+=1;k=str(self.serial);self.owned[k]={'asset':asset};return {'id':k}
  self.lib=SimpleNamespace(store=SimpleNamespace(root=Path(self.tmp.name)/'maps'),owned=self.owned,spawn=spawn,delete=lambda k:self.owned.pop(k),place=lambda k,p:None,world='/Game/Map',known={'a':{},'b':{}},message='')
  self.menu=SimpleNamespace(library=self.lib,mod=SimpleNamespace(last={'position':[0,0,0]}),bounds=lambda k:([1200,0,0],[50,100,75]))
  self.gallery=g.Gallery(self.menu)
 def tearDown(self):self.tmp.cleanup()
 def test_replacement_removes_only_gallery(self):
  self.owned['user']={};self.gallery.start(['a','b'],1);self.gallery.tick();old=list(self.gallery.owned);self.gallery.request(1)
  self.assertIn('user',self.owned);self.assertTrue(all(k not in self.owned for k in old));self.assertEqual(self.gallery.queue,['b'])
 def test_bad_asset_does_not_stop_batch(self):
  self.gallery.start(['bad','a']);self.gallery.tick();self.gallery.tick();self.assertEqual(len(self.gallery.failures),1);self.assertEqual(len(self.gallery.positions),1)
 def test_pause_retains_queue(self):
  self.gallery.start(['a']);self.gallery.paused=True;self.gallery.tick();self.assertEqual(self.gallery.queue,['a']);self.assertFalse(self.gallery.owned)
 def test_invalid_bounds_input(self):
  for size,spacing in [(101,600),(1,float('nan')),(1,0)]:
   with self.assertRaises(ValueError):self.gallery.start(['a'],size,spacing)

