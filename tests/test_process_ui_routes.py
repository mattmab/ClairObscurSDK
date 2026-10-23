import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
from expedition33 import process_ui_routes as routes
class RouteTests(unittest.TestCase):
    def setUp(self):
        self.service=Mock(menu=N(_view_factory=object()),travel_recovery_pending=False)
        self.owner=N(_check=Mock(),context=N(kind='title'),phase='ready',failed=False,
            service=self.service,status=Mock(return_value={'phase':'ready'}),entry=None)
        self.route=routes.ProcessMenuRoute(self.owner)

    def maptravel_child(self,active=True):
        spec=importlib.util.spec_from_file_location('reuse_maptravel_shutdown',ROOT/'mods/MapTravel/mod.py',
            submodule_search_locations=[str(ROOT/'mods/MapTravel')])
        mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
        factory=object();menu=N(_view_factory=factory,view=object())
        service=N(menu=menu,close_menu=Mock())
        owner=N(_check=lambda:None,context=N(kind='world') if active else None,
            phase='ready' if active else 'closed',failed=False,service=service,registry=object())
        model=mod.Mod();model.native=routes.ProcessMenuRoute(owner).for_view(factory);model.pause=Mock()
        return model,owner

    def test_active_maptravel_child_view_cleanup_uses_owning_registry(self):
        model,owner=self.maptravel_child();pause=model.pause
        model.disable();pause.close.assert_called_once()
        self.assertIsNone(model.native);self.assertIsNone(model.session)
        self.assertIs(owner.service.menu.view.registry,owner.registry)

    def test_closed_process_context_is_noop_for_maptravel_borrowed_route(self):
        model,owner=self.maptravel_child(active=False)
        model.disable();owner.service.close_menu.assert_not_called()

    def test_world_route_cannot_open_or_expose_title_staging_tree(self):
        self.assertIsNone(self.route.menu);self.assertFalse(self.route.ui_ready)
        with self.assertRaisesRegex(Exception,'context is not ready'):self.route.open()
        self.route.close_menu();self.service.open.assert_not_called();self.service.close_menu.assert_not_called()

    def test_route_resolves_replacement_service_without_old_pointer(self):
        self.owner.context.kind='world';self.route.open()
        self.service.open.assert_called_once_with(view_factory=None)
        replacement=Mock(menu=object());self.owner.service=replacement
        self.route.open();replacement.open.assert_called_once_with(view_factory=None)
        self.assertIs(self.route.menu,replacement.menu)

    def test_mod_route_uses_host_reader_and_borrows_existing_operation(self):
        from contextlib import contextmanager
        events=[]
        @contextmanager
        def operation():
            events.append('enter')
            try:yield
            finally:events.append('exit')
        self.owner.context.kind='world';self.owner._read_operation=operation
        self.service.open.side_effect=lambda **kw:events.append('open')
        with patch('expedition33._reader.active_reader',return_value=None):self.route.open()
        self.assertEqual(events,['enter','open','exit'])
        events.clear()
        with patch('expedition33._reader.active_reader',return_value=object()):self.route.open()
        self.assertEqual(events,['open'])

    def test_borrower_prepare_poll_close_never_build_or_destroy_host_tree(self):
        self.owner.context.kind='world'
        self.route.prepare();self.route.poll();self.route.close()
        self.service.prepare.assert_not_called();self.service.poll.assert_not_called()
        self.service.close.assert_not_called();self.service.close_menu.assert_called_once_with()
        self.assertIsNone(self.route.menu)

    def test_explicit_disposal_preserves_travel_semantics_requests_fresh_tree(self):
        self.owner.context.kind='world';self.route.dispose_menu()
        self.service.dispose_menu.assert_called_once_with();self.assertTrue(self.owner._rebuild_requested)

    def test_travel_detaches_host_entries_without_disposing_process_tree(self):
        self.owner.context.kind='world';self.owner.quiesce=Mock(return_value=True)
        self.route.prepare_travel()
        self.owner.quiesce.assert_called_once();self.service.dispose_menu.assert_not_called()
        self.owner.quiesce.return_value=False
        with self.assertRaisesRegex(Exception,'cleanup is still pending'):self.route.prepare_travel()

    def test_travel_request_is_retained_on_owner_across_service_replacement(self):
        self.owner.context.signature=('world',1)
        request=object();self.route.travel_recovery=request
        self.assertIs(self.owner._travel_recovery,request)
        self.assertEqual(self.owner._travel_origin,('world',1))

    def test_sdkmanagement_process_branch_constructs_no_second_service_or_entry(self):
        spec=importlib.util.spec_from_file_location('reuse_sdkmanagement',ROOT/'mods/SDKManagement/mod.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        session=N(mods=object(),console=object(),_session=N(_process_ui=self.owner))
        with patch.object(mod,'NativeMenuService') as native,patch.object(mod,'PauseMenuEntry') as pause,patch.object(mod,'ConsoleMenu') as console:
            instance=mod.Mod();instance.enable(session);instance.prepare();instance.poll()
            native.assert_not_called();pause.assert_not_called();console.assert_called_once()
            self.assertIsInstance(instance.native,routes.ProcessMenuRoute)
            self.assertIsInstance(instance.pause,routes.ProcessEntryRoute)
            self.assertIs(session._session._native_menu_service,instance.native)

    def test_sdkmanagement_legacy_branch_keeps_its_existing_native_owners(self):
        spec=importlib.util.spec_from_file_location('reuse_sdkmanagement_legacy',ROOT/'mods/SDKManagement/mod.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        session=N(mods=object(),console=object(),_session=N())
        with patch.object(mod,'NativeMenuService') as native,patch.object(mod,'PauseMenuEntry') as pause,patch.object(mod,'ConsoleMenu'):
            instance=mod.Mod();instance.enable(session)
            native.assert_called_once();pause.assert_called_once()

    def test_console_returns_to_persistent_staging_facade_without_new_attach(self):
        from expedition33 import process_console as module
        registry=N(_settings=object());native=object();menu=N(registry=registry,native=native)
        session=N(console=N(_enabled=True,enable=Mock()))
        console=module.ProcessConsole(session,menu);facade=menu.registry
        console.world_active();self.assertIs(menu.registry,registry);self.assertIs(menu.native,native)
        console.title_active();self.assertIs(menu.registry,facade);self.assertIsNone(menu.native)
        session.console.enable.assert_not_called()

    def test_title_console_uses_title_route_without_world_authority(self):
        from expedition33.management import ManagementError
        from expedition33.process_console import ProcessConsole
        registry=N(_settings=None);native=routes.ProcessMenuRoute(self.owner)
        menu=N(registry=registry,native=native);session=N(console=N(_enabled=True))
        driver=ProcessConsole(session,menu)
        self.owner.open=Mock(return_value='title opened')
        self.owner.context.kind='title'
        self.assertEqual(menu.native.command('open'),'title opened')
        self.owner.open.assert_called_once_with();self.service.open.assert_not_called()
        driver.world_active();self.assertIs(menu.native,native)
        driver.title_active();self.owner.context.kind='world'
        with self.assertRaises(ManagementError):menu.native.command('open')

if __name__=='__main__':unittest.main()
