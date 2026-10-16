import importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('bgtest',ROOT/'mods/E33WorldBuilder/__init__.py',submodule_search_locations=[str(ROOT/'mods/E33WorldBuilder')])
# Import only the scheduler; package initialization is not needed for these tests.
import types
pkg=types.ModuleType('bgtest');pkg.__path__=[str(ROOT/'mods/E33WorldBuilder')];sys.modules['bgtest']=pkg
from bgtest.background_cache import BackgroundCache,cache

class BackgroundTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build');self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_input_and_pause_gate_work(self):
  bg=BackgroundCache(self.root);bg.last_input=0
  self.assertFalse(bg.input(True,10));self.assertFalse(bg.input(False,14));self.assertTrue(bg.input(False,15))
  bg.set_enabled(False);self.assertFalse(bg.input(False,20));self.assertFalse(BackgroundCache(self.root).enabled)
 def test_resume_skips_completed_and_failed_assets(self):
  rows=[dict(path='/Game/A.A',kind='mesh'),dict(path='/Game/B.B',kind='mesh'),dict(path='/Game/C.C',kind='mesh'),dict(path='/Game/Audio.Audio_C',kind='actor')]
  with patch.object(cache,'cached_png',return_value=False):
   bg=BackgroundCache(self.root);bg.sync(rows);self.assertEqual(bg.take(),'/Game/A.A');bg.finish('/Game/A.A','bad asset')
   self.assertEqual(bg.take(),'/Game/B.B');bg.interrupted('/Game/B.B');self.assertEqual(bg.take(),'/Game/B.B')
  with patch.object(cache,'cached_png',side_effect=lambda key:key==cache.thumbnail_key('/Game/B.B')):
   resumed=BackgroundCache(self.root);resumed.sync(rows);self.assertEqual(resumed.take(),'/Game/C.C')
   self.assertEqual(resumed.status()['total'],3)
   self.assertEqual(resumed.status()['cached'],1);self.assertEqual(resumed.status()['failed'],1)
 def test_expensive_steps_back_off(self):
  bg=BackgroundCache(self.root);bg.cost(1);self.assertGreaterEqual(bg.delay,4);bg.cost(9);self.assertEqual(bg.delay,30)

 def test_cheap_steps_have_short_cooldown_and_recover(self):
  bg=BackgroundCache(self.root);bg.cost(.01);self.assertEqual(bg.delay,.15)
  bg.cost(1);self.assertEqual(bg.delay,4)
  for _ in range(5):bg.cost(.01)
  self.assertEqual(bg.delay,.15)

 def test_afk_persists_and_removes_cooldown_but_keeps_input_gate(self):
  bg=BackgroundCache(self.root);bg.set_mode('afk');bg.cost(9)
  self.assertEqual(bg.delay,0);self.assertEqual(BackgroundCache(self.root).mode,'afk')
  bg.next_at=0
  self.assertFalse(bg.input(True,100));self.assertFalse(bg.input(False,104));self.assertTrue(bg.input(False,105))
  bg.set_enabled(False);self.assertFalse(bg.input(False,110));self.assertEqual(bg.poll_interval(),.5)
  bg.set_mode('idle');bg.cost(1);self.assertEqual(bg.delay,4)
 def test_invalid_mode_rejected(self):
  bg=BackgroundCache(self.root)
  with self.assertRaises(ValueError):bg.set_mode('turbo')
  self.assertEqual(bg.mode,'idle')

 def test_afk_fast_polling_only_when_enabled_and_idle(self):
  bg=BackgroundCache(self.root);bg.set_mode('afk')
  with patch('bgtest.background_cache.time.monotonic',return_value=100):
   bg.last_input=94;self.assertEqual(bg.poll_interval(),.05)
   bg.last_input=99;self.assertEqual(bg.poll_interval(),.5)
   bg.last_input=94;bg.set_enabled(False);self.assertEqual(bg.poll_interval(),.5)
