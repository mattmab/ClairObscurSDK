import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from contextlib import nullcontext
from expedition33._cinematic_panel_pool import CinematicPanelPool

class CinematicPanelPoolTests(unittest.TestCase):
 def fixture(self,observations=None):
  context=dict(world=(7,1,2,0x10000),controller=(7,3,4,0x20000),world_path='/Game/QA.Map')
  scope=Mock(pid=7,_session=N(_transport=N(_executable='reader')))
  panel=Mock(state='built',uncertain=False);panel.hide.return_value=True;panel.retire_world.return_value='ack'
  observer=Mock(side_effect=observations or [context,context])
  with patch('expedition33._cinematic_panel_pool.SessionScope',return_value=scope),\
       patch('expedition33._cinematic_panel_pool.shared_operation',return_value=nullcontext()),\
       patch('expedition33._cinematic_panel_pool.context_observer',return_value=observer),\
       patch('expedition33._cinematic_panel_pool.CinematicContextPanel',return_value=panel),\
       patch('expedition33._cinematic_panel_pool.prepare_widget_routing',return_value='routing') as routing,\
       patch('expedition33._cinematic_panel_pool.PreparedWidgetDependencies',return_value='dependencies') as dependencies,\
       patch('expedition33._cinematic_panel_pool.PreparedAssetLoader',return_value='loader') as loader,\
       patch('expedition33._cinematic_panel_pool.PreparedSequenceMetadata',return_value='metadata') as metadata,\
       patch('expedition33._cinematic_panel_pool.PreparedMusicDependencies',return_value='music') as music:
   pool=CinematicPanelPool(object());pool.prepare()
   routing.assert_called_once_with(scope)
   self.assertEqual(pool.routing_class,'routing')
   dependencies.assert_called_once_with(scope)
   self.assertEqual(pool.widget_dependencies,'dependencies')
   loader.assert_called_once_with(scope)
   self.assertEqual(pool.asset_loader,'loader')
   metadata.assert_called_once_with(scope)
   self.assertEqual(pool.sequence_metadata,'metadata')
   music.assert_called_once_with(scope)
   self.assertEqual(pool.music_dependencies,'music')
  return pool,panel,scope,context
 def test_preparation_never_attaches_input_and_tree_survives_normal_consumer_release(self):
  pool,panel,scope,context=self.fixture()
  panel.build.assert_called_once();panel.open.assert_not_called();panel.hide.assert_not_called()
  self.assertIs(pool.acquire(context),panel)
  with self.assertRaises(RuntimeError):pool.acquire(context)
  self.assertTrue(pool.release(panel));self.assertFalse(pool.in_use)
  panel.close.assert_not_called();panel.close_owned_tree.assert_not_called();scope.close.assert_not_called()
  self.assertIs(pool.acquire(context),panel)
 def test_deferred_detach_keeps_owner_and_blocks_pool_close(self):
  pool,panel,scope,context=self.fixture();pool.acquire(context)
  panel.hide.side_effect=(False,True)
  self.assertFalse(pool.release(panel));self.assertTrue(pool.in_use)
  with self.assertRaisesRegex(RuntimeError,'consumer'):pool.close()
  self.assertTrue(pool.release(panel));self.assertFalse(pool.in_use)
 def test_changed_context_cannot_reuse_or_restore_old_world_tree(self):
  pool,panel,scope,context=self.fixture()
  with self.assertRaisesRegex(RuntimeError,'another world'):pool.acquire(dict(context,controller=(7,9,9,0x30000)))
  self.assertTrue(pool.retiring);self.assertFalse(pool.in_use)
  with patch('expedition33._cinematic_panel_pool.close_lease_only_scope',return_value=True):self.assertTrue(pool.close())
  panel.retire_world.assert_called_once();panel.hide.assert_not_called();panel.close_owned_tree.assert_not_called()
 def test_retirement_waits_for_consumer_then_retains_scope_until_release_ack(self):
  pool,panel,scope,context=self.fixture();pool.acquire(context)
  self.assertEqual(pool.retire_world(),'pending');panel.retire_world.assert_not_called()
  panel.retire_world.side_effect=('pending','ack','ack','ack')
  self.assertFalse(pool.release(panel,retired=True));self.assertTrue(pool.in_use)
  self.assertTrue(pool.release(panel,retired=True));self.assertFalse(pool.in_use)
  with patch('expedition33._cinematic_panel_pool.close_lease_only_scope',side_effect=(False,True)):
   self.assertEqual(pool.retire_world(),'pending');self.assertFalse(pool.closed)
   self.assertEqual(pool.retire_world(),'ack');self.assertTrue(pool.closed)
  panel.close_owned_tree.assert_not_called()
 def test_owned_close_does_not_acknowledge_deferred_tree_cleanup(self):
  pool,panel,scope,context=self.fixture();panel.close_owned_tree.side_effect=(False,True)
  with patch('expedition33._cinematic_panel_pool.close_lease_only_scope',return_value=True) as close:
   self.assertFalse(pool.close());close.assert_not_called()
   self.assertTrue(pool.close());self.assertTrue(pool.closed)

if __name__=='__main__':unittest.main()
