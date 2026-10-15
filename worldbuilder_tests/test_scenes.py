import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('scenes',Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder/scenes.py');scene=importlib.util.module_from_spec(spec);spec.loader.exec_module(scene)
class Scenes(unittest.TestCase):
 def sample(self):
  asset='/Game/Props/Rock.Rock'
  return dict(format=scene.FORMAT,version=1,name='Test',world='/Game/Level.Level',objects=[dict(id='a'*32,kind='mesh',asset=asset,transform=[0.,0.,0.,1.,10.,20.,30.,0.,1.,1.,1.,0.])],assets=[asset])
 def test_roundtrip_and_save_as(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as folder:
   store=scene.MapStore(folder);data=self.sample();a=store.save(data);b=store.save(data)
   self.assertNotEqual(a,b);self.assertEqual(store.read(a),data);self.assertEqual(len(store.list()),2)
 def test_wrong_level(self):
  with self.assertRaises(ValueError):scene.validate(self.sample(),'/Game/Other.Other')
 def test_missing_manifest_dependency(self):
  data=self.sample();data['assets']=[]
  with self.assertRaises(ValueError):scene.validate(data)
 def test_nonfinite_and_invalid_rotation(self):
  for n in (float('nan'),float('inf'),100.):
   data=self.sample();data['objects'][0]['transform'][3]=n
   with self.assertRaises(ValueError):scene.validate(data)
 def test_duplicate_ids(self):
  data=self.sample();data['objects']*=2
  with self.assertRaises(ValueError):scene.validate(data)
 def test_child_mesh_manifest_and_relative_path(self):
  data=self.sample();child=dict(component='.RockComponent',asset='/Game/Props/Child.Child',transform=data['objects'][0]['transform'])
  data['objects'][0]['component_edits']=[child]
  with self.assertRaises(ValueError):scene.validate(data)
  data['assets']=sorted([data['objects'][0]['asset'],child['asset']])
  self.assertEqual(scene.validate(data),data)
  child['component']='/Game/Unrelated.Actor.Component'
  with self.assertRaises(ValueError):scene.validate(data)
 def test_duplicate_child_rejected(self):
  data=self.sample();child=dict(component='.RockComponent',asset=data['objects'][0]['asset'],transform=data['objects'][0]['transform'])
  data['objects'][0]['component_edits']=[child,child]
  with self.assertRaises(ValueError):scene.validate(data)
 def test_paths_cannot_escape_map_folder(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'build') as folder:
   store=scene.MapStore(folder)
   with self.assertRaises(ValueError):store.read('../outside')
if __name__=='__main__':unittest.main()

