import unittest
from unittest.mock import patch
from types import SimpleNamespace

import test_management
from expedition33.management import ManagementError
from expedition33.management_native import NativeManagementMenu, display_line, display_detail


class FakePanel:
    def __init__(self, session, *, cached_construction=False, selected_results=False):
        self.cached_construction = cached_construction
        self.selected_results = selected_results
        self.state = "new"
        self.count = 12
        self.title, self.detail = 'title', 'detail'
        self.buttons = list(range(12))
        self.labels = [f'label{i}' for i in range(12)]
        self.text, self.enabled, self.handles, self.operations = {}, {}, [], []
        self.visible = {}
        self.menu = SimpleNamespace(bind_control=self.bind)
        self.defer = False
    def build(self): self.operations.append('build'); self.state = 'built'
    def enable_cached_planning(self): self.operations.append('planner')
    def open(self): self.operations.append('open'); self.state = 'open'
    def set_text(self, label, text): self.text[label] = text
    def set_enabled(self, index, enabled): self.enabled[index] = enabled
    def set_visible(self, index, visible): self.visible[index] = visible
    def bind(self, button, callback):
        handle = SimpleNamespace(button=button, callback=callback, active=True)
        def remove():
            handle.active = False
            self.operations.append('remove')
            return not self.defer
        handle.remove = remove
        self.handles.append(handle)
        self.operations.append('bind')
        return handle
    def close(self):
        self.operations.append('close')
        if self.defer: return False
        for handle in self.handles: handle.active = False
        self.state = "closed"
        return True


class NativeManagementTests(unittest.TestCase):
    setUp = test_management.ManagementTests.setUp
    tearDown = test_management.ManagementTests.tearDown

    def start(self):
        with patch('expedition33.management_native.OwnedMenuPanel', FakePanel):
            self.menu = NativeManagementMenu(None, self.registry)
        self.menu.open()

    def click(self, label):
        control = next(c for c in self.menu.frame.controls if c.label == label)
        handle = next(h for h in self.menu.actions if h.button == control.token)
        handle.callback(None)

    def test_explicit_planning_options_reach_panel_before_attachment(self):
        with patch('expedition33.management_native.OwnedMenuPanel', FakePanel):
            menu = NativeManagementMenu(None, self.registry, cached_planning=True,
                                        cached_construction=True, selected_results=True)
        menu.open()
        self.assertTrue(menu.panel.cached_construction)
        self.assertTrue(menu.panel.selected_results)
        self.assertEqual(menu.panel.operations[:3], ['build', 'planner', 'open'])
        menu.close()

    def test_click_navigation_updates_native_labels_and_shared_registry(self):
        self.start()
        self.assertEqual(self.menu.panel.text['label0'], 'Specimen [disabled]')
        self.assertFalse(self.menu.panel.visible[11])
        stale = self.menu.actions[0]
        self.click('Specimen [disabled]')
        self.assertFalse(stale.active)
        with self.assertRaises(ManagementError): stale.callback(None)
        self.click('Enable')
        self.click('Settings')
        self.click('Toggle: true')
        self.assertFalse(self.registry.option(self.registry.select('specimen'), 'toggle'))
        self.click('Choice: "a"')
        self.assertEqual(self.registry.option(self.registry.select('specimen'), 'choice'), 'b')
        self.click('Back')
        self.click('Actions')
        self.click('Read current value')
        self.assertIn('Result: 3', self.menu.panel.text['detail'])
        self.click('Close')
        self.assertTrue(self.menu.frame.closed)
        self.assertFalse(any(h.active for h in self.menu.panel.handles))

    def test_pending_editor_does_not_change_value_and_refresh_reflects_console_edit(self):
        self.start()
        self.click('Specimen [disabled]')
        self.click('Settings')
        self.click('Count: 3')
        self.assertIn('editor pending', self.menu.panel.text['detail'])
        self.registry.set_option(self.registry.select('specimen'), 'count', 8)
        self.menu.refresh()
        self.assertEqual(self.menu.panel.text['label0'], 'Count: 8')
        self.assertEqual(len(self.menu.actions), sum(c.enabled for c in self.menu.frame.controls))

    def test_deferred_removal_prevents_rebinding_or_repaint(self):
        self.start()
        bindings = len(self.menu.panel.handles)
        text = dict(self.menu.panel.text)
        self.menu.panel.defer = True
        with self.assertRaisesRegex(RuntimeError, 'deferred'): self.menu.refresh()
        with self.assertRaisesRegex(ManagementError, 'revoked'):
            self.menu.actions[-1].callback(None)
        self.assertEqual(len(self.menu.panel.handles), bindings)
        self.assertEqual(self.menu.panel.text, text)
        self.assertFalse(self.menu.close())
        self.menu.panel.defer = False
        self.assertTrue(self.menu.close())

    def test_long_text_has_bounded_lines_and_does_not_change_registry(self):
        self.assertEqual(display_line('one\ntwo', 20), 'one two')
        self.assertEqual(len(display_line('x' * 100, 48)), 48)
        detail = display_detail('X' * 2000)
        self.assertLessEqual(len(detail.splitlines()), 18)
        self.assertTrue(all(len(line) <= 42 for line in detail.splitlines()))
        self.assertIn('SDK log', detail)
        self.start()
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        description = 'Long description ' * 200
        entry.definition = replace(entry.definition, description=description)
        self.click('Specimen [disabled]')
        self.assertEqual(self.registry.view(self.registry.select('specimen'))['description'], description)
        self.assertLessEqual(len(self.menu.panel.text['detail'].splitlines()), 18)


if __name__ == '__main__':
    unittest.main()
