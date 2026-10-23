"""Isolated actual ModLoader startup contract tests; no game or shared edits."""
from pathlib import Path
import sys,tempfile,types,unittest
from unittest.mock import patch
from expedition33.mods import ModLoader,ModError
from expedition33._console_dispatch import CommandDispatcher

VALID=b'{"version":1,"prepare_at_startup":true,"world_uobject_access":false}'
SOURCE='''
import startup_probe as p
from expedition33.management import ModDefinition
p.events.append('import')
class Mod:
 def __init__(self): p.events.append('construct'); self.count=0
 def management(self): p.events.append('management'); return ModDefinition('test.specimen','Specimen')
 def prepare(self): raise AssertionError('legacy native prepare must stay untouched')
 def prepare_startup(self,context):
  p.events.append('prepare');self.count+=1;p.context=context;p.prepared=self
 def enable(self,session): p.events.append('enable');p.enabled=self
 def disable(self): p.events.append('disable')
'''
class FakeSession:
 def __init__(self):
  self.closed=False
  dispatcher=CommandDispatcher(self,lambda _:None)
  self.console=types.SimpleNamespace(poll=lambda:(),dispatcher=dispatcher,register=dispatcher.register,remove_owner=dispatcher.remove_owner,expose=lambda name,value:dispatcher.namespace.__setitem__(name,value))
 def _check(self):
  if self.closed:raise RuntimeError('closed')
 def close(self):self.closed=True
 def poll(self):return 0

class StartupPreparationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'mods';self.mod=self.root/'Specimen';self.mod.mkdir(parents=True)
  self.probe=types.ModuleType('startup_probe');self.probe.events=[]
  self.modules=patch.dict(sys.modules,{'startup_probe':self.probe});self.modules.start();self.addCleanup(self.modules.stop)
  self.loader=ModLoader(self.root,session=FakeSession());self.addCleanup(self.loader.close)
 def source(self,text=SOURCE,marker=VALID):
  (self.mod/'mod.py').write_text(text,encoding='utf8')
  if marker is not None:(self.mod/'lifecycle.json').write_bytes(marker)
 def test_missing_marker_never_executes(self):
  self.source(marker=None)
  self.assertFalse(self.loader.prepare_startup('Specimen',sdk_version='rc17'))
  self.assertEqual(self.probe.events,[]);self.assertEqual(self.loader.status(),())
 def test_explicit_false_never_executes(self):
  self.source(marker=VALID.replace(b'true',b'false'))
  self.assertFalse(self.loader.prepare_startup('Specimen',sdk_version='rc17'));self.assertEqual(self.probe.events,[])
 def test_malformed_fails_before_import(self):
  self.source(marker=b'{"version":true}')
  with self.assertRaisesRegex(ModError,'package preflight'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertEqual(self.probe.events,[]);self.assertEqual(self.loader.status(),())
 def test_prepare_no_scope_no_enable(self):
  self.source()
  with patch('expedition33.mods.SessionScope',side_effect=AssertionError('scope forbidden during prepare')):
   self.assertTrue(self.loader.prepare_startup('Specimen',sdk_version='rc17'))
  self.assertEqual(self.probe.events,['import','construct','management','prepare'])
  self.assertFalse(self.loader.status()[0].enabled);self.assertIsNone(self.loader._loaded['Specimen'][2])
  for name in ('session','transport','scope','read','call'):self.assertFalse(hasattr(self.probe.context,name))
 def test_retains_module_and_instance_into_enable(self):
  self.source();self.loader.prepare_startup('Specimen',sdk_version='rc17');record=self.loader._loaded['Specimen'];key,instance,_=record;module=sys.modules[key]
  self.assertFalse(self.loader.prepare_startup('Specimen',sdk_version='rc17'))
  self.loader.load('Specimen');self.loader.enable('Specimen')
  self.assertIs(module,sys.modules[key]);self.assertIs(instance,self.probe.prepared);self.assertIs(instance,self.probe.enabled)
  self.assertEqual(instance.count,1);self.assertEqual(self.probe.events,['import','construct','management','prepare','enable']);self.assertTrue(self.loader.status()[0].enabled)
 def test_failed_prepare_blocks_replay_and_enable(self):
  self.source(SOURCE.replace("p.events.append('prepare');self.count+=1;p.context=context;p.prepared=self","p.events.append('prepare');raise RuntimeError('intentional')"))
  with self.assertRaisesRegex(ModError,'intentional'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  instance=self.loader._loaded['Specimen'][1]
  for action in (lambda:self.loader.prepare_startup('Specimen',sdk_version='rc17'),lambda:self.loader.enable('Specimen')):
   with self.assertRaisesRegex(ModError,'no automatic replay'):action()
  self.assertIs(instance,self.loader._loaded['Specimen'][1]);self.assertEqual(self.probe.events.count('prepare'),1);self.assertNotIn('enable',self.probe.events)
 def test_prepare_preserves_disabled_state_through_poll(self):
  self.source();self.loader.prepare_startup('Specimen',sdk_version='rc17');self.loader.poll()
  self.assertFalse(self.loader.status()[0].enabled);self.assertNotIn('enable',self.probe.events)
 def test_noarg_prepare_untouched_without_new_callback(self):
  self.source(SOURCE.replace('def prepare_startup(self,context):','def unused_startup(self,context):'))
  self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertEqual(self.probe.events,['import','construct','management'])
 def test_import_failure_marked_and_not_reexecuted(self):
  self.source("import startup_probe as p\np.events.append('import')\nraise RuntimeError('bad import')\n")
  with self.assertRaisesRegex(ModError,'bad import'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertIn('Specimen',self.loader._preparation_failures);self.assertNotIn('Specimen',self.loader._loaded)
  with self.assertRaisesRegex(ModError,'no automatic replay'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertEqual(self.probe.events,['import'])
 def test_legacy_load_behavior_preserved(self):
  self.source(marker=None);self.loader.load('Specimen');self.loader.enable('Specimen')
  self.assertEqual(self.probe.events,['import','construct','management','enable'])
 def test_constructor_failure_marked(self):
  self.source(SOURCE.replace("p.events.append('construct'); self.count=0","p.events.append('construct'); raise RuntimeError('bad constructor')"))
  with self.assertRaisesRegex(ModError,'bad constructor'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertIn('Specimen',self.loader._preparation_failures);self.assertEqual(self.probe.events,['import','construct'])
 def test_management_failure_marked(self):
  self.source(SOURCE.replace("p.events.append('management'); return ModDefinition('test.specimen','Specimen')","p.events.append('management'); raise RuntimeError('bad management')"))
  with self.assertRaisesRegex(ModError,'bad management'):self.loader.prepare_startup('Specimen',sdk_version='rc17')
  self.assertIn('Specimen',self.loader._preparation_failures);self.assertEqual(self.probe.events,['import','construct','management'])
if __name__=='__main__':unittest.main(verbosity=2)
