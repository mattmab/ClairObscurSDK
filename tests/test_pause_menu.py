import unittest
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.pause_menu import PauseMenuEntry

class PauseMenuLifecycleTests(unittest.TestCase):
    def test_failed_open_restores_pause_and_focus_without_retry(self):
        o = self.entry(); events = []
        o.observer.read.return_value = [object()]
        o.attachment.conceal.side_effect = lambda *a: events.append('conceal') or True
        o.attachment.restore.side_effect = lambda: events.append('restore') or True
        o.invoke.side_effect = lambda call: events.append(call) or True
        o.service.open.side_effect = RuntimeError('native_error=811')
        with self.assertLogs('expedition33.pause_menu', level='ERROR'):
            o.poll()
        self.assertEqual(events, ['active', 'conceal', 'viewport', 'restore', 'active', 'button'])
        self.assertEqual(o.state, 'failed')
        o.poll()
        o.service.open.assert_called_once()

    def test_failed_open_with_deferred_restore_retains_owner_without_focus(self):
        o = self.entry()
        o.observer.read.return_value = [object()]
        o.service.open.side_effect = RuntimeError('native_error=811')
        o.attachment.restore.return_value = False
        with self.assertLogs('expedition33.pause_menu', level='ERROR'):
            o.poll()
        self.assertEqual(o.state, 'failed')
        self.assertIn('restoration deferred', o.error)
        self.assertNotIn(unittest.mock.call('button'), o.invoke.call_args_list)
        o.attachment.close.assert_not_called()

    def test_management_restores_pause_before_warmup_after_travel(self):
        mod_type = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'mods/SDKManagement/mod.py'))['Mod']
        mod = mod_type(); events = []
        mod.native = SimpleNamespace(travel_recovery_pending=False, menu=None,
                                     poll=Mock(side_effect=lambda: events.append('warmup')))
        mod.pause = SimpleNamespace(available=True, state='attached')
        def travel():
            events.append('travel-cleanup')
            mod.pause.state = 'new'
        mod.pause.poll = Mock(side_effect=travel)
        mod.poll()
        self.assertEqual(events, ['travel-cleanup'])
        def attach():
            events.append('attach')
            mod.pause.state = 'attached'
        mod.pause.poll.side_effect = attach
        mod.poll()
        self.assertEqual(events, ['travel-cleanup', 'attach', 'warmup'])

    def entry(self):
        root=SimpleNamespace(_transport=SimpleNamespace(pause_attachment_protocol=2,trace_renew_protocol=1))
        service=SimpleNamespace(menu=SimpleNamespace(panel=SimpleNamespace(state='built')),open=Mock())
        owner=PauseMenuEntry(SimpleNamespace(_session=root),service)
        owner.state='attached'
        owner.observer=SimpleNamespace(read=Mock(return_value=[]),state='active',_observed=0,renew=Mock(),close=Mock())
        owner._renew_at=float('inf')
        owner._next_world_check=float('inf')
        owner.attachment=SimpleNamespace(conceal=Mock(return_value=True),restore=Mock(return_value=True),close=Mock(return_value=True))
        owner._active_call='active';owner._viewport_focus='viewport';owner._button_focus='button'
        owner._hide_opacity='opacity';owner._hide_enabled='enabled'
        owner.invoke=Mock(return_value=True)
        return owner

    def test_travel_cleans_owners_before_rebuilding(self):
        o=self.entry(); events=[]
        o.parent_scope.pid=1
        o.player=SimpleNamespace(index=1,serial=1,address=100);o.local_player=SimpleNamespace(index=9,serial=10,address=900);o._local_player_owner='owner'
        o.planner=SimpleNamespace(_catalog='catalog')
        o._next_world_check=0
        o.close=Mock(side_effect=lambda:events.append('detach'))
        o.service.dispose_menu=Mock(side_effect=lambda:events.append('dispose'))
        with patch('expedition33.pause_menu.ReadBatch'), patch('expedition33.pause_menu.capture_selected',return_value='fresh'), patch('expedition33.pause_menu.read_object_reference',return_value=(SimpleNamespace(index=2,serial=2,address=200),None)):
            o.poll()
        self.assertEqual(events,['detach','dispose'])
        self.assertEqual(o.state,'new')

    def test_travel_cleanup_failure_keeps_owner_and_stops(self):
        o=self.entry();o.parent_scope.pid=1
        o.player=SimpleNamespace(index=1,serial=1,address=100);o.local_player=SimpleNamespace(index=9,serial=10,address=900);o._local_player_owner='owner'
        o.planner=SimpleNamespace(_catalog='catalog');o._next_world_check=0
        o.close=Mock(side_effect=RuntimeError('unknown detach'))
        o.service.dispose_menu=Mock()
        with patch('expedition33.pause_menu.ReadBatch'), patch('expedition33.pause_menu.capture_selected',return_value='fresh'), patch('expedition33.pause_menu.read_object_reference',return_value=(SimpleNamespace(index=2,serial=2,address=200),None)):
            with self.assertLogs('expedition33.pause_menu',level='ERROR'):o.poll()
        self.assertEqual(o.state,'failed')
        o.service.dispose_menu.assert_not_called()

    def test_selection_uses_controller_reference_not_retained_old_widget(self):
        catalog=Mock();player=SimpleNamespace(object_flags=0)
        catalog.select.return_value=[player]
        local=SimpleNamespace(class_name='LocalPlayer')
        pause=SimpleNamespace(class_name='WBP_PauseMenu_C')
        with patch('expedition33.pause_menu.read_values',return_value=SimpleNamespace(values={(1,'Player'):local,(2,'PauseMenuWidget'):pause})):
            self.assertEqual(PauseMenuEntry.current_entry(catalog),(player,pause))

    def test_gc_flag_changes_do_not_trigger_rebuild(self):
        o=self.entry();o.parent_scope.pid=1
        o.player=SimpleNamespace(index=1,serial=2,address=100,item_flags=1)
        current=SimpleNamespace(index=1,serial=2,address=100,item_flags=4)
        o.local_player=SimpleNamespace(index=9,serial=10,address=900);o._local_player_owner='owner'
        o.planner=SimpleNamespace(_catalog='catalog');o._next_world_check=0
        o.close=Mock()
        with patch('expedition33.pause_menu.ReadBatch'), patch('expedition33.pause_menu.capture_selected',return_value='fresh'), patch('expedition33.pause_menu.read_object_reference',return_value=(current,None)):
            o.poll()
        self.assertEqual(o.state,'attached');o.close.assert_not_called()

    def test_travel_observation_does_not_merge_into_old_world_catalog(self):
        o=self.entry();o.parent_scope.pid=1
        o.player=SimpleNamespace(index=1,serial=2,address=100)
        o.local_player=SimpleNamespace(index=9,serial=10,address=900)
        o._local_player_owner='owner';o.planner=SimpleNamespace(_catalog='stale-world')
        o._next_world_check=0
        with patch('expedition33.pause_menu.ReadBatch'), patch('expedition33.pause_menu.capture_selected',return_value='fresh') as capture, patch('expedition33.pause_menu.read_object_reference',return_value=(o.player,None)) as read:
            o.poll()
        capture.assert_called_once_with(1,((9,10,900),))
        read.assert_called_once_with('fresh',o.local_player,'owner','PlayerController')
        self.assertEqual(o.state,'attached')

    def test_close_restores_pause_before_focus(self):
        o=self.entry();events=[];o._return_focus=True
        o.attachment.restore.side_effect=lambda:events.append('restore') or True
        o.invoke.side_effect=lambda call:events.append(call) or True
        o.poll()
        self.assertEqual(events,['restore','active','button'])
        self.assertFalse(o._return_focus)

    def test_failed_restore_never_focuses_or_silently_retries(self):
        o=self.entry();o._return_focus=True;o.attachment.restore.side_effect=RuntimeError('unknown')
        with self.assertLogs('expedition33.pause_menu',level='ERROR'):o.poll()
        o.poll()
        self.assertEqual(o.state,'failed');o.invoke.assert_not_called()
        o.attachment.restore.assert_called_once()

    def test_disposed_menu_also_restores_borrowed_pause_panel(self):
        o=self.entry();o._return_focus=True;o.service.menu=None
        o.poll()
        o.attachment.restore.assert_called_once();self.assertFalse(o._return_focus)

    def test_expired_observer_is_not_reinstalled(self):
        o=self.entry();o.observer.state='expired'
        with self.assertLogs('expedition33.pause_menu',level='ERROR'):o.poll()
        self.assertEqual(o.state,'failed');o.observer.renew.assert_not_called()

    def test_cleanup_revokes_observer_then_detaches_before_releasing(self):
        o=self.entry();events=[]
        o.observer.close.side_effect=lambda:events.append('observer')
        o.attachment.close.side_effect=lambda:events.append('detach') or True
        o.scope=SimpleNamespace(close=lambda:events.append('leases'))
        o.close();o.close()
        self.assertEqual(events,['observer','detach','leases'])

if __name__=='__main__':unittest.main()
