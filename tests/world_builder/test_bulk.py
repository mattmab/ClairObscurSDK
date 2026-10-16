import importlib.util,sys,types,struct,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder'
pkg=types.ModuleType('bulk_test_package');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
s=importlib.util.spec_from_file_location(pkg.__name__+'.bulk',ROOT/'bulk.py');bulk=importlib.util.module_from_spec(s);s.loader.exec_module(bulk)
class BulkTests(unittest.TestCase):
 def test_export_5000_preserves_all_transforms(self):
  asset='/Game/Props/Rock.Rock';world='/Game/Map.Map';owned={f'{i:032x}':dict(id=f'{i:032x}',kind='mesh',asset=asset,component=(i,7,10000+i),actor=(i+5000,7,20000+i),world=world) for i in range(5000)}
  pages=[];mod=types.SimpleNamespace()
  def command(op,registry_offset):
   self.assertEqual(op,51);pages.append(registry_offset);raw=bytearray(20984);end=min(5000,registry_offset+128)
   struct.pack_into('<III',raw,3560,end-registry_offset,5000,end)
   for n,i in enumerate(range(registry_offset,end)):
    at=4096+128*n;struct.pack_into('<iiQ12dI',raw,at,i,7,10000+i,0,0,0,1,i,i*2,0,0,1,1,1,0,1)
   mod.last_raw=raw
  mod.command=command
  lib=types.SimpleNamespace(context=lambda:(None,None,None,world),owned=owned,mod=mod,preview_key=None)
  with patch.dict(sys.modules,{'expedition33.catalog':types.SimpleNamespace(capture_selected=None),'expedition33.values':types.SimpleNamespace(read_values_with_references=None)}):data=bulk.snapshot(lib,'Large scene')
  self.assertEqual(len(data['objects']),5000);self.assertEqual(len(pages),40);self.assertEqual(data['objects'][-1]['transform'][4:6],[4999,9998])
 def test_partial_delete_removes_only_acknowledged_keys(self):
  lib=types.SimpleNamespace(owned={str(i):{'actor':(i,1,100+i)} for i in range(5)},mod=types.SimpleNamespace())
  calls=[]
  def command(op,bulk):
   calls.append(bulk);raw=bytearray(20984);struct.pack_into('<I',raw,3560,1);lib.mod.last_raw=raw
  lib.mod.command=command;bulk.delete_many(lib,['1','3']);self.assertEqual(set(lib.owned),{'0','2','4'});self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()
