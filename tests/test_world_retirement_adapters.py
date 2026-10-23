import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from expedition33.introspection import Harness
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location('adapter_'+name,ROOT/'mods'/name/'mod.py',submodule_search_locations=[str(ROOT/'mods'/name)])
 module=importlib.util.module_from_spec(spec)
 import sys
 sys.modules[spec.name]=module;spec.loader.exec_module(module);return module
intro=load('IntrospectionHarness');loader=load('WorldBuilderMapLoader');travel=load('MapTravel')
class Lease:
 def __init__(self):self._state='active';self.calls=0;self.fail=False
 def release(self):
  self.calls+=1
  if self.fail:self._state='unknown';raise RuntimeError('unknown native ACK')
  self._state='pending_release' if self.calls==1 else 'released'
  return self._state=='released'
class RetirementTests(unittest.TestCase):
 def test_introspection_retained_result_waits_for_exact_pending_lease_ack(self):
  model=intro.Mod();model.harness=Harness();lease=Lease();value=object()
  owner=SimpleNamespace(_leases=[lease],release=Mock(side_effect=lease.release))
  model.harness._explorer.values['owned']=value
  model.harness._explorer._owners['owned']=(value,owner)
  model.service=Mock(_busy=False);service=model.service
  command=Mock();model._commands=[command]
  model.revoke_world(object());service.revoke.assert_called_once()
  self.assertEqual(model.begin_world_retirement(object()),'pending')
  self.assertEqual(lease.calls,1);self.assertIsNotNone(model.harness)
  self.assertEqual(model.poll_world_retirement(object()),'ack')
  # Existing sweep performs the first release (deferred); adapter subsequently
  # observes and polls only that exact known deferred lease.
  self.assertEqual(lease.calls,2);owner.release.assert_called_once()
  command.remove.assert_called_once();self.assertIsNone(model.harness)
  self.assertEqual(model.poll_world_retirement(object()),'ack');self.assertEqual(lease.calls,2)
 def test_introspection_unknown_close_preserves_harness_and_exact_lease(self):
  model=intro.Mod();model.harness=Harness();harness=model.harness;lease=Lease();lease.fail=True;value=object()
  owner=SimpleNamespace(_leases=[lease],release=lease.release)
  harness._explorer.values['owned']=value;harness._explorer._owners['owned']=(value,owner)
  model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'unknown')
  self.assertIs(model.harness,harness);self.assertIs(model._retirement_leases[0],lease)
  self.assertEqual(model.poll_world_retirement(object()),'unknown');self.assertEqual(lease.calls,1)
 def test_introspection_revocation_blocks_direct_and_mod_requests(self):
  model=intro.Mod();model.harness=Harness();harness=model.harness
  model.revoke_world(object())
  with self.assertRaisesRegex(RuntimeError,'retiring'):harness.request({'op':'status'})
  with self.assertRaisesRegex(RuntimeError,'retiring'):model.request({'op':'status'})
  self.assertEqual(model.begin_world_retirement(object()),'ack')
 def test_introspection_busy_dispatch_waits_without_close(self):
  model=intro.Mod();model.harness=Harness();model.service=Mock(_busy=True)
  model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'pending')
  model.service.close.assert_not_called()
  model.service._busy=False
  self.assertEqual(model.poll_world_retirement(object()),'ack')
 def test_introspection_trace_failure_latches_without_forget_replay(self):
  model=intro.Mod();model.harness=Harness();trace=Mock()
  trace.close.side_effect=RuntimeError('trace forget unknown')
  model.harness._explorer._trace_adapter=trace
  model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'unknown')
  self.assertEqual(model.poll_world_retirement(object()),'unknown');trace.close.assert_called_once()
 def test_map_loader_pending_worker_and_active_owner_are_not_false_ack(self):
  model=loader.Mod();model.runtime=SimpleNamespace(retire_world=lambda:'ack',started=False,uncertain=False,objects={})
  model._context_monitor=Mock();model._context_monitor.close.return_value=False
  model.revoke_world(object());self.assertEqual(model.begin_world_retirement(object()),'pending')
  model._context_monitor.close.return_value=True
  self.assertEqual(model.poll_world_retirement(object()),'ack')
  held=loader.Mod();held.runtime=Mock(started=True,uncertain=False,objects={})
  held.revoke_world(object());self.assertEqual(held.begin_world_retirement(object()),'unknown')
  held.runtime.close.assert_not_called()
 def test_map_loader_retirement_waits_for_worker_before_native_owner_cleanup(self):
  model=loader.Mod();model.runtime=Mock();model.runtime.retire_world.return_value='ack'
  model._context_monitor=Mock();model._context_monitor.close.return_value=False
  model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'pending')
  model.runtime.retire_world.assert_not_called()
  model._context_monitor.close.return_value=True
  self.assertEqual(model.poll_world_retirement(object()),'ack')
  model.runtime.retire_world.assert_called_once()

 def test_map_loader_composes_explicit_panel_runtime_retire_ack_without_close(self):
  model=loader.Mod();panel=Mock();runtime=Mock()
  panel.retire_world.side_effect=['pending','ack'];runtime.retire_world.return_value='ack'
  model.panel=panel;model.runtime=runtime;model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'pending');self.assertIs(model.panel,panel)
  self.assertEqual(model.poll_world_retirement(object()),'ack');self.assertIsNone(model.panel)
  panel.close.assert_not_called();runtime.close.assert_not_called()
 def test_map_loader_unknown_retire_never_replays_graceful_cleanup(self):
  model=loader.Mod();model.runtime=Mock()
  model.runtime.retire_world.side_effect=RuntimeError('native release unknown')
  self.assertEqual(model.begin_world_retirement(object()),'unknown')
  self.assertEqual(model.poll_world_retirement(object()),'unknown')
  model.runtime.retire_world.assert_called_once();model.runtime.close.assert_not_called()

 def test_map_travel_uses_only_explicit_epoch_retire_api_and_waits_for_ack(self):
  model=travel.Mod();entry=Mock(state='attached');entry.attachment=SimpleNamespace(state='armed')
  entry.retire_world.side_effect=['pending','ack'];model.pause=entry
  model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'pending');self.assertIs(model.pause,entry)
  self.assertEqual(model.poll_world_retirement(object()),'ack');self.assertIsNone(model.pause)
  entry.close.assert_not_called();self.assertEqual(entry.retire_world.call_count,2)
 def test_map_travel_epoch_retire_failure_never_replays(self):
  model=travel.Mod();entry=Mock(state='attached');entry.attachment=SimpleNamespace(state='armed')
  entry.retire_world.side_effect=RuntimeError('unknown retire ACK');model.pause=entry
  self.assertEqual(model.begin_world_retirement(object()),'unknown')
  self.assertEqual(model.poll_world_retirement(object()),'unknown');entry.retire_world.assert_called_once()

 def test_map_travel_does_not_restore_retired_borrowed_pause(self):
  model=travel.Mod();model.pause=Mock(state='attached');model.pause.attachment=SimpleNamespace(state='armed')
  model.pending_open=True;model.pending_travel='old route';model.revoke_world(object())
  self.assertEqual(model.begin_world_retirement(object()),'unknown')
  self.assertFalse(model.pending_open);self.assertIsNone(model.pending_travel)
  model.pause.close.assert_not_called()
if __name__=='__main__':unittest.main()
