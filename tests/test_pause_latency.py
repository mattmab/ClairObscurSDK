import importlib.util,pathlib,sys,types,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from expedition33 import pause_menu as module
PauseMenuEntry=module.PauseMenuEntry
class LatencyTests(unittest.TestCase):
    def test_owner_lookup_uses_one_projected_read_for_all_controllers(self):
        old=SimpleNamespace(index=1,object_flags=0);current=SimpleNamespace(index=2,object_flags=0);dead=SimpleNamespace(index=3,object_flags=0x10)
        local=SimpleNamespace(class_name='LocalPlayer');pause=SimpleNamespace(class_name='WBP_PauseMenu_C')
        cat=Mock();cat.select.return_value=[old,current,dead]
        rows={1:SimpleNamespace(values={(1,'Player'):None,(2,'PauseMenuWidget'):pause}),2:SimpleNamespace(values={(1,'Player'):local,(2,'PauseMenuWidget'):pause})}
        with patch.object(module,'read_values_many',return_value=rows) as read:
            self.assertEqual(PauseMenuEntry.current_entry(cat),(current,pause))
        read.assert_called_once_with(cat,(old,current),fields=('Player','PauseMenuWidget'))
    def test_ambiguity_still_rejected(self):
        players=[SimpleNamespace(index=i,object_flags=0) for i in [1,2]];cat=Mock();cat.select.return_value=players
        row=SimpleNamespace(values={(1,'Player'):SimpleNamespace(class_name='LocalPlayer'),(2,'PauseMenuWidget'):SimpleNamespace(class_name='WBP_PauseMenu_C')})
        with patch.object(module,'read_values_many',return_value={1:row,2:row}):
            with self.assertRaisesRegex(RuntimeError,'Multiple local'):PauseMenuEntry.current_entry(cat)
    def entry(self,warm=True):
        scope=SimpleNamespace(_session=SimpleNamespace())
        service=SimpleNamespace(menu=SimpleNamespace(panel=SimpleNamespace(state='built' if warm else 'new')),open=Mock())
        o=PauseMenuEntry(scope,service);o.invoke=Mock(return_value=True)
        o._loading_label='loading';o._normal_label='normal';o._viewport_focus='viewport';o._hide_enabled='disable';o._hide_opacity='hide'
        o.attachment=SimpleNamespace(show_busy=Mock(return_value=True),hide_busy=Mock(return_value=True),restore=Mock(return_value=True))
        o._active_call='active';o._button_focus='focus';return o
    def test_warm_open_skips_two_feedback_setters_and_keeps_conceal(self):
        o=self.entry();o._open_from_pause()
        self.assertEqual(o.invoke.call_args_list,[unittest.mock.call('viewport')]);o.service.open.assert_called_once()
        o.attachment.show_busy.assert_called_once();o.attachment.hide_busy.assert_called_once();self.assertTrue(o._return_focus)
        self.assertIn('open_total_ms',o.timings)
    def test_cold_open_keeps_loading_feedback(self):
        o=self.entry(False);o._open_from_pause()
        self.assertEqual(o.invoke.call_args_list,[unittest.mock.call('loading'),unittest.mock.call('viewport'),unittest.mock.call('normal')])
    def test_warm_failed_open_restores_once_without_replay(self):
        o=self.entry();o.service.open.side_effect=RuntimeError('failed')
        with self.assertRaises(RuntimeError):o._open_from_pause()
        o.service.open.assert_called_once();o.attachment.restore.assert_called_once()
        self.assertNotIn(unittest.mock.call('loading'),o.invoke.call_args_list)
    def test_route_recognizes_shared_prepared_shell(self):
        o=self.entry();parent=o.service;o.service=SimpleNamespace(parent=parent,menu=None)
        self.assertTrue(o._has_prepared_shell());parent._failure='retained failed owner';self.assertFalse(o._has_prepared_shell())
if __name__=='__main__':unittest.main()
