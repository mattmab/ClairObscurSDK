from pathlib import Path
from types import SimpleNamespace as N
import tempfile
import unittest
from unittest.mock import Mock,patch

from expedition33.mods import ModLoader,ModError,ModDisablePending
from expedition33.management import ManagementError
from expedition33.world_lifecycle import WorldLifecycleError
from expedition33.world_admission import Admission
from test_mods import FakeSession


def token(n):return ((7,n,10,0x10000+n),(7,2,10,0x10002),(7,3,10,0x10003),0)
def ready(n=1,exploration=True):return Admission('world_ready','test',token(n),exploration)

SOURCE='''
from expedition33.management import ModDefinition,Option,Action,Keybind
class Mod:
 def __init__(self):self.events=[];self.outcomes=['ack'];self.fail_disable=False
 def management(self):return ModDefinition('test.world','World',options=(Option('value','Value','int',1,on_change=self.change),),actions=(Action('act','Act',self.change),),keybinds=(Keybind('key','Key','F8',self.change),))
 def change(self,arg):self.events.append('callback')
 def enable(self,scope):
  self.scope=scope;self.events.append('enable')
  scope.console.register('world',lambda arg:self.change(arg),owner=self)
  scope.actions.register('world.action',lambda:self.change(None))
 def disable(self):
  self.events.append('disable')
  if self.fail_disable:raise RuntimeError('Map context observer cleanup pending')
 def poll(self):self.events.append('poll')
 def revoke_world(self,context):self.events.append('revoke')
 def begin_world_retirement(self,context):self.events.append('begin');return self.outcomes.pop(0)
 def poll_world_retirement(self,context):self.events.append('cleanup');return self.outcomes.pop(0)
'''


class WorldLifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);(root/'World').mkdir();(root/'World/mod.py').write_text(SOURCE)
  self.shared=FakeSession();self.shared._transport=object();self.shared._closed=False
  self.shared.poll=Mock(return_value=0);self.shared.console.poll=Mock(return_value=())
  self.loader=ModLoader(root,session=self.shared);self.coordinator=self.loader.install_world_lifecycle()
  self.loader.load('World');self.mod=self.loader._loaded['World'][1]
 def tearDown(self):
  # Tests intentionally retain unknown owners. Test-only explicit teardown
  # drops the coordinator, without claiming this is production retirement.
  self.loader.world_lifecycle=None;self.mod.fail_disable=False
  try:self.loader.close()
  except ModError:pass
  self.tmp.cleanup()
 def enable(self):
  self.coordinator.observe(ready());self.loader.enable('World');self.mod.events.clear()
 def test_explicit_disable_barrier_pending_retains_scope_without_unknown_or_mutation(self):
  self.enable();scope=self.mod.scope
  self.mod.prepare_disable=Mock(side_effect=(False,True))
  with self.assertRaises(ModDisablePending):self.loader.disable('World')
  self.assertEqual(self.mod.events,[]);self.assertIs(self.loader._loaded['World'][2],scope)
  self.assertEqual(self.coordinator.bindings['World'].state,'bound')
  self.assertNotIn('World',self.loader._cleanup_failures)
  self.loader.disable('World');self.assertEqual(self.mod.events,['disable'])
  self.assertEqual(self.mod.prepare_disable.call_count,2)
 def test_unload_pending_cannot_drop_enabled_module_and_scope(self):
  self.enable();scope=self.mod.scope;self.mod.prepare_disable=Mock(return_value=False)
  with self.assertRaises(ModDisablePending):self.loader.unload('World')
  self.assertIs(self.loader._loaded['World'][2],scope)
  self.assertEqual(self.mod.events,[])
  self.mod.prepare_disable.return_value=True
 def test_close_barriers_precede_key_actions_and_any_disable(self):
  self.enable();scope=self.mod.scope;self.mod.prepare_disable=Mock(side_effect=(False,True))
  keys=self.loader._keys=Mock();actions=self.loader.actions.close=Mock()
  with self.assertRaises(ModDisablePending):self.loader.close()
  keys.close.assert_not_called();actions.assert_not_called()
  self.assertFalse(self.loader._closed);self.assertIs(self.loader._loaded['World'][2],scope)
  self.loader.close();self.assertEqual(self.mod.events,['disable'])
  self.assertEqual(self.mod.prepare_disable.call_count,2)
  self.assertTrue(self.loader._closed)
 def test_barrier_unknown_latches_owner_without_replaying_or_disabling(self):
  self.enable();scope=self.mod.scope
  self.mod.prepare_disable=Mock(side_effect=RuntimeError('unknown stop outcome'))
  with self.assertRaises(ModError):self.loader.disable('World')
  with self.assertRaises(ModError):self.loader.disable('World')
  self.mod.prepare_disable.assert_called_once()
  self.assertEqual(self.mod.events,[]);self.assertEqual(self.coordinator.bindings['World'].state,'unknown')
  self.assertIs(self.loader._loaded['World'][2],scope)
  del self.mod.prepare_disable
 def test_uncertain_world_unload_does_not_drop_bound_scope(self):
  self.enable();scope=self.mod.scope;self.coordinator.observe(None)
  with self.assertRaises(ModError):self.loader.unload('World')
  self.assertIs(self.loader._loaded['World'][2],scope)
  self.assertEqual(self.mod.events,[])
 def test_scope_cleanup_failure_retains_owner_and_never_replays_domain_disable(self):
  self.enable();scope=self.mod.scope;scope.close=Mock(side_effect=RuntimeError('scope cleanup unknown'))
  with self.assertRaises(ModError):self.loader.disable('World')
  self.assertEqual(self.mod.events,['disable']);scope.close.assert_called_once()
  self.assertIs(self.loader._loaded['World'][2],scope)
  self.assertEqual(self.coordinator.bindings['World'].state,'unknown')
  for operation in (lambda:self.loader.disable('World'),lambda:self.loader.unload('World'),self.loader.close):
   with self.assertRaises(ModError):operation()
  self.assertEqual(self.mod.events,['disable']);scope.close.assert_called_once()
 def test_scope_failure_cannot_erase_preclose_child_and_lease_journal(self):
  self.enable();scope=self.mod.scope
  lease=N(_state='pending_release');child=N(_leases=[lease],_children=[])
  scope._children.append(child)
  def fail_close():
   child._leases.clear();scope._children.clear();scope._leases.clear()
   raise RuntimeError('scope cleanup unknown')
  scope.close=Mock(side_effect=fail_close)
  with self.assertRaises(ModError):self.loader.disable('World')
  row=self.coordinator.bindings['World']
  self.assertIn(lease,row.leases);self.assertIn(child,row.scopes)
  self.assertIs(row.scope,scope);self.assertEqual(row.state,'unknown')
 def test_first_admission_required_and_missing_does_not_retire(self):
  with self.assertRaises(ModError):self.loader.enable('World')
  self.assertTrue(self.coordinator.allows('SDKManagement'))
  self.enable();scope=self.mod.scope;self.coordinator.observe(None)
  self.loader.poll();self.shared.poll.assert_called();self.shared.console.poll.assert_called()
  self.assertEqual(self.mod.events,[]);self.assertIs(self.loader._loaded['World'][2],scope)
  self.assertEqual(self.coordinator.bindings['World'].state,'bound')
 def test_combat_same_epoch_retains_callbacks(self):
  self.enable();self.coordinator.observe(ready(exploration=False));self.loader.poll()
  self.assertIn('poll',self.mod.events);self.assertNotIn('begin',self.mod.events)
 def test_all_managed_callback_routes_block_during_uncertainty(self):
  self.enable();registry=self.loader.registry;selection=registry.select('test.world')
  captured=registry.action_callback(selection,'act');debug=self.loader.actions.actions['world.action']['callback']
  self.assertTrue(registry.key_routes());self.coordinator.observe(None)
  self.assertEqual(registry.key_routes(),())
  for callback in (lambda:captured(),lambda:registry.dispatch_key(selection,'key','F8'),
    lambda:registry.set_option(selection,'value',2),debug):
   with self.assertRaises((ManagementError,WorldLifecycleError)):callback()
  console=self.shared.console.dispatcher.execute('world')
  self.assertNotIn('callback',self.mod.events)
 def test_pending_adapter_and_gc_deferral_keep_scope_until_actual_ack(self):
  self.enable();scope=self.mod.scope;lease=N(_state='pending_release')
  def close():scope._leases.clear();scope._closed=True
  scope._leases.append(lease);scope.close=Mock(side_effect=close)
  self.mod.outcomes=['pending','ack'];self.coordinator.observe(None,title=True)
  self.loader.poll();self.assertEqual(self.mod.events,['revoke','begin'])
  self.loader.poll();self.assertEqual(self.mod.events,['revoke','begin','cleanup'])
  self.assertIs(self.loader._loaded['World'][2],scope);scope.close.assert_called_once()
  self.loader.poll();self.assertIs(self.loader._loaded['World'][2],scope)
  lease._state='released';self.loader.poll();self.assertIsNone(self.loader._loaded['World'][2])
  self.assertEqual(self.coordinator.bindings['World'].state,'retired');self.assertNotIn('disable',self.mod.events)
 def test_ack_allows_fresh_scope_same_import_instance(self):
  self.enable();old=self.mod.scope;key=self.loader._loaded['World'][0]
  self.coordinator.observe(ready(9));self.loader.poll()
  self.assertIsNone(self.loader._loaded['World'][2]);self.loader.enable('World')
  self.assertIs(self.loader._loaded['World'][1],self.mod);self.assertEqual(self.loader._loaded['World'][0],key)
  self.assertIsNot(self.mod.scope,old);self.assertTrue(old._closed)
 def test_unknown_adapter_is_never_replayed_and_blocks_new_epoch(self):
  self.enable();self.mod.outcomes=['unknown'];scope=self.mod.scope
  self.coordinator.observe(ready(9));self.loader.poll();self.loader.poll()
  self.assertEqual(self.mod.events,['revoke','begin']);self.assertIs(self.loader._loaded['World'][2],scope)
  with self.assertRaises(ModError):self.loader.enable('World')
  with self.assertRaises(ModError):self.loader.unload('World')
  with self.assertRaises(ModError):self.loader.close()
  self.assertFalse(self.loader._closed);self.assertIn('world.action',self.loader.actions.actions)
 def test_domain_ack_cannot_hide_active_borrowed_owner(self):
  self.enable();self.mod.scope._native_owners.append(N(state='active',close=Mock()))
  self.coordinator.observe(None,title=True);self.loader.poll()
  row=self.coordinator.bindings['World'];self.assertEqual(row.state,'unknown');self.assertEqual(row.error,'DomainOwnersRemain')
  self.assertFalse(self.mod.scope._closed)
  self.mod.scope._native_owners.clear()
 def test_failed_disable_retains_scope_and_module_without_replay(self):
  self.enable();scope=self.mod.scope;self.mod.fail_disable=True
  with self.assertRaisesRegex(ModError,'cleanup pending'):self.loader.unload('World')
  self.assertIs(self.loader._loaded['World'][2],scope);self.assertFalse(scope._closed)
  self.assertEqual(self.coordinator.bindings['World'].state,'unknown')
  with self.assertRaises(ModError):self.loader.disable('World')
  self.assertEqual(self.mod.events.count('disable'),1)
 def test_invalid_adapter_outcome_keeps_owner(self):
  self.enable();self.mod.outcomes=[True];self.coordinator.observe(None,title=True);self.loader.poll()
  self.assertEqual(self.coordinator.bindings['World'].state,'unknown')
  self.assertIsNotNone(self.loader._loaded['World'][2])
 def test_old_debug_callback_cannot_run_after_new_scope_activation(self):
  self.enable();callback=self.loader.actions.actions['world.action']['callback']
  self.coordinator.observe(ready(9));self.loader.poll();self.loader.enable('World');self.mod.events.clear()
  with self.assertRaises((RuntimeError,WorldLifecycleError)):callback()
  self.assertEqual(self.mod.events,[])
 def test_child_scope_journal_survives_adapter_detaching_its_lists(self):
  from expedition33._scope import SessionScope
  self.enable();scope=self.mod.scope;child=SessionScope(scope);lease=N(_state='pending_release')
  child._leases.append(lease)
  def begin(context):scope._children.clear();return 'ack'
  self.mod.begin_world_retirement=begin
  def close():child._leases.clear();child._closed=True
  child.close=Mock(side_effect=close)
  self.coordinator.observe(None,title=True);self.loader.poll()
  self.assertIs(self.loader._loaded['World'][2],scope);child.close.assert_called_once()
  lease._state='released';self.loader.poll();self.assertIsNone(self.loader._loaded['World'][2])
 def test_target_exit_marker_is_not_a_normal_release_ack(self):
  self.enable();scope=self.mod.scope;lease=N(_state='target_exited')
  scope._leases.append(lease)
  def close():scope._leases.clear();scope._closed=True
  scope.close=Mock(side_effect=close)
  self.coordinator.observe(None,title=True);self.loader.poll()
  row=self.coordinator.bindings['World'];self.assertEqual(row.state,'unknown')
  self.assertIs(self.loader._loaded['World'][2],scope)
 def test_readiness_loss_cancels_world_capture_but_preserves_process_capture(self):
  self.enable();self.coordinator.observe(None)
  world=N(scope=self.mod.scope);process=N(scope=N(_world_callback_readiness=None))
  for owner,expected in ((world,True),(process,False)):
   keys=N(session=self.shared,_capture=(owner,Mock()),cancel_capture=Mock(),poll=Mock(return_value=0),close=Mock())
   self.loader._keys=keys
   with patch('expedition33._session.supports_keys',return_value=True):self.loader.poll()
   self.assertEqual(keys.cancel_capture.called,expected)
  self.loader._keys=None

if __name__=='__main__':unittest.main()
