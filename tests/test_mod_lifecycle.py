import hashlib,importlib.util,json,pathlib,sys,tempfile,types,unittest
from expedition33 import mod_lifecycle as m
VALID=b'{"version":1,"prepare_at_startup":true,"world_uobject_access":false}'
class Tests(unittest.TestCase):
 def test_absent_legacy(self):self.assertFalse(m.parse_lifecycle(None).prepare_at_startup)
 def test_opt_in_and_explicit_defer(self):
  self.assertTrue(m.parse_lifecycle(VALID).prepare_at_startup)
  self.assertFalse(m.parse_lifecycle(VALID.replace(b'true',b'false')).prepare_at_startup)
 def test_invalid_before_factory(self):
  for data in [b'',b'x',b'{}',b'[]',b'\xff',VALID+b'x',VALID.replace(b'1',b'true'),VALID.replace(b'1',b'2'),VALID.replace(b'false',b'0'),VALID.replace(b'false',b'true'),VALID.replace(b'true',b'1'),VALID[:-1]+b',"version":1}',b' '*4097]:
   with self.subTest(data=data[:70]),self.assertRaises(m.LifecycleMetadataError):m.parse_lifecycle(data)
 def setup_folder(self,metadata=VALID):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=pathlib.Path(tmp.name);p=root/'mod.py';b=b'raise AssertionError("must not execute during capture")\n';p.write_bytes(b)
  if metadata is not None:(root/'lifecycle.json').write_bytes(metadata)
  return root,p,b,hashlib.sha256(b).hexdigest()
 def capture(self,p,b,d,callback=None):
  def factory(*args):
   if callback:callback()
   return types.SimpleNamespace(sha256='a'*64,modules={'':compile(b,str(p),'exec')})
  return m.capture_package(p,compile(b,str(p),'exec'),d,package_factory=factory)
 def test_capture_does_not_execute(self):
  r,p,b,d=self.setup_folder();c=self.capture(p,b,d);self.assertTrue(c.policy.prepare_at_startup);self.assertEqual(c.sources.sha256,'a'*64)
 def test_malformed_fails_before_source_capture(self):
  r,p,b,d=self.setup_folder(b'{}');calls=[]
  with self.assertRaises(m.LifecycleMetadataError):self.capture(p,b,d,lambda:calls.append(1))
  self.assertEqual(calls,[])
 def test_marker_change_during_source_capture(self):
  r,p,b,d=self.setup_folder()
  with self.assertRaises(m.LifecycleMetadataError):self.capture(p,b,d,lambda:(r/'lifecycle.json').unlink())
 def test_marker_appears_during_legacy_capture(self):
  r,p,b,d=self.setup_folder(None)
  with self.assertRaises(m.LifecycleMetadataError):self.capture(p,b,d,lambda:(r/'lifecycle.json').write_bytes(VALID))
 def test_entry_change_detected(self):
  r,p,b,d=self.setup_folder()
  with self.assertRaises(m.LifecycleMetadataError):self.capture(p,b,d,lambda:p.write_bytes(b'pass\n'))
 def test_entry_already_changed(self):
  r,p,b,d=self.setup_folder();p.write_bytes(b'pass\n')
  with self.assertRaises(m.LifecycleMetadataError):self.capture(p,b,d)
 def test_marker_participates_in_identity(self):
  r,p,b,d=self.setup_folder(None);a=self.capture(p,b,d);(r/'lifecycle.json').write_bytes(VALID);c=self.capture(p,b,d)
  self.assertEqual(a.package_sha256,c.package_sha256);self.assertNotEqual(a.lifecycle_sha256,c.lifecycle_sha256)
 def test_archive_marker(self):
  self.assertFalse(m.policy_from_candidate(types.SimpleNamespace(files=(('mod.py',b'pass'),))).prepare_at_startup)
  self.assertTrue(m.policy_from_candidate(types.SimpleNamespace(files=(('lifecycle.json',VALID),))).prepare_at_startup)
  with self.assertRaises(m.LifecycleMetadataError):m.policy_from_candidate(types.SimpleNamespace(files=(('Lifecycle.json',VALID),)))
 def test_facade_read_only_no_world(self):
  c=m.PreparationContext('rc17','Sample','a'*64)
  for field in ['session','transport','pid','scope','read','call','console','actions']:
   self.assertFalse(hasattr(c,field))
  with self.assertRaises((AttributeError,TypeError)):c.mod_name='changed'
 def test_prepare_once_same_instance(self):
  calls=[];i=types.SimpleNamespace(prepare_startup=lambda c:calls.append(c));g=m.PreparationOnce(i);c=m.PreparationContext('rc17','Sample','a'*64)
  self.assertTrue(g.run(c));self.assertFalse(g.run(c));self.assertIs(g.instance,i);self.assertEqual(len(calls),1)
 def test_optional_prepare(self):
  g=m.PreparationOnce(object());self.assertTrue(g.run(m.PreparationContext('rc17','Sample','a'*64)))
 def test_failure_not_replayed(self):
  calls=[]
  def fail(c):calls.append(c);raise RuntimeError('failure')
  i=types.SimpleNamespace(prepare_startup=fail);g=m.PreparationOnce(i);c=m.PreparationContext('rc17','Sample','a'*64)
  with self.assertRaises(RuntimeError):g.run(c)
  with self.assertRaises(RuntimeError):g.run(c)
  self.assertEqual(len(calls),1);self.assertIs(g.instance,i);self.assertEqual(g.state,'failed')
 def test_reentrant_not_replayed(self):
  c=m.PreparationContext('rc17','Sample','a'*64);g=m.PreparationOnce(types.SimpleNamespace(prepare_startup=lambda _:g.run(c)))
  with self.assertRaises(RuntimeError):g.run(c)
  self.assertEqual(g.state,'failed')
 def test_actual_captured_dependencies_not_reread(self):
  from expedition33.mod_imports import PackageSources,OwnedImports
  r,p,b,d=self.setup_folder();b=b'from .helper import value\nclass Mod: pass\n';p.write_bytes(b);d=hashlib.sha256(b).hexdigest();(r/'helper.py').write_text('value=17\n')
  c=m.capture_package(p,compile(b,str(p),'exec'),d,package_factory=PackageSources)
  (r/'helper.py').write_text('raise AssertionError("disk code must not run")\n')
  imports=OwnedImports('_lifecycle_capture_test',c.sources);imports.install();self.addCleanup(imports.close)
  spec=imports.find_spec(imports.key);module=importlib.util.module_from_spec(spec);sys.modules[imports.key]=module;imports.exec_module(module)
  self.assertEqual(module.value,17)
 def test_existing_prepare_not_invoked(self):
  calls=[];i=types.SimpleNamespace(prepare=lambda:calls.append('native-ui'),prepare_startup=lambda context:calls.append('startup'))
  g=m.PreparationOnce(i);g.run(m.PreparationContext('rc17','Sample','a'*64));self.assertEqual(calls,['startup'])
  legacy=m.PreparationOnce(types.SimpleNamespace(prepare=lambda:calls.append('legacy-native-ui')))
  legacy.run(m.PreparationContext('rc17','Legacy','a'*64));self.assertEqual(calls,['startup'])
if __name__=='__main__':unittest.main(verbosity=2)
