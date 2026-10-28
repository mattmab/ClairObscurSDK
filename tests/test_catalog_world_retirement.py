import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.procedural_mesh import Tetrahedron,MeshStatusPending
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('_catalog_retirement_tests',root/'mods/CatalogModels/mod.py',submodule_search_locations=[str(root/'mods/CatalogModels')])
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)

class CatalogRetirementTests(unittest.TestCase):
 def test_preview_loads_section_materials_before_catalog_snapshot(self):
  from expedition33.procedural_mesh import MATERIAL_PROFILES
  for skin,expected in ((False,(13,2)),(True,(13,))):
   with self.subTest(skin=skin):
    mod=module.Mod();mod.session=Mock();mod.replacement_profile=13
    data=dict(id='test',vertices=3,sections=[dict(mesh='mesh',texture='image',profile=13),dict(mesh='mesh2',texture='image2',profile=2)],material_profiles=[13])
    if skin:data['skin']='skin'
    events=[]
    with patch.object(module,'SessionScope'),patch.object(module,'Tetrahedron'),patch('expedition33.assets.load_asset',side_effect=lambda scope,path:events.append(path)),patch.object(module,'capture_matching',side_effect=lambda *a,**k:events.append('snapshot')):
     mod._begin(data)
    self.assertEqual(events,[MATERIAL_PROFILES[p][0] for p in expected]+['snapshot'])

 def test_mesh_tracking_requires_native_idle_and_never_dispatches_restore_or_destroy(self):
  model=object.__new__(Tetrahedron);model.closed=False;model.created=True
  model.scope=N(_mesh_models=[model]);model._command=Mock()
  model.status=Mock(side_effect=(MeshStatusPending('GC'),{'state':1},{'state':2},{'state':0}))
  for _ in range(3):self.assertFalse(model.retire_world());self.assertFalse(model.closed)
  self.assertTrue(model.retire_world());self.assertTrue(model.closed);self.assertFalse(model.created)
  self.assertEqual(model.scope._mesh_models,[]);model._command.assert_not_called()
 def test_unknown_or_malformed_mesh_receipt_keeps_tracking_owned(self):
  for state in (True,None,3,9):
   model=object.__new__(Tetrahedron);model.closed=False;model.created=True
   model.scope=N(_mesh_models=[model]);model.status=Mock(return_value={'state':state})
   with self.assertRaises(RuntimeError):model.retire_world()
   self.assertFalse(model.closed);self.assertEqual(model.scope._mesh_models,[model])
 def test_retirement_waits_for_worker_and_native_ack_then_releases_only_owned_tracking(self):
  mod=module.Mod();context=N(previous_token='old')
  mod.session=object();mod.pool=Mock();pool=mod.pool
  worker=Mock();worker.done.return_value=False;worker.cancel.return_value=False;mod.future=worker
  mod.model=Mock();model=mod.model;model.retire_world.side_effect=(False,True)
  mod.scope=object();scope=mod.scope;mod.open_pending=True;mod.follow_character=True
  mod.revoke_world(context);self.assertFalse(mod.open_pending);self.assertFalse(mod.follow_character)
  self.assertEqual(mod.begin_world_retirement(context),'pending');model.retire_world.assert_not_called()
  worker.done.return_value=True
  with patch('expedition33._retired_tracking.close_lease_only_scope',side_effect=(False,True)) as close:
   self.assertEqual(mod.poll_world_retirement(context),'pending');close.assert_not_called()
   self.assertEqual(mod.poll_world_retirement(context),'pending');self.assertIs(mod.scope,scope)
   self.assertEqual(mod.poll_world_retirement(context),'ack')
  worker.result.assert_not_called();model.close.assert_not_called();model.unbind_skin.assert_not_called()
  pool.shutdown.assert_called_once_with(wait=False,cancel_futures=True)
  self.assertIsNone(mod.session);self.assertIsNone(mod.model);self.assertIsNone(mod.scope)
  self.assertEqual(mod.poll_world_retirement(N(previous_token='different')),'unknown')
 def test_revoked_poll_never_uploads_completed_preparation_into_new_world(self):
  mod=module.Mod();mod.session=object();mod.future=Mock();mod.future.done.return_value=True
  mod._begin=Mock();mod.revoke_world(N(previous_token='old'));mod.poll()
  mod.future.result.assert_not_called();mod._begin.assert_not_called()

if __name__=='__main__':unittest.main()
