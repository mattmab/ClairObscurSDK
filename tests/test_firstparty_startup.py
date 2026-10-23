"""Isolated first-party static startup and queue cancellation proposals."""
from pathlib import Path
import copy,hashlib,importlib.util,shutil,sys,tempfile,types,unittest,uuid
from unittest.mock import patch
from expedition33.mod_imports import PackageSources,OwnedImports
from expedition33.mod_lifecycle import PreparationContext
from expedition33.enemy_spawning import load_catalog

HERE=Path(__file__).resolve().parents[1]
# Runner supplies source root explicitly, so the test is portable after copy.
REPO=Path(__import__('expedition33').__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def load(self,name,queue=False):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)/name
  shutil.copytree(REPO/'mods'/name,root)
  b=(root/'mod.py').read_bytes();sources=PackageSources(root/'mod.py',compile(b,str(root/'mod.py'),'exec'),hashlib.sha256(b).hexdigest())
  imports=OwnedImports('_startup_test_'+uuid.uuid4().hex,sources);imports.install();self.addCleanup(imports.close)
  spec=imports.find_spec(imports.key);module=importlib.util.module_from_spec(spec);sys.modules[imports.key]=module;imports.exec_module(module)
  return module,root
 def context(self,name):return PreparationContext('rc17',name,'a'*64)
 def session(self):
  views=[];console=types.SimpleNamespace(expose=lambda *a:None,register=lambda *a,**k:None)
  shared=types.SimpleNamespace(for_view=lambda f:views.append(f) or types.SimpleNamespace(close=lambda:None))
  return types.SimpleNamespace(_session=types.SimpleNamespace(_transport=types.SimpleNamespace(runtime_scene_protocol=7),_native_menu_service=shared),console=console),views
 def test_both_import_constructor_management_prepare_without_world(self):
  with patch('expedition33.catalog.capture_matching',side_effect=AssertionError('world read')),patch('expedition33.catalog.capture_selected',side_effect=AssertionError('world read')),patch('expedition33._reader.ReadBatch.__enter__',side_effect=AssertionError('reader')),patch('expedition33._scope.SessionScope',side_effect=AssertionError('scope')):
   for name in ('SceneEditor','EnemySpawner'):
    module,root=self.load(name);instance=module.Mod();definition=instance.management();instance.prepare_startup(self.context(name))
    self.assertIsNone(instance.session);self.assertIsNone(instance.native);self.assertFalse((root.parents[1]/'settings').exists())
    self.assertTrue(definition.id)
 def test_scene_static_idempotent_and_enable_reuses_view(self):
  module,_=self.load('SceneEditor');i=module.Mod();i.prepare_startup(self.context('SceneEditor'));view=i._scene_view
  i.prepare_startup(self.context('SceneEditor'));session,views=self.session();i.enable(session)
  self.assertIs(i._scene_view,view);self.assertEqual(len(views),1);self.assertIs(i.runtime.session,session);self.assertIsNone(i.document)
 def test_scene_legacy_enable_prepares_fallback(self):
  module,_=self.load('SceneEditor');i=module.Mod();session,views=self.session();i.enable(session)
  self.assertTrue(callable(i._scene_view));self.assertEqual(len(views),1)
 def test_enemy_startup_matches_legacy_catalogs_and_reuses_derivation(self):
  from expedition33.original_helper_encounters import catalog_recipes
  from expedition33._original_trigger_fight import direct_fight_recipes
  module,_=self.load('EnemySpawner');i=module.Mod();i.prepare_startup(self.context('EnemySpawner'));catalog=i.catalog;helpers=i.helper_catalog;direct=i.direct_catalog
  self.assertEqual(helpers,catalog_recipes(catalog));self.assertEqual(direct,direct_fight_recipes(catalog));i.prepare_startup(self.context('EnemySpawner'));self.assertIs(i.catalog,catalog)
  session,_=self.session();service=types.SimpleNamespace(catalog=copy.deepcopy(catalog))
  with patch('expedition33.enemy_spawning.EnemySpawner',return_value=service),patch('expedition33.original_helper_encounters.catalog_recipes',side_effect=AssertionError('rederived')),patch('expedition33._original_trigger_fight.direct_fight_recipes',side_effect=AssertionError('rederived')):i.enable(session)
  self.assertIs(i.helper_catalog,helpers);self.assertIs(i.direct_catalog,direct);self.assertIs(i.spawner,service)
 def test_enemy_legacy_fallback_and_changed_resource_revalidation(self):
  module,_=self.load('EnemySpawner');i=module.Mod();catalog=load_catalog();session,_=self.session()
  with patch('expedition33.enemy_spawning.EnemySpawner',return_value=types.SimpleNamespace(catalog=catalog)):i.enable(session)
  self.assertEqual(i.catalog,catalog);self.assertTrue(i.direct_catalog)
  changed=copy.deepcopy(catalog);changed['entries'][0]['label']='updated static label'
  with patch('expedition33.enemy_spawning.EnemySpawner',return_value=types.SimpleNamespace(catalog=changed)):i.enable(session)
  self.assertEqual(i.catalog,changed)
 def queued(self,i):
  for name in ('_pending','_pending_addition','_pending_arena','_pending_positions','_helper_pending','_npc_pending','_npc_dialogue_choice','_pending_tuning','_original_pending','_direct_pending'):setattr(i,name,object())
  for name in ('want_open','_helper_begin','_npc_remove','_npc_dialogue_presented'):setattr(i,name,True)
  i._pending_activate=False
 def assert_cleared(self,i):
  for name in ('_pending','_pending_addition','_pending_arena','_pending_positions','_helper_pending','_npc_pending','_npc_dialogue_choice','_pending_tuning','_original_pending','_direct_pending'):self.assertIsNone(getattr(i,name),name)
  for name in ('want_open','_helper_begin','_npc_remove','_npc_dialogue_presented'):self.assertIs(getattr(i,name),False,name)
  self.assertTrue(i._pending_activate)
 def test_queue_cleanup_success(self):
  module,_=self.load('EnemySpawner',queue=True);i=module.Mod();self.queued(i);closed=[]
  i.spawner=types.SimpleNamespace(close=lambda:closed.append('spawner') or True);i.native=types.SimpleNamespace(close=lambda:closed.append('native'))
  i.disable();self.assert_cleared(i);self.assertEqual(closed,['spawner','native']);self.assertIsNone(i.spawner)
 def test_queue_cleanup_deferred_retains_owner(self):
  module,_=self.load('EnemySpawner',queue=True);i=module.Mod();self.queued(i);owner=types.SimpleNamespace(close=lambda:False);i.spawner=owner;session=object();i.session=session
  with self.assertRaisesRegex(RuntimeError,'deferred'):i.disable()
  self.assert_cleared(i);self.assertIs(i.spawner,owner);self.assertIs(i.session,session)
 def test_queue_cleanup_npc_deferred_still_cancels_all(self):
  module,_=self.load('EnemySpawner',queue=True);i=module.Mod();self.queued(i);owner=types.SimpleNamespace(close=lambda:False);i.npc_encounter=owner
  with self.assertRaisesRegex(RuntimeError,'NPC cleanup deferred'):i.disable()
  self.assert_cleared(i);self.assertIs(i.npc_encounter,owner)
 def test_enemy_failed_static_does_not_publish_partial_catalog(self):
  module,_=self.load('EnemySpawner');i=module.Mod()
  with patch('expedition33._original_trigger_fight.direct_fight_recipes',side_effect=ValueError('invalid profile')):
   with self.assertRaisesRegex(ValueError,'invalid profile'):i.prepare_startup(self.context('EnemySpawner'))
  self.assertIsNone(i.catalog);self.assertEqual(i.helper_catalog,{});self.assertEqual(i.direct_catalog,{});self.assertIsNone(i.spawner)
if __name__=='__main__':unittest.main(verbosity=2)
