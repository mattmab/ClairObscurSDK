import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33.invocation import InvocationError
from expedition33.multi_controls import MenuControls,ControlAction,ControlBindBatchRejected
from expedition33.menu import MenuError

ROOT=Path(__file__).resolve().parents[1]/'src/expedition33'
def load(name):
    spec=importlib.util.spec_from_file_location('expedition33._retention_'+name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module
f=load('frontend_rejection')
with patch.dict(sys.modules,{'expedition33.frontend_rejection':f}):
    native=load('management_native');service_module=load('management_service');driver=load('process_title_ui')

def rejection():return InvocationError('do not copy this payload',outcome='not_dispatched',native_error=202)

class FrontendRetentionTests(unittest.TestCase):
    def menu(self,error):
        menu=native.NativeManagementMenu.__new__(native.NativeManagementMenu)
        menu.failure=None;menu._frontend_rejection=None;menu._presentation_suspended=False
        menu.view=N(activate=Mock(return_value=N(closed=False)))
        menu._revoke=Mock();menu._paint=Mock(side_effect=error);menu._bind=Mock()
        return menu

    def test_actual_submit_retains_only_bounded_proven_failure(self):
        menu=self.menu(rejection())
        with self.assertRaises(InvocationError):menu.submit(1,2)
        self.assertEqual(menu._frontend_rejection,f.FrontendRejection('InvocationError',202,'not_dispatched'))
        self.assertNotIn('do not copy',repr(menu._frontend_rejection))
        self.assertFalse(hasattr(menu._frontend_rejection,'__traceback__'))
        self.assertFalse(menu._accept_input)

    def test_unknown_and_generic_returned_errors_do_not_select_recovery(self):
        for error in (InvocationError('unknown',outcome='unknown',native_error=202),
                MenuError('generic',outcome='returned',native_error=1012),RuntimeError('other')):
            menu=self.menu(error)
            with self.assertRaises(type(error)):menu.submit(1,2)
            self.assertIsNone(menu._frontend_rejection)
        self.assertIsNotNone(f.known_rejection(ControlBindBatchRejected(2,1012)))

    def ui(self,menu,*,deferred=False):
        events=[];entry=N(close=Mock(),poll=Mock(),restore_title_input_after_menu_close=Mock(side_effect=lambda:events.append('input.restore') or True))
        service=N(menu=menu,_frontend_rejection=None,poll=Mock())
        def dispose():
            events.append('dispose.attempt')
            if deferred:raise RuntimeError('Native menu cleanup is pending; keep its owner and try close after polling')
            service.menu=None;events.append('dispose.ack')
        service.dispose_menu=Mock(side_effect=dispose)
        ui=driver.ProcessTitleUI(N(poll=Mock()),object(),scope_factory=lambda:N(close=Mock()),service_factory=lambda *a:service,
            entry_factory=lambda *a,**kw:entry,view_factory=object(),menu_factory=object())
        ui.scope=N();ui.service=service;ui.entry=entry;ui._ready=True
        return ui,service,entry,events

    def test_swallowed_actual_callback_failure_drives_ack_cleanup_next_title_tick(self):
        menu=self.menu(rejection())
        session=N(_check=Mock());owner=MenuControls(N(_session=lambda:session,_state='attached',_owner=1))
        control=ControlAction(owner,object(),lambda event:menu.submit(1,2));control._registration=7;control._state='active'
        owner.controls=[control]
        owner.send=Mock(return_value=N(events=(N(registration=7,action=control._action,sequence=1),),dropped=0))
        self.assertEqual(owner.poll(),1);self.assertTrue(control.failures)
        ui,service,entry,events=self.ui(menu)
        ui.poll(True)
        self.assertEqual(events,['dispose.attempt','dispose.ack','input.restore'])
        self.assertFalse(ui.frontend_cleanup_pending);self.assertEqual(ui.frontend_failed['native_error'],202)
        self.assertIsNone(service.menu)
        ui.poll(True);self.assertEqual(service.dispose_menu.call_count,1)
        menu._paint.assert_called_once_with()

    def test_pending_dispose_retains_record_and_never_restores_input_early(self):
        menu=self.menu(rejection())
        with self.assertRaises(InvocationError):menu.submit(1,2)
        ui,service,entry,events=self.ui(menu,deferred=True)
        ui.poll(True)
        self.assertTrue(ui.frontend_cleanup_pending);self.assertIs(service.menu,menu)
        entry.restore_title_input_after_menu_close.assert_not_called()
        def ack():events.append('dispose.ack');service.menu=None
        service.dispose_menu.side_effect=ack;ui.poll(True)
        self.assertFalse(ui.frontend_cleanup_pending);self.assertEqual(events[-2:],['dispose.ack','input.restore'])

    def test_generic_failure_string_alone_cannot_authorize_recovery(self):
        menu=N(failure='InvocationError 202 text only',panel=N(state='built'))
        ui,service,entry,events=self.ui(menu)
        ui.poll(True)
        service.dispose_menu.assert_not_called();self.assertIsNone(ui.frontend_failed)

    def test_service_open_retains_typed_failure_and_clears_only_after_dispose_ack(self):
        scope=N(_check=Mock(),supports_multi_controls=True)
        service=service_module.NativeMenuService(scope,object())
        menu=N(panel=N(state='built'),_view_factory=object(),view=N(close=Mock()),open=Mock(side_effect=rejection()),close=Mock(return_value=False))
        service.menu=menu
        with self.assertRaises(InvocationError):service.open(view_factory=menu._view_factory)
        self.assertIsInstance(service._frontend_rejection,f.FrontendRejection)
        with self.assertRaises(RuntimeError):service.dispose_menu()
        self.assertIsNotNone(service._frontend_rejection)
        menu.close.return_value=True;service.dispose_menu()
        self.assertIsNone(service._frontend_rejection)

if __name__=='__main__':unittest.main()
