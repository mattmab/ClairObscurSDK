from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest
from expedition33 import simon_portable as m
from expedition33 import _original_trigger_fight as fights

class PreloadTests(unittest.TestCase):
 def setUp(self):
  self.transport=N(battle_completion_receipt_protocol=1,_executable='candidate')
  self.scope=N(pid=123,_check=Mock(),_session=N(_transport=self.transport),_register_native_owner=Mock())
  self.context={'world_path':m.WORLD,'world':(123,1,1001,0x10000),'controller':(123,2,1002,0x20000)}
  self.warm=N(close=Mock());self.spawner=N(catalog={},close=Mock(return_value=True))
  self.snapshot=self.enterContext(patch.object(m,'_snapshot',return_value=(self.context,(123,3,1003,0x30000),(1.,2.,3.))))
  self.enterContext(patch('expedition33._scope.SessionScope',return_value=self.warm))
  self.spawner_factory=self.enterContext(patch.object(m,'EnemySpawner',return_value=self.spawner))
  self.enterContext(patch.object(m,'ReadBatch'))
  self.enterContext(patch.object(m,'controller_context',return_value=self.context))
  self.metadata=self.enterContext(patch.object(m,'_construction_metadata'))
  base=dict(battle_source='Root.Root:Battle',arena={'class_path':'Arena.Arena_C'},trigger_class='Trigger.Trigger_C')
  self.enterContext(patch.object(fights,'_recipes',return_value=[dict(base,id='simon-normal'),dict(base,id='simon-phase2')]))
  self.assets=self.enterContext(patch('expedition33.assets.load_asset',side_effect=lambda *a:N(return_value=object(),release=Mock(return_value=True),_leases=[])))
  self.classes=self.enterContext(patch('expedition33.picto_class_load.load_class',side_effect=lambda *a:N(return_value=object(),release=Mock(return_value=True),_leases=[])))
  self.runner=m.PortableSimon(self.scope,disposable_test=True)
 def test_preload_retains_three_scenes_and_shared_source_without_battle(self):
  r=self.runner;r._prepare_battle=Mock();r._start_scene=Mock();r.preload()
  self.assertEqual(r.state,'preloaded');self.assertTrue(r.status()['preloaded'])
  self.assertEqual([c.args[1] for c in self.assets.call_args_list],[m.SCENES[n] for n in ('intro','transition','outro')]+['Root.Root'])
  self.assertEqual([c.args[1] for c in self.classes.call_args_list],['Arena.Arena_C','Trigger.Trigger_C'])
  r._prepare_battle.assert_not_called();r._start_scene.assert_not_called();self.spawner_factory.assert_not_called()
  self.metadata.assert_called_once();self.assertEqual(self.assets.call_args_list[0].args[0],self.warm)
 def test_start_after_preload_takes_fresh_return_position_without_reloading(self):
  r=self.runner;r.preload();r._prepare_battle=Mock();r._start_scene=Mock()
  self.snapshot.return_value=(self.context,(123,3,1003,0x30000),(50.,60.,70.))
  r.start();self.assertEqual(r.initial_position,(50.,60.,70.));self.assertEqual(self.assets.call_count,4)
  r._prepare_battle.assert_called_once_with('simon-normal');r._start_scene.assert_called_once_with('intro')
 def test_unknown_preload_preserves_owner_and_never_replays_or_releases(self):
  r=self.runner;self.assets.side_effect=RuntimeError('lost asset acknowledgement')
  with self.assertRaisesRegex(RuntimeError,'lost asset'):r.preload()
  self.assertEqual(r.state,'blocked');self.assertFalse(r.status()['preloaded'])
  self.assertEqual(r._warm_pending,m.SCENES['intro']);self.assertFalse(r.close())
  self.warm.close.assert_not_called();self.spawner.close.assert_not_called()
  with self.assertRaisesRegex(RuntimeError,'one-shot'):r.preload()
 def test_context_replacement_blocks_start_without_geometry_or_entry(self):
  r=self.runner;r.preload();r._prepare_battle=Mock();r._start_scene=Mock()
  self.snapshot.return_value=({**self.context,'world':(123,4,1004,0x40000)},(123,3,1003,0x30000),(1.,2.,3.))
  with self.assertRaisesRegex(RuntimeError,'replaced'):r.start()
  r._prepare_battle.assert_not_called();r._start_scene.assert_not_called()
 def test_close_retires_only_owned_warm_scope(self):
  r=self.runner;r.preload();self.assertTrue(r.close());self.warm.close.assert_called_once()
  self.assertEqual(r.state,'closed');self.assertFalse(r.status()['preloaded']);self.scope._check.assert_called()
 def test_deferred_asset_release_is_not_replayed(self):
  r=self.runner;r.preload();last=r._warm_holds[-1]['handle'];lease=N(_state='pending_release')
  last._leases=[lease];last.release.return_value=False
  self.assertFalse(r.close());self.assertFalse(r.close());last.release.assert_called_once();self.warm.close.assert_not_called()
  lease._state='released';self.assertTrue(r.close());last.release.assert_called_once()
 def test_unknown_asset_release_preserves_cleanup_failure(self):
  r=self.runner;r.preload();last=r._warm_holds[-1]['handle'];last.release.side_effect=RuntimeError('lost release')
  with self.assertRaisesRegex(RuntimeError,'lost release'):r.close()
  self.assertFalse(r.close());last.release.assert_called_once();self.warm.close.assert_not_called()

class ConstructionMetadataTests(unittest.TestCase):
 def setUp(self):
  self.scope=N(pid=123);self.transport=object();self.spawner=N()
  self.context={'controller':(123,1,1001,0x10000),'world':(123,2,1002,0x20000)}
  self.function=N(index=3,serial=1003,address=0x30000,class_name='Function',name='K2_DestroyActor')
  self.catalog=N(objects=(self.function,))
  self.match=self.enterContext(patch('expedition33.catalog.capture_matching',return_value=self.catalog))
  self.select=self.enterContext(patch('expedition33.catalog.capture_selected',return_value='fresh-selected'))
 def get(self):return fights._construction_metadata(self.scope,self.transport,self.context,self.spawner)
 def test_reuse_refreshes_exact_static_identity_not_values(self):
  self.assertIs(self.get(),self.catalog);self.assertEqual(self.get(),'fresh-selected')
  self.match.assert_called_once();self.select.assert_called_once_with(123,((3,1003,0x30000),))
 def test_zero_serial_is_not_cached_as_a_wildcard(self):
  self.function.serial=0;self.get();self.get();self.assertEqual(self.match.call_count,2);self.select.assert_not_called()
 def test_world_or_transport_change_forces_fresh_discovery(self):
  self.get();self.context={**self.context,'world':(123,4,1004,0x40000)};self.get()
  self.transport=object();self.get();self.assertEqual(self.match.call_count,3);self.select.assert_not_called()
