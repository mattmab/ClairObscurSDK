import ctypes,importlib.util,random,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('native_cache_test',ROOT/'mods/E33WorldBuilder/thumbnail_cache.py');cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
DLL=ROOT/'build/release/thumbnail-worker-v2/thumbnail_worker.dll'
@unittest.skipUnless(DLL.exists(),'Build native image worker first')
class NativeCacheTests(unittest.TestCase):
 def test_pixels_equal_python_and_failed_input_keeps_sources(self):
  lib=ctypes.CDLL(str(DLL));fn=lib.compose_thumbnail;fn.argtypes=[ctypes.c_wchar_p]*3;fn.restype=ctypes.c_long
  rng=random.Random(42);base=bytes(3)+rng.randbytes(320*240*3-3);normal=bytes(3)+rng.randbytes(len(base)-3)
  with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder,patch.object(cache,'ROOT',Path(folder)),patch.object(cache,'native_composer',return_value=fn):
   root=Path(folder);key='a'*64
   def inputs():
    cache.write_png(root/(key+'.base.png'),base);cache.write_png(root/(key+'.normal.png'),normal)
   inputs();t=time.perf_counter();cache.compose_python(key);python_time=time.perf_counter()-t;expected=cache.read_png(root/(key+'.png'))
   inputs();t=time.perf_counter();cache.compose(key);native_time=time.perf_counter()-t
   self.assertEqual(expected,cache.read_png(root/(key+'.png')))
   (root/(key+'.base.rgb')).write_bytes(base);(root/(key+'.normal.rgb')).write_bytes(normal)
   cache.compose(key);self.assertEqual(expected,cache.read_png(root/(key+'.png')))
   print(f'Compose Python {python_time:.4f}s native {native_time:.4f}s ({python_time/native_time:.1f}x)',flush=True)
   inputs();(root/(key+'.normal.png')).write_bytes(b'broken')
   with self.assertRaises(RuntimeError):cache.compose(key)
   self.assertTrue((root/(key+'.base.png')).exists());self.assertFalse((root/(key+'.native.tmp')).exists())
   self.assertEqual(expected,cache.read_png(root/(key+'.png')))
