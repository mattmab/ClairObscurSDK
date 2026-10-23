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
        for token in (1, 3, 5, 108):
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
        tools = self.view.activate(frame.revision, 2)
        updated = self.view.activate(tools.revision, 107)
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
        registry._startup_progress = {};registry.views.return_value = [];registry.keys.return_value = []
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

    def test_filter_snapshot_includes_hidden_fields_and_removed_rows(self):
        self.harness.request.return_value={'values':{'Health':10,'Speed':20}}
        self.browser.set_filter('Health')
        self.browser.snapshot()
        self.assertEqual(len(self.browser.baseline[1]),2)
        self.browser.set_filter('')
        self.harness.request.return_value={'values':{'Health':11}}
        self.browser.refresh();self.browser.changed_only=True
        self.assertEqual(dict(self.browser.rows()),{'Health':11,'Speed':{'$removed':20}})

    def test_monitor_stops_when_hidden_or_object_disappears(self):
        self.browser.request={'op':'inspect','target':{'$object':'/Pawn'}}
        self.browser.result={'values':{'Health':10}}
        self.browser.path=['Health']
        self.browser.toggle_live();self.browser.next_refresh=0
        self.harness.request.side_effect=ValueError('Object identity changed')
        self.assertTrue(self.browser.poll(True))
        self.assertFalse(self.browser.live)
        self.assertEqual(self.browser.result,{})
        self.assertIn('identity',self.browser.monitor_error)
        self.browser.live=True
        self.browser.poll(False)
        self.assertFalse(self.browser.live)

    def test_staged_edit_rejects_changed_value_without_dispatch(self):
        target={'$object':'/Pawn','class':'Pawn','$identity':{'pid':1,'index':2,'serial':3}}
        self.browser.request={'op':'inspect','target':target}
        self.browser.path=['Owner']
        self.harness.request.return_value={'values':{'Owner':None}}
        self.browser.stage_edit(None)
        self.harness.request.return_value={'values':{'Owner':{'$object':'/Other'}}}
        with self.assertRaisesRegex(ValueError,'changed since staging'):self.browser.apply_edit()
        self.assertFalse(any(call.args[0]['op']=='set' for call in self.harness.request.call_args_list))
        self.assertIsNone(self.browser.draft)

    def test_scalar_edits_stage_apply_and_reject_type_mismatch(self):
        self.browser.request={'op':'inspect','target':{'$object':'/Pawn','$identity':{'pid':1,'index':2,'serial':3}}}
        self.browser.path=['Value']
        for before,after in ((1,2),(1.25,2.5),(False,True)):
            self.harness.request.return_value={'values':{'Value':before}}
            self.browser.stage_edit(after)
            self.browser.apply_edit()
            writes=[c.args[0] for c in self.harness.request.call_args_list if c.args[0]['op']=='set']
            self.assertEqual(writes[-1]['expected'],before)
            self.assertEqual(writes[-1]['value'],after)
        self.harness.request.return_value={'values':{'Value':False}}
        with self.assertRaises(ValueError):self.browser.stage_edit(1)

    def test_tools_and_page_cycle_fit_shared_twelve_controls(self):
        frame=self.view.render()
        tools=self.view.activate(frame.revision,2)
        self.assertLessEqual(len(tools.controls),12)
        page2=self.view.activate(tools.revision,4)
        self.assertEqual(page2.page,1)
        page3=self.view.activate(page2.revision,4)
        self.assertEqual(page3.page,2)
        self.assertEqual(self.view.activate(page3.revision,4).page,0)

    def test_monitor_refresh_does_not_reset_tools_page(self):
        self.view.screen='tools'
        self.view.page=2
        self.browser.generation+=1
        self.assertEqual(self.view.render().page,2)

    def test_selected_reference_remains_editable_until_explicit_follow(self):
        reference = {'$object': '/World.Other', 'class': 'Pawn'}
        self.browser.request = {'op': 'inspect', 'target': {'$object': '/World.Pawn'}}
        self.browser.result = {'values': {'Owner': reference}}
        self.browser.select('Owner')
        self.assertEqual(self.browser.path, ['Owner'])
        self.assertEqual(self.browser.request['target']['$object'], '/World.Pawn')
        self.harness.request.return_value = {'values': {}}
        self.browser.follow_reference()
        self.assertEqual(self.browser.request['target'], reference)

    def test_missing_monitored_member_stops_instead_of_expanding_read(self):
        self.browser.request = {'op': 'inspect', 'target': {'$object': '/World.Pawn'}}
        self.browser.result = {'values': {'Health': 1}}
        self.browser.path = ['Health']
        self.browser.toggle_live(); self.browser.next_refresh = 0
        self.harness.request.return_value = {'values': {}}
        self.browser.poll(True)
        self.assertFalse(self.browser.live)
        self.assertIn('disappeared', self.browser.monitor_error)

    def test_apply_passes_staged_expectation_to_native_assignment_request(self):
        target = {'$object': '/Pawn', '$identity': {'pid': 1, 'index': 2, 'serial': 3}}
        self.browser.request = {'op': 'inspect', 'target': target}
        self.browser.path = ['Owner']
        self.harness.request.return_value = {'values': {'Owner': None}}
        self.browser.stage_edit(None)
        self.browser.apply_edit()
        writes = [c.args[0] for c in self.harness.request.call_args_list if c.args[0]['op'] == 'set']
        self.assertEqual(len(writes), 1)
        self.assertIn('expected', writes[0])
        self.assertIsNone(writes[0]['expected'])

    def test_collection_summary_does_not_dump_raw_reference_json(self):
        self.assertEqual(module.summary([{'$object': '/World.Pawn'}]), '1 items: Pawn')

    def test_only_acknowledged_focus_preparation_failure_is_cleaned(self):
        for outcome, code, cleaned in (('returned', 902, True), ('unknown', 902, False), ('returned', 811, False)):
            mod = module.Mod()
            mod.browser = self.browser
            mod.native = Mock(menu=None)
            mod.native.open.side_effect = module.MenuError('rejected', outcome=outcome, native_error=code)
            with self.assertRaises((module.ManagementError, module.MenuError)):
                mod.open()
            self.assertEqual(mod.native.close_menu.called, cleaned)


if __name__ == '__main__':
    unittest.main()
