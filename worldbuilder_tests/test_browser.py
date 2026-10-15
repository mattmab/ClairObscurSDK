import importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('browser',Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/browser.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class BrowserTests(unittest.TestCase):
 def test_folders_global_search_and_persistent_favorites(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as root:
   b=module.Browser(root)
   assets=[dict(kind='mesh',name='Rock',path='/Game/Props/Rock.Rock'),dict(kind='mesh',name='Rock2',path='/Game/Props/Sub/Rock2.Rock2'),dict(kind='actor',name='Lamp',path='/Game/Actors/Lamp.Lamp_C')]
   rows=b.rows(assets);self.assertEqual([r['name'] for r in rows],['Rock','Rock2'])
   self.assertEqual(len(b.rows(assets,query='ROCK')),2)
   self.assertEqual([r['kind'] for r in b.rows(assets,folder='/Game/Props/')],['mesh','mesh'])
   b.favorite(assets[0]['path']);self.assertEqual(module.Browser(root).rows(assets,favorites=True),assets[:1])
   b.favorite(assets[0]['path']);self.assertEqual(module.Browser(root).favorites,set())


 def test_flatten_deep_branches_up_to_four_keep_five_grouped(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as root:
   b=module.Browser(root)
   small=[dict(kind='mesh',name=f'S{i}',path=f'/Game/Small/A/B/C/S{i}.S{i}') for i in range(4)]
   large=[dict(kind='mesh',name=f'L{i}',path=f'/Game/Large/A/B/C/L{i}.L{i}') for i in range(5)]
   rows=b.rows(small+large)
   self.assertEqual(rows[0]['kind'],'folder');self.assertEqual(rows[0]['count'],5)
   self.assertEqual(rows[1:],small)
   self.assertEqual(len({r['path'] for r in rows}),5)
   self.assertEqual(b.rows(small+large,folder='/Game/Small/'),small)
   self.assertEqual(b.rows(small+large,query='L0'),large[:1])
