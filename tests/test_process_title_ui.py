import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33.ownership import ObjectLease
from expedition33.sdk import Session
from expedition33.invocation import InvocationError,UnsupportedInvocation
from expedition33._metadata_stabilization import UnstableUIIdentity
from expedition33.frontend_rejection import known_rejection

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/process_title_ui.py'
spec=importlib.util.spec_from_file_location('expedition33._title_driver_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.events=[]
        self.scope=N(close=Mock(side_effect=lambda:self.events.append('scope.close')))
        self.entry=N(poll=Mock(),close=Mock(side_effect=lambda:self.events.append('entry.close')))
        self.service=N(poll=Mock(),menu=N(poll_scroll=Mock(),panel=N(state='built')),
            close=Mock(side_effect=lambda:self.events.append('service.close')))
        def hide():
            self.events.append('menu.hide.ack')
            self.service.menu.panel.state='built'
        self.service.close_menu=Mock(side_effect=hide)
        def dispose():
            self.events.append('menu.dispose.ack')
            self.service.menu=None;self.service._failure=None
        self.service.dispose_menu=Mock(side_effect=dispose)
        self.entry.restore_title_input_after_menu_close=Mock(return_value=True)
        self.entry.open=Mock(return_value='opened')
        self.session=N(poll=Mock())
        self.sf=Mock(return_value=self.scope);self.ef=Mock(return_value=self.entry);self.nf=Mock(return_value=self.service)
        self.driver=m.ProcessTitleUI(self.session,object(),scope_factory=self.sf,
            service_factory=self.nf,entry_factory=self.ef,view_factory=object(),menu_factory=object())
        self.imports=patch.dict(sys.modules,{'expedition33.title_menu':N(TitleMenuEntry=self.ef),
            'expedition33.title_management':N(TitleWorkspaceView=object())})
        self.imports.start();self.addCleanup(self.imports.stop)

    def test_no_title_or_uncertain_without_owners_does_not_touch_native(self):
        self.driver.poll(None);self.driver.poll(False)
        self.session.poll.assert_not_called();self.sf.assert_not_called()

    def test_title_tick_is_only_session_title_service_and_scroll(self):
        self.driver.poll(True)
        self.session.poll.assert_called_once_with();self.entry.poll.assert_called_once_with()
        self.service.poll.assert_called_once_with();self.service.menu.poll_scroll.assert_called_once_with()
        self.assertTrue(self.driver.active)
        self.driver.poll(True);self.sf.assert_called_once()

    def test_cleanup_order_acknowledges_title_before_scope_release(self):
        self.driver.poll(True);self.driver.poll(False)
        self.assertEqual(self.events,['entry.close','service.close','scope.close'])
        self.assertFalse(self.driver.active)

    def test_deferred_detach_retains_owners_until_next_ack(self):
        self.driver.poll(True)
        self.entry.close.side_effect=RuntimeError('Pause entry detach deferred; retain its owner')
        self.driver.poll(False)
        self.assertTrue(self.driver.active);self.assertTrue(self.driver.cleanup_pending)
        self.service.close.assert_not_called();self.scope.close.assert_not_called()
        self.entry.close.side_effect=None
        self.driver.poll(False)
        self.assertFalse(self.driver.active);self.assertFalse(self.driver.cleanup_pending)

    def test_unknown_cleanup_error_visible_retains_ownership(self):
        self.driver.poll(True)
        self.entry.close.side_effect=RuntimeError('unknown dispatch')
        with self.assertRaisesRegex(RuntimeError,'unknown dispatch'):self.driver.poll(False)
        self.assertTrue(self.driver.active);self.service.close.assert_not_called()

    def test_entry_waits_for_built_shell(self):
        self.service.menu.panel.state='new'
        self.driver.poll(True)
        self.entry.poll.assert_not_called()
        self.service.menu.panel.state='built'
        self.driver.poll(True)
        self.entry.poll.assert_called_once_with()

    def test_shutdown_open_title_hides_menu_before_entry_input_restore(self):
        self.driver.poll(True)
        self.service.menu.panel.state='open'
        self.driver.close()
        self.assertEqual(self.events,['menu.hide.ack','entry.close','service.close','scope.close'])

    def test_unknown_menu_hide_preserves_all_owners_and_skips_entry_restore(self):
        self.driver.poll(True);self.service.menu.panel.state='open'
        self.service.close_menu.side_effect=RuntimeError('unknown native menu hide')
        with self.assertRaisesRegex(RuntimeError,'unknown native menu hide'):self.driver.close()
        self.assertIs(self.driver.entry,self.entry);self.assertIs(self.driver.service,self.service)
        self.entry.close.assert_not_called();self.service.close.assert_not_called();self.scope.close.assert_not_called()

    def test_unacknowledged_menu_hide_never_restores_title_input(self):
        self.driver.poll(True);self.service.menu.panel.state='open'
        self.service.close_menu.side_effect=None
        with self.assertRaisesRegex(RuntimeError,'hide acknowledgement is unresolved'):self.driver.close()
        self.entry.close.assert_not_called();self.assertTrue(self.driver.active)

    def test_deferred_menu_hide_keeps_entry_and_retries_only_cleanup(self):
        self.driver.poll(True);self.service.menu.panel.state='open'
        self.service.close_menu.side_effect=RuntimeError('Native menu detach is pending; keep its owner')
        self.driver.poll(False)
        self.assertTrue(self.driver.cleanup_pending);self.entry.close.assert_not_called()

    def test_descendant_gc_deferred_lease_keeps_driver_active_until_session_ack(self):
        self.driver.poll(True)
        class LeaseSession:
            _closed=False
            def __init__(self):
                self._transport=N(_check_thread=lambda:None);self._leases=set();self._menus=()
                self.attempts=0
            def _release_lease(self,lease):
                self.attempts+=1
                if self.attempts==1:lease._state='pending_release';return False
                lease._state='released';self._leases.remove(lease);return True
            def poll(self):Session._release_pending_leases(self)
        session=LeaseSession();lease=ObjectLease(session,1,object());session._leases.add(lease)
        child=N(_leases=[lease],_children=[])
        self.scope._leases=[];self.scope._children=[child]
        def legacy_scope_close():
            lease.release()  # GC deferred False, then legacy lists are cleared.
            child._leases.clear();self.scope._children.clear()
        self.scope.close.side_effect=legacy_scope_close
        self.driver.session=session
        self.driver.poll(False)
        self.assertEqual(session.attempts,1)
        self.assertTrue(self.driver.active);self.assertTrue(self.driver.cleanup_pending)
        self.assertIsNone(self.driver.scope)
        self.assertEqual(self.driver.status()['pending_leases'],1)
        self.driver.poll(False)
        self.assertEqual(session.attempts,2)
        self.assertFalse(self.driver.active)
        self.assertEqual(lease._state,'released')

    def test_unknown_and_target_exit_lease_are_not_acknowledgement_or_retried(self):
        for state in ('unknown','invalid','target_exited'):
            with self.subTest(state=state):
                driver=m.ProcessTitleUI(self.session,object())
                lease=N(_state=state,release=Mock())
                driver.scope=N(_leases=[lease],_children=[],close=Mock())
                with self.assertRaisesRegex(RuntimeError,'unresolved outcomes'):driver.close()
                self.assertTrue(driver.active);lease.release.assert_not_called()

    def test_unrelated_session_lease_is_never_captured(self):
        self.driver.poll(True)
        self.session._leases=[N(_state='unknown')]
        self.driver.close()
        self.assertFalse(self.driver.active)

    def test_known_not_dispatched_202_recovers_detached_menu_without_retry(self):
        self.driver.poll(True)
        error=InvocationError('private rejected payload',outcome='not_dispatched',native_error=202)
        self.entry.open.side_effect=error;self.service._failure='InvocationError'
        self.driver.open()
        self.assertIsNone(self.service.menu)
        self.assertFalse(self.driver.frontend_cleanup_pending)
        self.assertEqual(self.driver.frontend_failed,dict(type='InvocationError',native_error=202,outcome='not_dispatched'))
        self.entry.restore_title_input_after_menu_close.assert_called_once_with()
        self.driver.poll(True)
        self.assertEqual(self.entry.open.call_count,1)
        with self.assertRaisesRegex(RuntimeError,'suspended'):self.driver.open()

    def test_known_202_pending_disposal_keeps_owner_until_ack(self):
        self.driver.poll(True)
        self.entry.open.side_effect=InvocationError('reject',outcome='not_dispatched',native_error=202)
        self.service.dispose_menu.side_effect=RuntimeError('Native menu cleanup is pending; keep its owner and try close after polling')
        self.driver.open()
        self.assertTrue(self.driver.frontend_cleanup_pending)
        self.entry.restore_title_input_after_menu_close.assert_not_called()
        self.assertIsNotNone(self.service.menu)

    def test_unknown_open_error_is_not_recovered_or_replayed(self):
        self.driver.poll(True)
        self.entry.open.side_effect=InvocationError('unknown',outcome='unknown',native_error=202)
        with self.assertRaises(InvocationError):self.driver.open()
        self.service.dispose_menu.assert_not_called()
        self.entry.restore_title_input_after_menu_close.assert_not_called()
        self.assertIsNone(self.driver.frontend_failed)

    def test_close_disposes_failed_built_menu_before_entry_restore(self):
        self.driver.poll(True);self.service._failure='InvocationError'
        def dispose_failed():self.events.append('menu.dispose.ack');self.service.menu=None;self.service._failure=None
        self.service.close_menu.side_effect=dispose_failed
        self.driver.close()
        self.assertEqual(self.events,['menu.dispose.ack','entry.close','service.close','scope.close'])

    def _unstable_entry(self):
        self.entry.state='failed'
        self.entry.poll.side_effect=UnstableUIIdentity('object_patch')
        def acknowledged():
            self.events.append('entry.close');self.entry.state='closed'
        self.entry.close.side_effect=acknowledged

    def test_typed_preflight_is_bounded_and_generic_unsupported_is_not_recovered(self):
        error=UnstableUIIdentity('function')
        self.assertIsInstance(error,UnsupportedInvocation)
        record=known_rejection(error)
        self.assertEqual((record.kind,record.native_error,record.outcome,record.role),
            ('UnstableUIIdentity',0,'not_dispatched','function'))
        with self.assertRaises(ValueError):UnstableUIIdentity('private arbitrary payload')
        self.entry.poll.side_effect=UnsupportedInvocation('other unsupported operation')
        with self.assertRaises(UnsupportedInvocation):self.driver.poll(True)
        self.assertIsNone(self.driver.frontend_failed)
        self.service.dispose_menu.assert_not_called()

    def test_unattached_preflight_disposes_all_owners_then_stays_suspended(self):
        self._unstable_entry();self.driver.poll(True)
        self.assertEqual(self.events,['menu.dispose.ack','entry.close','service.close','scope.close'])
        self.assertFalse(self.driver.active);self.assertFalse(self.driver.frontend_cleanup_pending)
        self.assertEqual(self.driver.frontend_failed,dict(type='UnstableUIIdentity',native_error=0,
            outcome='not_dispatched',role='object_patch'))
        self.entry.restore_title_input_after_menu_close.assert_not_called()
        for _ in range(3):self.driver.poll(True)
        self.sf.assert_called_once();self.entry.poll.assert_called_once()

    def test_unattached_preflight_defers_entry_close_until_ack(self):
        self._unstable_entry();ack=self.entry.close.side_effect
        self.entry.close.side_effect=RuntimeError('Pause entry detach deferred; retain its owner')
        self.driver.poll(True)
        self.assertTrue(self.driver.frontend_cleanup_pending);self.assertIs(self.driver.entry,self.entry)
        self.service.close.assert_not_called();self.scope.close.assert_not_called()
        self.entry.close.side_effect=ack;self.driver.poll(True)
        self.assertFalse(self.driver.active);self.sf.assert_called_once()

    def test_unattached_preflight_unknown_cleanup_retains_owners_and_propagates(self):
        self._unstable_entry();self.entry.close.side_effect=RuntimeError('unknown cleanup outcome')
        with self.assertRaisesRegex(RuntimeError,'unknown cleanup'):self.driver.poll(True)
        self.assertIs(self.driver.entry,self.entry);self.assertTrue(self.driver.active)
        self.service.close.assert_not_called();self.scope.close.assert_not_called()

    def test_unattached_preflight_gc_deferral_keeps_journal_until_poll_ack(self):
        self._unstable_entry();lease=N(_state='pending_release',release=Mock())
        self.scope._leases=[lease];self.scope._children=[]
        self.driver.poll(True)
        self.assertTrue(self.driver.active);self.assertTrue(self.driver.frontend_cleanup_pending)
        self.assertEqual(self.driver.status()['pending_leases'],1);lease.release.assert_not_called()
        self.session.poll.side_effect=lambda:setattr(lease,'_state','released')
        self.driver.poll(True)
        self.assertFalse(self.driver.active);self.sf.assert_called_once();lease.release.assert_not_called()

    def test_attached_typed_preflight_keeps_existing_input_restore_path(self):
        self.driver.poll(True);self.entry.state='attached'
        self.entry.open.side_effect=UnstableUIIdentity('constraint')
        self.driver.open()
        self.entry.restore_title_input_after_menu_close.assert_called_once_with()
        self.entry.close.assert_not_called();self.assertIs(self.driver.entry,self.entry)

    def test_recorded_typed_preflight_cleans_unattached_owner(self):
        self.driver.poll(True);self.entry.state='failed'
        self.entry.close.side_effect=lambda:setattr(self.entry,'state','closed')
        self.service._frontend_rejection=known_rejection(UnstableUIIdentity('target'))
        self.driver.poll(True)
        self.assertFalse(self.driver.active);self.assertEqual(self.driver.frontend_failed['role'],'target')


if __name__=='__main__':unittest.main()
