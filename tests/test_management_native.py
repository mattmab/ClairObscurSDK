import unittest
from contextlib import nullcontext
from unittest.mock import patch, Mock
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
        self.menu = None
        self._binding_menu = SimpleNamespace(bind_control=self.bind,
            bind_controls=lambda bindings: [self.bind(*b) for b in bindings],
            remove_controls=lambda controls: all(c.remove() for c in controls))
        self.defer = False
    def build(self): self.operations.append('build'); self.state = 'built'
    def enable_cached_planning(self): self.operations.append('planner')
    def prime_menu_plan(self): self.operations.append('prime')
    def paint_batch(self): return nullcontext()
    def open(self): self.operations.append('open'); self.state = 'open'; self.menu=self._binding_menu
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
        self.menu = None
        return True
    def hide(self):
        if self.defer: return False
        for handle in self.handles: handle.active = False
        self.operations.append('hide')
        self.state = 'built'
        self.menu = None
        return True


class NativeManagementTests(unittest.TestCase):
    setUp = test_management.ManagementTests.setUp
    tearDown = test_management.ManagementTests.tearDown

    def start(self):
        with patch('expedition33.management_native.OwnedMenuPanel', FakePanel):
            self.menu = NativeManagementMenu(None, self.registry)
        self.menu.open()

    def test_detached_refresh_rejects_retained_active_callbacks(self):
        self.start()
        self.menu.panel.state='built';self.menu.panel.menu=None
        with patch.object(self.menu,'_paint') as paint:
            with self.assertRaisesRegex(ManagementError,'acknowledged native detach'):
                self.menu.refresh_detached()
        paint.assert_not_called()
        # Preserve active owners for the normal cleanup path.
        self.assertTrue(any(action.active for action in self.menu.actions))

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

    def test_owned_tree_close_skips_per_child_fallback_after_ack(self):
        self.start()
        self.menu.panel.close_owned_tree = Mock(return_value=True)
        self.menu.panel.close = Mock(side_effect=AssertionError('per-child close fallback'))
        self.assertTrue(self.menu.close())
        self.menu.panel.close_owned_tree.assert_called_once()
        self.menu.panel.close.assert_not_called()
        self.assertFalse(self.menu.actions)
        self.assertFalse(self.menu._accept_input)

    def test_pending_owned_tree_close_keeps_handles_and_does_not_fallback(self):
        self.start()
        actions = list(self.menu.actions)
        self.menu.panel.close_owned_tree = Mock(side_effect=[False, True])
        self.menu.panel.close = Mock(side_effect=AssertionError('fallback must not retry'))
        self.assertFalse(self.menu.close())
        self.assertEqual(self.menu.actions, actions)
        self.assertFalse(self.menu._accept_input)
        self.assertTrue(self.menu.close())
        self.assertFalse(self.menu.actions)
        self.menu.panel.close.assert_not_called()
        self.assertEqual(self.menu.panel.close_owned_tree.call_count, 2)

    def test_unknown_owned_tree_close_retains_owner_without_fallback(self):
        self.start()
        actions = list(self.menu.actions)
        self.menu.panel.close_owned_tree = Mock(side_effect=RuntimeError('unknown root cleanup'))
        self.menu.panel.close = Mock(side_effect=AssertionError('unknown fallback'))
        with self.assertRaisesRegex(RuntimeError, 'unknown root cleanup'):
            self.menu.close()
        self.assertEqual(self.menu.actions, actions)
        self.assertFalse(self.menu._accept_input)
        self.menu.panel.close_owned_tree.assert_called_once()
        self.menu.panel.close.assert_not_called()

    def test_noncallable_owned_tree_contract_uses_legacy_close(self):
        self.start()
        self.menu.panel.close_owned_tree = None
        self.assertTrue(self.menu.close())
        self.assertEqual(self.menu.panel.state, 'closed')
        self.assertIn('close', self.menu.panel.operations)

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
