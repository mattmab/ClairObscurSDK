import ast,unittest
from pathlib import Path
from types import SimpleNamespace
class MenuRecoveryTests(unittest.TestCase):
 def test_empty_discovery_failure_is_closed_before_rebuild(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/mod.py').read_text(encoding='utf8'))
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mod')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_menu_owner')
  namespace={};exec(compile(ast.Module(body=[method],type_ignores=[]),'mod.py','exec'),namespace)
  calls=[];mod=SimpleNamespace(catalog_menu=SimpleNamespace(widget=None,close=lambda:calls.append('close') or True))
  namespace['refresh_menu_owner'](mod)
  self.assertIsNone(mod.catalog_menu);self.assertEqual(calls,['close'])
 def test_failed_cleanup_keeps_owner(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/mod.py').read_text(encoding='utf8'))
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mod')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_menu_owner')
  namespace={};exec(compile(ast.Module(body=[method],type_ignores=[]),'mod.py','exec'),namespace)
  owner=SimpleNamespace(widget=None,close=lambda:False);mod=SimpleNamespace(catalog_menu=owner)
  with self.assertRaises(RuntimeError):namespace['refresh_menu_owner'](mod)
  self.assertIs(mod.catalog_menu,owner)
