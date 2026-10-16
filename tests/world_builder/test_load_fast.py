import importlib,sys,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2]
pkg=types.ModuleType('load_fast_test');pkg.__path__=[str(ROOT/'mods/E33WorldBuilder')];sys.modules[pkg.__name__]=pkg
library=importlib.import_module(pkg.__name__+'.library')
bulk=importlib.import_module(pkg.__name__+'.bulk')
class LoadTests(unittest.TestCase):
 def test_cached_mesh_load_avoids_full_catalog_and_preserves_saved_id(self):
  asset='/Game/Rock.Rock';world='/Game/Map.Map';key='a'*32
  data=dict(format=library.FORMAT,version=1,name='Test',world=world,assets=[asset],objects=[dict(id=key,kind='mesh',asset=asset,transform=[0.,0.,0.,1.,1.,2.,3.,0.,1.,1.,1.,0.])])
  lib=library.Library.__new__(library.Library)
  lib.mod=types.SimpleNamespace(active=True,last={})
  lib.clear_preview=Mock();lib.context=Mock(return_value=(None,None,None,world));lib.store=types.SimpleNamespace(read=lambda _:data)
  lib.owned={};lib.rows=[dict(path=asset,kind='mesh')];lib.known={asset:lib.rows[0]};lib.bulk_indices={asset:0}
  def spawn(*args,**kwargs):
   lib.owned['temporary']={'id':'temporary','asset':asset,'world':world}
   return [{'id':'temporary'}]
  with patch.object(library,'capture',side_effect=AssertionError('full scan')),patch.object(bulk,'prepare'),patch.object(bulk,'spawn_batch',side_effect=spawn):
   self.assertEqual(lib._load(key)['objects'],1)
  self.assertEqual(list(lib.owned),[key]);self.assertEqual(lib.owned[key]['id'],key)
