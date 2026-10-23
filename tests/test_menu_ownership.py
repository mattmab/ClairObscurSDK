import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from expedition33.menu import NativeMenu, MenuError
from expedition33._scope import SessionScope
from expedition33.sdk import Session
from expedition33.ownership import ObjectLease, LeaseError


class FakeSession:
    def __init__(self):
        self._menus, self._leases = set(), set()
        self._closed = False
        self.calls = []
        self.reply = (0,2,1)
        self.aborted = False
        self._transport = SimpleNamespace(_check_thread=lambda: None, command=self.command)
    def _check(self): pass
    def command(self, command, sent):
        self.calls.append(command)
        received = bytearray(sent)
        struct.pack_into('<3I', received, 8, *self.reply)
        return {'menu_packet':received.hex()}
    def _abort_ownership(self): self.aborted = True


class MenuOwnershipTests(unittest.TestCase):
    def test_combined_open_focus_capability_avoids_second_dispatch(self):
        from expedition33 import menu as module
        for capability,expected in ((1,1),(0,2),(True,2)):
            s,m=self.make();s._transport.menu_open_focus_protocol=capability
            with patch.object(module.wire,'request',return_value=bytes(module.wire.SIZE)),patch.object(module.wire,'decode',return_value=SimpleNamespace(error=0,outcome='returned',active=True)):
                m._send('open');m.attach();m.focus()
            self.assertEqual(len(s.calls),expected)

    def make(self):
        session = FakeSession()
        menu = NativeMenu(session, ())
        session._menus.add(menu)
        menu._state = 'prepared'
        return session, menu
    def test_order_and_close(self):
        s,m = self.make()
        with self.assertRaises(MenuError): m.focus()
        self.assertEqual(s.calls, [])
        self.assertTrue(m.attach()); self.assertTrue(m.focus())
        s.reply = (0,2,0)
        self.assertTrue(m.close()); self.assertTrue(m.close())
        self.assertFalse(m.active); self.assertEqual(len(s.calls),3)
        self.assertEqual(s._menus,set())
    def test_deferred_close_keeps_protection(self):
        s,m = self.make()
        lease = object(); m._leases = (lease,)
        s.reply = (813,2,1)
        self.assertFalse(m.close())
        self.assertTrue(m.close_pending and m.protects(lease))
        s.reply = (0,2,0)
        self.assertTrue(m.close()); self.assertFalse(m.protects(lease))
    def test_unknown_never_replayed(self):
        s,m = self.make(); s.reply = (816,1,1)
        with self.assertRaises(MenuError): m.attach()
        self.assertTrue(s.aborted)
        with self.assertRaises(MenuError): m.close()
        self.assertEqual(s.calls,['menu'])
    def test_invalid_prepare_does_not_leave_python_owner(self):
        s,m=self.make(); m._state='preparing'
        with self.assertRaises(ValueError): m._send('prepare')
        self.assertFalse(m.active); self.assertEqual(s._menus,set()); self.assertEqual(s.calls,[])
    def test_acknowledged_rejection_leaves_no_record(self):
        s,m=self.make(); s.reply=(811,2,0)
        with self.assertRaises(MenuError): m.attach()
        self.assertFalse(m.active); self.assertEqual(s._menus,set()); self.assertFalse(s.aborted)
    def test_protected_release_preserves_handle(self):
        s,m = self.make()
        lease = ObjectLease(s,7,object()); s._leases.add(lease); m._leases=(lease,)
        with self.assertRaises(LeaseError): Session._release_lease(s,lease)
        self.assertEqual(lease._state,'active'); self.assertEqual(s.calls,[])
    def test_button_reference_acknowledgement(self):
        for state in (None,True,0,1,3,4,5):
            s,m=self.make(); s._transport.button_reference_protocol=1
            original=s.command
            s._transport.command=lambda command,sent: dict(original(command,sent),button_reference_state=state)
            with self.assertRaises(MenuError): m.attach()
            self.assertTrue(s.aborted)
        s,m=self.make(); s._transport.button_reference_protocol=1
        original=s.command
        s._transport.command=lambda command,sent: dict(original(command,sent),button_reference_state=2)
        self.assertTrue(m.attach()); self.assertEqual(m._button_reference_state,2)
        s.reply=(0,2,0)
        s._transport.command=lambda command,sent: dict(original(command,sent),button_reference_state=0)
        self.assertTrue(m.close()); self.assertEqual(m._button_reference_state,0)
    def test_scope_close_orders_menu_before_leases(self):
        events=[]
        s=FakeSession(); scope=SessionScope(s)
        scope.console._close=lambda: None
        scope._menus=[SimpleNamespace(close=lambda: events.append('menu') or True)]
        scope._leases=[SimpleNamespace(release=lambda: events.append('lease'))]
        scope.close()
        self.assertEqual(events,['menu','lease'])
    def test_scope_deferred_cleanup_remains_session_owned(self):
        s,m=self.make(); scope=SessionScope(s); scope.console._close=lambda: None
        scope._menus=[m]; s.reply=(813,2,1)
        lease=ObjectLease(s,7,object()); s._leases.add(lease); m._leases=(lease,)
        scope._leases=[lease]
        with self.assertRaisesRegex(RuntimeError, 'native menu cleanup deferred'):
            scope.close()
        self.assertEqual(lease._state,'pending_release')
        self.assertTrue(m.close_pending and m in s._menus and lease in s._leases)
