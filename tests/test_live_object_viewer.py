"""Viewer navigation contract; no game process or fabricated live evidence."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from contextlib import nullcontext

spec = importlib.util.spec_from_file_location('live_object_viewer',
    Path(__file__).resolve().parents[1] / 'mods/LiveObjectViewer/mod.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.harness = Mock()
        self.harness.request.return_value = {'Pawn': [{'$object': '/World.Pawn', 'class': '/Script/Pawn'}]}
        self.browser = module.Browser(self.harness)
        self.browser.refresh()
        self.view = module.BrowserView(SimpleNamespace(_check=lambda: None), self.browser)

    def test_roots_to_object_and_back(self):
        self.browser.select('Pawn')
        self.harness.request.return_value = {'values': {'Health': 10}, 'next_offset': None}
        self.browser.select(0)
        self.assertEqual(self.browser.request['target']['$object'], '/World.Pawn')
        self.assertEqual(self.browser.rows(), [('Health', 10)])
        self.harness.request.return_value = {'Pawn': []}
        self.browser.back()
        self.assertEqual(self.browser.request, {'op': 'roots'})
        self.assertEqual(self.browser.path, ['Pawn'])

    def test_stale_disabled_and_off_page_controls_rejected(self):
        self.browser.result = {'values': {str(n): n for n in range(20)}}
        frame = self.view.render()
        self.assertEqual(len(frame.controls), 12)
        for token in (1, 3, 5, 106):
            with self.assertRaises(module.ManagementError):
                self.view.activate(frame.revision, token)
        next_frame = self.view.activate(frame.revision, 4)
        self.assertEqual(next_frame.page, 1)
        with self.assertRaises(module.ManagementError):
            self.view.activate(frame.revision, 100)

    def test_paging_uses_server_cursor_not_row_count(self):
        self.browser.request = {'op': 'search', 'class': 'Actor'}
        self.browser.result = {'objects': [], 'next_offset': 5000}
        self.harness.request.return_value = {'objects': [], 'next_offset': None}
        self.browser.next_batch()
        self.assertEqual(self.harness.request.call_args.args[0]['offset'], 5000)
        with self.assertRaises(ValueError):
            self.browser.next_batch()

    def test_failed_refresh_clears_stale_values(self):
        self.browser.select('Pawn')
        self.harness.request.side_effect = ValueError('Object no longer exists')
        frame = self.view.render()
        updated = self.view.activate(frame.revision, 2)
        self.assertIn('no longer exists', updated.status)
        self.assertEqual(self.browser.result, {})
        self.assertEqual(self.browser.rows(), [])

    def test_external_failed_navigation_revokes_displayed_controls(self):
        frame = self.view.render()
        self.harness.request.side_effect = ValueError('Missing class')
        with self.assertRaises(ValueError):
            self.browser.navigate({'op': 'search', 'class': 'Missing'})
        with self.assertRaises(module.ManagementError):
            self.view.activate(frame.revision, 100)

    def test_snapshot_is_deep_and_scoped(self):
        result = {'values': {'Health': 10, 'Position': {'X': 1}}}
        self.harness.request.return_value = result
        self.browser.snapshot()
        result['values']['Position']['X'] = 2
        self.assertTrue(self.browser.changed('Position', {'X': 2}))
        self.browser.changed_only = True
        self.assertEqual(self.browser.rows(), [('Position', {'X': 2})])
        self.browser.path = ['Position']
        self.assertEqual(self.browser.rows(), [])
        self.assertFalse(self.browser.changed('X', 2))

    def test_disappearing_nested_path_returns_to_object(self):
        self.browser.result = {'values': {'Array': [1, 2]}}
        self.browser.select('Array')
        self.browser.select(1)
        self.harness.request.return_value = {'values': {'Array': []}}
        self.browser.refresh()
        self.assertEqual(self.browser.path, [])

    def test_schema_navigation_does_not_invoke_functions(self):
        self.browser.request = {'op': 'schema', 'class': 'Actor'}
        self.browser.result = {'functions': [{'name': 'DestroyActor'}], 'next_offset': None}
        self.browser.select('functions')
        self.browser.select(0)
        self.assertEqual(self.browser.rows(), [('name', 'DestroyActor')])
        self.assertEqual(self.harness.request.call_count, 1)

    def test_close_revokes_controls(self):
        frame = self.view.render()
        self.assertTrue(self.view.activate(frame.revision, 6).closed)
        with self.assertRaises(module.ManagementError):
            self.view.activate(frame.revision, 100)

    def test_mod_lifecycle_removes_commands_and_harness(self):
        mod = module.Mod()
        mod.native, mod.harness = Mock(), Mock()
        harness, native = mod.harness, mod.native
        command = Mock()
        mod.commands = [command]
        mod.disable()
        native.close.assert_called_once()
        harness.close.assert_called_once()
        command.remove.assert_called_once()
        self.assertIsNone(mod.browser)

    def test_missing_shared_service_fails_before_allocating(self):
        mod = module.Mod()
        with patch.object(module, 'Harness') as harness:
            with self.assertRaisesRegex(RuntimeError, 'shared native views'):
                mod.enable(SimpleNamespace(_session=SimpleNamespace()))
            harness.assert_not_called()
        self.assertIsNone(mod.native)

    def test_viewer_reuses_management_panel_and_releases_only_route(self):
        from expedition33.management_service import NativeMenuService
        from expedition33.management_view import ManagementView
        from test_management_native import FakePanel
        registry = Mock()
        registry.views.return_value = []
        registry.installed.return_value = []
        scope = Mock(supports_multi_controls=True)
        shared = NativeMenuService(scope, registry)
        session = SimpleNamespace(_session=SimpleNamespace(_native_menu_service=shared),
                                  console=Mock())
        mod = module.Mod()
        with patch('expedition33.management_native.OwnedMenuPanel', side_effect=FakePanel) as panels, \
             patch('expedition33.management_native.NativeManagementMenu._read_operation', lambda _: nullcontext()), \
             patch.object(module, 'Harness', return_value=self.harness):
            shared.prepare()
            panel = shared.menu.panel
            mod.enable(session)
            mod.open()
            self.assertIs(mod.native.menu.panel, panel)
            self.assertEqual(panels.call_count, 1)
            self.assertIn('already open', mod.open())
            # Console refresh paints this view through the shared owner.
            mod.refresh()
            self.assertEqual(shared.menu.frame.title, 'E33 Live Object Viewer')
            mod.toggle()
            self.assertEqual(panel.state, 'built')
            mod.open()
            mod.disable()
            self.assertEqual(panel.state, 'built')
            self.assertIsInstance(shared.menu.view, ManagementView)
            shared.open()
            self.assertEqual(shared.menu.frame.title, 'SDK Mods')
            self.assertEqual(panels.call_count, 1)
            shared.close()

    def test_refresh_does_not_repaint_another_mods_view(self):
        mod = module.Mod()
        mod.browser = self.browser
        mod.native = SimpleNamespace(menu=None)
        mod.shared = Mock()
        mod.refresh()
        mod.shared.refresh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
