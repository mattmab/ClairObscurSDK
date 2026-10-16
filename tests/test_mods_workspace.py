import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_management
from test_management_native import FakePanel
from expedition33.management import ManagementError
from expedition33.mods_workspace import ModsWorkspaceView, ModsWorkspaceMenu, ModsWorkspacePanel


class WorkspaceFakePanel(FakePanel):
    def __init__(self, session, **options):
        super().__init__(session, **options)
        self.count = 16
        self.buttons = list(range(16))
        self.labels = [f'label{i}' for i in range(16)]
        self.field_value = ''
    def set_field(self, value): self.field_value = value
    def read_field(self): return self.field_value
    def paint_appearance(self, theme, scale): self.appearance = (theme, scale)


class WorkspaceTests(unittest.TestCase):
    setUp = test_management.ManagementTests.setUp
    tearDown = test_management.ManagementTests.tearDown

    def test_editable_text_setter_is_not_sent_in_textblock_batch(self):
        panel = object.__new__(ModsWorkspacePanel)
        panel.field_value, panel.field = None, 'field'
        queued = []
        panel._paint_queue = queued
        seen = []
        panel._render_call = lambda *a, **kw: seen.append(panel._paint_queue)
        panel.set_field('test')
        self.assertEqual(seen, [None])
        self.assertIs(panel._paint_queue, queued)
        self.assertEqual(panel.field_value, 'test')

    def start(self):
        self.view = ModsWorkspaceView(self.registry)
        self.frame = self.view.render()

    def click(self, label, **values):
        control = next(c for c in self.frame.controls if c.label == label)
        self.frame = self.view.activate(self.frame.revision, control.token, **values)

    def settings(self):
        self.start()
        self.click('Specimen [disabled]')
        self.click('Settings')

    def test_search_filter_empty_page_and_fixed_navigation(self):
        self.start()
        self.assertEqual(len(self.frame.controls), 16)
        self.assertEqual([c.label for c in self.frame.controls[8:12]], ['Back', 'Previous', 'Next', 'Close'])
        self.click('Search', value='missing')
        self.assertFalse(any('Specimen' in c.label for c in self.frame.controls))
        self.click('Clear')
        self.click('Filter: All')
        self.assertEqual(self.view.filter_mode, 'Enabled')
        self.assertFalse(any('Specimen' in c.label for c in self.frame.controls))
        self.click('Filter: Enabled')
        self.assertTrue(any('Specimen' in c.label for c in self.frame.controls))

    def test_edit_validation_draft_cancel_reset_and_persistence(self):
        self.settings()
        self.click('Count: 3')
        self.click('Apply', value='99')
        self.assertIn('Invalid value', self.frame.status)
        self.assertIsNotNone(self.view.editing)
        self.assertEqual(self.registry.option(self.view.selection, 'count'), 3)
        self.click('Apply', value='7')
        self.assertEqual(self.registry.option(self.view.selection, 'count'), 7)
        self.click('Count: 7')
        self.click('Cancel')
        self.assertEqual(self.registry.option(self.view.selection, 'count'), 7)
        self.click('Count: 7')
        self.click('Reset')
        self.assertEqual(self.registry.option(self.view.selection, 'count'), 3)
        self.assertEqual(self.store.get('specimen')['options']['count'], 3)

    def test_boolean_and_choice_keep_exact_registry_types(self):
        self.settings()
        self.click('Toggle: true')
        self.click('Apply', value='false')
        self.assertIs(self.registry.option(self.view.selection, 'toggle'), False)
        self.click('Choice: "a"')
        self.click('Apply', value='"b"')
        self.assertEqual(self.registry.option(self.view.selection, 'choice'), 'b')

    def test_stale_clicks_and_reload_while_editing(self):
        self.settings()
        stale = self.frame
        self.click('Count: 3')
        with self.assertRaises(ManagementError):
            self.view.activate(stale.revision, stale.controls[0].token)
        self.loader.unload('Specimen')
        self.loader.load('Specimen')
        self.frame = self.view.render()
        self.assertIsNone(self.view.editing)
        self.assertEqual(self.view.screen, 'list')

    def test_reload_preserves_enabled_state_and_reselects_new_generation(self):
        self.start()
        self.click('Specimen [disabled]')
        self.click('Enable')
        old = self.view.selection
        self.click('Reload')
        self.assertIn('Reloaded', self.frame.status)
        self.assertNotEqual(self.view.selection, old)
        self.assertTrue(self.registry.view(self.view.selection)['enabled'])

    def test_bulk_requires_concrete_confirmation(self):
        self.start()
        self.click('Bulk actions')
        self.click('Enable all')
        self.assertFalse(self.registry.views()[0]['enabled'])
        self.click('Confirm enable 1 mods')
        self.assertTrue(self.registry.views()[0]['enabled'])
        self.assertIn('Specimen: done', self.frame.status)

    def test_all_keybinds_uses_registry_conflicts_and_remap(self):
        from dataclasses import replace
        from expedition33.management import Keybind
        entry = self.registry._entries['specimen']
        entry.definition = replace(entry.definition, keybinds=(Keybind('test', 'Test key', 'F6', lambda _: None),))
        self.start()
        self.click('All keybinds')
        self.click('Specimen / Test key: F6')
        self.click('Unbind')
        self.assertIsNone(self.registry.view(self.view.selection)['keybinds'][0]['value'])

    def test_native_draft_survives_refresh_and_apply_reads_field(self):
        with patch('expedition33.mods_workspace.ModsWorkspacePanel', WorkspaceFakePanel):
            menu = ModsWorkspaceMenu(None, self.registry)
        menu.open()
        def click(label):
            i = next(i for i, c in enumerate(menu.frame.controls) if c.label == label)
            next(h for h in menu.actions if h.button == i).callback(None)
        click('Specimen [disabled]'); click('Settings'); click('Count: 3')
        menu.panel.field_value = '8'
        menu.refresh()
        self.assertEqual(menu.panel.field_value, '8')
        click('Apply')
        self.assertEqual(self.registry.option(menu.view.selection, 'count'), 8)
        click('Close')
        self.assertEqual(menu.panel.state, 'closed')

    def test_protected_reload_unload_and_disable_are_unavailable(self):
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        entry.definition = replace(entry.definition, protected=True)
        self.loader.enable('Specimen')
        self.start(); self.click('Specimen [enabled]')
        for label in ('Disable', 'Reload', 'Unload'):
            self.assertFalse(next(c for c in self.frame.controls if c.label == label).enabled)
        with self.assertRaises(ManagementError):
            self.registry.reload_current(self.view.selection)

    def test_nonfinite_and_wrong_numeric_type_rejected(self):
        self.settings(); self.click('Count: 3')
        for value in ('NaN', 'Infinity', '3.5', 'true', 'null'):
            self.click('Apply', value=value)
            self.assertIsNotNone(self.view.editing)
            self.assertEqual(self.registry.option(self.view.selection, 'count'), 3)

    def test_bulk_keys_refresh_generation_between_bindings(self):
        from dataclasses import replace
        from expedition33.management import Keybind
        entry = self.registry._entries['specimen']
        entry.definition = replace(entry.definition, keybinds=(
            Keybind('first', 'First', 'F5', lambda _: None),
            Keybind('second', 'Second', 'F6', lambda _: None)))
        self.start(); self.click('Bulk actions'); self.click('Unbind all user-mod keys')
        self.click('Confirm unbind 1 mods')
        self.assertEqual([b['value'] for b in self.registry.views()[0]['keybinds']], [None, None])
        self.click('Back'); self.click('Bulk actions'); self.click('Restore all user-mod key defaults')
        self.click('Confirm reset_keys 1 mods')
        self.assertEqual([b['value'] for b in self.registry.views()[0]['keybinds']], ['F5', 'F6'])
        self.assertTrue((self.store.path.parent / 'ModsMenu/last_bulk_operation.json').is_file())

    def test_bulk_confirmation_does_not_mutate_reloaded_generation(self):
        self.start(); self.click('Bulk actions'); self.click('Enable all')
        self.loader.unload('Specimen'); self.loader.load('Specimen')
        self.click('Confirm enable 1 mods')
        self.assertFalse(self.registry.views()[0]['enabled'])
        self.assertIn('Stale', self.frame.status)

    def test_diagnostic_export_contains_selected_mod_metadata(self):
        import json
        self.start(); self.click('Specimen [disabled]'); self.click('Export diagnostics')
        path = self.store.path.parent / 'ModsMenu/selected_mod_diagnostics.json'
        self.assertEqual(json.loads(path.read_text())['id'], 'specimen')


if __name__ == '__main__':
    unittest.main()
