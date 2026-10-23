import sys,pathlib,unittest,runpy
from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import Mock,patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
from expedition33.management_service import NativeMenuService
from expedition33.pause_menu import PauseMenuEntry
from expedition33.management import ManagementError
class Menu:
    created=0
    def __init__(self,*a,**kw):
        type(self).created+=1;self.panel=SimpleNamespace(state='new');self.failure=None;self.close_pending=False;self.closed=0
    def _read_operation(self):return nullcontext()
    def prepare(self):self.panel.state='built'
    def close(self):
        self.closed+=1
        if self.close_pending:return False
        self.panel.state='closed';return True
class ReadinessTests(unittest.TestCase):
    def service(self,readiness=None):
        scope=SimpleNamespace(_check=lambda:None,supports_multi_controls=True)
        registry=SimpleNamespace(views=lambda:[],installed=lambda:[])
        return NativeMenuService(scope,registry,menu_factory=Menu,readiness=readiness)
    def test_title_has_no_widget_and_manual_open_fails_safely(self):
        before=Menu.created;s=self.service(lambda:False)
        s.prepare();s.poll();s.poll()
        self.assertIsNone(s.menu);self.assertEqual(Menu.created,before)
        with self.assertRaisesRegex(ManagementError,'ready world'):s.open()
        self.assertIsNone(s.menu)
    def test_ready_transition_once_then_cleanup_and_reactivation(self):
        ready=[False];s=self.service(lambda:ready[0]);s.poll();ready[0]=True;s.poll();owner=s.menu
        s.poll();s.prepare();self.assertIs(s.menu,owner)
        ready[0]=False;s.poll();self.assertIsNone(s.menu);self.assertEqual(owner.closed,1)
        ready[0]=True;s.poll();self.assertIsNot(s.menu,owner)
    def test_pending_cleanup_retains_owner_and_blocks_rebuild(self):
        ready=[True];s=self.service(lambda:ready[0]);s.prepare();owner=s.menu;owner.close_pending=True;ready[0]=False
        with self.assertRaisesRegex(ManagementError,'cleanup is pending'):s.poll()
        self.assertIs(s.menu,owner);self.assertTrue(s._warmup_attempted)
        owner.close_pending=False;s.poll();self.assertIsNone(s.menu);self.assertEqual(owner.closed,2)
    def test_legacy_default_still_prepares(self):
        s=self.service();s.prepare();self.assertIsNotNone(s.menu);self.assertTrue(s.ui_ready)
    def test_travel_recovery_priority_preserved(self):
        ready=[True];s=self.service(lambda:ready[0]);s.prepare();owner=s.menu
        s.travel_recovery=SimpleNamespace(state='recovering',deadline=float('inf'));ready[0]=False;s.poll()
        self.assertIs(s.menu,owner);self.assertEqual(owner.closed,0)
        s.travel_recovery=None;s.poll();self.assertEqual(owner.closed,1)
    def pause(self,ready):
        root=SimpleNamespace(_transport=SimpleNamespace(pause_attachment_protocol=2,trace_renew_protocol=1))
        return PauseMenuEntry(SimpleNamespace(_session=root),SimpleNamespace(),readiness=lambda:ready[0])
    def test_pause_title_no_discovery_and_repeated_ready_installs_once(self):
        ready=[False];p=self.pause(ready);p.install=Mock(side_effect=lambda:setattr(p,'state','attached'))
        p.poll();p.poll();p.install.assert_not_called()
        ready[0]=True;p.poll();p.install.assert_called_once()
        p._next_poll=float('inf');p.poll();p.install.assert_called_once()
    def test_pause_deactivate_retains_pending_attachment_then_rearms(self):
        ready=[False];p=self.pause(ready);p.state='attached';p.attachment=SimpleNamespace(close=Mock(return_value=False))
        with self.assertRaisesRegex(RuntimeError,'detach deferred'):p.poll()
        self.assertEqual(p.state,'attached');self.assertFalse(p._waiting_ready)
        p.attachment.close.return_value=True;p.poll();self.assertEqual(p.state,'closed');self.assertTrue(p._waiting_ready)
        ready[0]=True
        with patch.object(PauseMenuEntry,'install',return_value=False):p.poll()
        self.assertEqual(p.state,'new');self.assertFalse(p._waiting_ready)
    def test_management_core_enables_before_console_attach_without_native_work(self):
        from expedition33._console import Console
        root=SimpleNamespace(_check=lambda:None,_transport=Mock(),_menu_readiness=lambda:False)
        root.console=Console(root)
        scope=SimpleNamespace(_session=root,_check=lambda:None,supports_multi_controls=True,
            console=root.console,mods=SimpleNamespace(views=lambda:[],installed=lambda:[]))
        kind=runpy.run_path(str(ROOT/'mods/SDKManagement/mod.py'))['Mod'];mod=kind()
        mod.enable(scope);mod.prepare();mod.poll()
        self.assertIs(root._native_menu_service,mod.native);self.assertIsNone(mod.native.menu)
        self.assertIn('mods',root.console.dispatcher.command_names)
        root._transport.command.assert_not_called();self.assertFalse(root.console._enabled)
        mod.disable();self.assertNotIn('mods',root.console.dispatcher.command_names)
    def test_non_callable_provider_rejected(self):
        with self.assertRaises(TypeError):self.service(True)
        with self.assertRaises(TypeError):PauseMenuEntry(None,None,readiness=True)
if __name__=='__main__':unittest.main()
