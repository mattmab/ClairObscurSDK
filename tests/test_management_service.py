import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_management
import test_management_native
import test_retained_results
from expedition33._scope import SessionScope
from expedition33.management import ManagementError
from expedition33.management_console import ConsoleMenu
from expedition33.management_service import NativeMenuService
from test_mods import FakeSession


class ChildScopeTests(unittest.TestCase):
    setUp = test_retained_results.RetainedResultTests.setUp

    def test_child_release_does_not_revoke_parent_or_sibling(self):
        parent = SessionScope(self.session)
        a, b = SessionScope(parent), SessionScope(parent)
        owner = parent.retain(self.p.target)
        first, second = a.retain(self.p.target), b.retain(self.p.target)
        self.assertIs(a._session, self.session)
        a.close()
        self.assertFalse(first.active)
        self.assertTrue(owner.active and second.active)
        self.assertEqual(parent._children, [b])
        parent.close()
        self.assertFalse(owner.active or second.active)
        self.assertFalse(self.transport.tokens)
        with self.assertRaisesRegex(RuntimeError, 'closed'): b.retain(self.p.target)

    def test_child_cleanup_precedes_parent_and_survives_one_failure(self):
        parent = SessionScope(self.session)
        child = SessionScope(parent)
        events = []
        def fail():
            events.append('child-menu')
            raise RuntimeError('failed close')
        child._menus.append(SimpleNamespace(close=fail))
        parent._hooks.append(SimpleNamespace(remove=lambda: events.append('parent-hook')))
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'): parent.close()
        self.assertEqual(events, ['child-menu', 'parent-hook'])
        self.assertTrue(parent._closed and child._closed)
        self.assertFalse(parent._children)

    def test_nested_prepared_results_use_root_transport_and_child_ownership(self):
        parent = SessionScope(self.session)
        child = SessionScope(parent)
        with child.invocation_planner() as planner:
            result = planner.prepare(self.p.target, self.p.function).invoke()
            self.assertEqual(result.return_value, self.p.target)
            parent.close()
            self.assertFalse(result.active)
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                planner.prepare(self.p.target, self.p.function)
        self.assertFalse(self.transport.tokens)


class NativeServiceTests(unittest.TestCase):
    def setUp(self):
        test_management.ManagementTests.setUp(self)
        patcher = patch('expedition33.management_native.NativeManagementMenu._read_operation',
                        side_effect=lambda: nullcontext())
        patcher.start(); self.addCleanup(patcher.stop)
    tearDown = test_management.ManagementTests.tearDown

    def service(self):
        scope = SimpleNamespace(_check=lambda: None, supports_multi_controls=True)
        service = NativeMenuService(scope, self.registry)
        patcher = patch('expedition33.management_native.OwnedMenuPanel', test_management_native.FakePanel)
        patcher.start(); self.addCleanup(patcher.stop)
        self.addCleanup(service.close)
        return service

    def test_console_routes_native_menu_without_replacing_python_or_native_commands(self):
        service = self.service()
        shared = FakeSession()
        menu = ConsoleMenu(self.registry, shared.console, native=service)
        self.addCleanup(menu.close)
        dispatch = shared.console.dispatcher
        self.assertIn('not_created', dispatch.execute('mods ui status').output)
        self.assertIn('opened', dispatch.execute('mods ui').output)
        original = service.menu
        self.assertTrue(original.panel.selected_results)
        self.assertIn('already open', dispatch.execute('mods ui open').output)
        self.assertIs(original, service.menu)
        self.assertEqual(dispatch.execute('stat fps').route, 'native')
        self.assertEqual(dispatch.execute('py 2 + 3').output.strip(), '5')
        self.assertIn('closed', dispatch.execute('mods ui close').output)
        self.assertIs(service.menu, original)
        self.assertEqual(original.panel.state, 'built')
        self.assertFalse(any(action.active for action in original.panel.handles))
        self.assertIn('opened', dispatch.execute('mods ui').output)
        self.assertIs(original, service.menu)
        self.assertEqual(original.panel.operations.count('build'), 1)

    def test_unsupported_controller_keeps_console_fallback(self):
        service = self.service()
        service.scope.supports_multi_controls = False
        with self.assertRaisesRegex(ManagementError, '--multi-controls'): service.open()
        self.assertIsNone(service.menu)
        self.assertFalse(service.status()['available'])

    def test_routes_share_widgets_and_restore_default_presenter(self):
        from expedition33.management_view import ManagementView
        service = self.service()
        service.prepare()
        original = service.menu
        factory = lambda registry: ManagementView(registry)
        route = service.for_view(factory)
        route.open()
        self.assertIs(route.menu, original)
        self.assertIs(original._view_factory, factory)
        with self.assertRaisesRegex(ManagementError, 'Another native view'):
            route.open()
        route.close()
        self.assertIsNone(route.menu)
        self.assertEqual(original.panel.state, 'built')
        self.assertIs(original._view_factory, ManagementView)
        service.open()
        self.assertIs(service.menu, original)
        self.assertEqual(original.panel.operations.count('build'), 1)
        route.close()  # An inactive route cannot close the default view.
        self.assertEqual(original.panel.state, 'open')

    def test_dispose_releases_hidden_cache_without_automatic_recreation(self):
        service = self.service(); service.prepare()
        owner = service.menu
        self.assertTrue(service.status()['cached_widgets'])
        self.assertEqual(owner.panel.state, 'built')
        service.command('dispose')
        self.assertEqual(owner.panel.state, 'closed')
        service.poll()
        self.assertIsNone(service.menu)
        service.open()
        self.assertIsNot(service.menu, owner)

    def test_click_render_failure_latches_and_is_not_replayed(self):
        service = self.service(); service.open()
        menu = service.menu
        first = menu.frame.controls[0]
        with patch.object(menu, '_paint', side_effect=RuntimeError('batch failed')) as paint:
            with self.assertRaisesRegex(RuntimeError, 'batch failed'):
                menu.submit(menu.frame.revision, first.token)
            service.poll()
            self.assertIn('batch failed', service.status()['error'])
            with self.assertRaisesRegex(ManagementError, 'failed'): service.open()
            paint.assert_called_once_with()
            self.assertFalse(menu._accept_input)

    def test_construction_failure_preserves_owner_and_blocks_second_open(self):
        service = self.service()
        with patch('expedition33.management_native.NativeManagementMenu.open', side_effect=RuntimeError('build failed')):
            with self.assertRaisesRegex(RuntimeError, 'build failed'): service.open()
        original = service.menu
        with self.assertRaisesRegex(ManagementError, 'failed'): service.open()
        self.assertIs(service.menu, original)
        service.close_menu()
        self.assertIsNone(service.menu)

    def test_registry_changes_refresh_and_revoke_prior_controls(self):
        service = self.service(); service.open()
        old = service.menu.actions[0]
        self.loader.enable('Specimen')
        service.poll()
        self.assertFalse(old.active)
        self.assertIn('enabled', service.menu.frame.controls[0].label)
        self.loader.unload('Specimen'); service._next_poll = 0
        service.poll()
        self.assertIn('not loaded', service.menu.frame.controls[0].label)

    def test_refresh_failure_is_not_replayed_and_can_be_closed(self):
        service = self.service(); service.open()
        self.loader.enable('Specimen')
        service.menu.refresh = Mock(side_effect=RuntimeError('paint failed'))
        with self.assertLogs('expedition33.management_service', level='ERROR'):
            service.poll()
        service._next_poll = 0; service.poll()
        service.menu.refresh.assert_called_once_with()
        self.assertFalse(service.menu._accept_input)
        self.assertIn('paint failed', service.status()['error'])
        service.close_menu()

    def test_actual_management_mod_owns_frontend_and_revokes_command_on_disable(self):
        from pathlib import Path
        folder = self.root / 'SDKManagement'
        folder.mkdir()
        source = Path(__file__).resolve().parents[1] / 'mods/SDKManagement/mod.py'
        (folder / 'mod.py').write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
        self.loader.enable('Specimen')
        self.loader._session.supports_multi_controls = True
        self.loader.load('SDKManagement'); self.loader.enable('SDKManagement', console=True)
        instance = self.loader._loaded['SDKManagement'][1]
        dispatch = self.loader._session.console.dispatcher
        with patch('expedition33.management_native.OwnedMenuPanel', test_management_native.FakePanel):
            self.assertFalse(dispatch.execute('mods ui').failed)
        panel = instance.native.menu.panel
        self.loader.disable('SDKManagement')
        self.assertEqual(panel.state, 'closed')
        self.assertNotIn('mods', dispatch.command_names)
        self.assertIsNone(instance.native)
        self.assertFalse(self.loader._session.closed)
        self.assertTrue(self.loader.status()[0].enabled)

    def test_deferred_close_retains_owner_until_acknowledged(self):
        service = self.service(); service.open()
        original = service.menu
        original.panel.defer = True
        with self.assertRaisesRegex(ManagementError, 'pending'): service.close()
        self.assertIs(service.menu, original)
        self.assertFalse(service._closed)
        original.panel.defer = False
        service.close()
        self.assertTrue(service._closed)


if __name__ == '__main__':
    unittest.main()
