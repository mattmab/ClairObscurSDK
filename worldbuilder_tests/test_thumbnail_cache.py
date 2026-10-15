import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('thumbnail_cache',Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/thumbnail_cache.py');cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
class CacheTests(unittest.TestCase):
 def test_cached_png_uses_header_without_pixel_decode(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as root:
   with patch.object(cache,'ROOT',Path(root)):
    key='b'*64
    self.assertFalse(cache.cached_png(key))
    cache.write_png(Path(root)/(key+'.png'),bytes(320*240*3))
    with patch.object(cache,'read_png',side_effect=AssertionError('must not decode twice')):
     self.assertTrue(cache.cached_png(key))
    (Path(root)/(key+'.png')).write_bytes(b'broken')
    self.assertFalse(cache.cached_png(key))
 def test_png_roundtrip_and_neutral_background(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as root:
   with patch.object(cache,'ROOT',Path(root)):
    key='a'*64;base=bytes((160,120,80))*(320*240);normal=bytes((128,128,255))*(320*240)
    cache.write_png(Path(root)/(key+'.base.png'),base);cache.write_png(Path(root)/(key+'.normal.png'),normal)
    self.assertEqual(cache.read_png(Path(root)/(key+'.base.png')),base)
    out=cache.read_png(cache.compose(key));self.assertGreater(out[0],out[1]);self.assertGreater(out[1],out[2]);self.assertLessEqual(out[0],255)
    self.assertFalse((Path(root)/(key+'.base.png')).exists())
    cache.write_png(Path(root)/(key+'.base.png'),base);cache.write_png(Path(root)/(key+'.normal.png'),bytes(320*240*3))
    out=cache.read_png(cache.compose(key));self.assertNotEqual(out[:3],bytes((42,46,53)))
 def test_catalog_invalidation_and_corruption(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as root:
   with patch.object(cache,'ROOT',Path(root)),patch.object(cache,'build_key',return_value='build-a'):
    cache.write_catalog(['/Game/Props/Rock.Rock']);self.assertEqual(cache.read_catalog(),['/Game/Props/Rock.Rock'])
    with patch.object(cache,'build_key',return_value='build-b'):self.assertIsNone(cache.read_catalog())
    (Path(root)/'catalog.json').write_text('broken');self.assertIsNone(cache.read_catalog())
