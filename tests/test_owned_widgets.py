import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33.widgets import OwnedMenuPanel


class OwnedWidgetCleanupTests(unittest.TestCase):
    def panel(self):
        operations = []
        scope = SimpleNamespace(close=lambda: operations.append('release'))
        session = SimpleNamespace(_check=lambda: None, supports_multi_controls=True)
        with patch('expedition33.widgets.SessionScope', return_value=scope):
            panel = OwnedMenuPanel(session, controls=2)
        panel.state = 'open'
        panel.menu = SimpleNamespace(close=lambda: operations.append('native-close') or True)
        panel.assigned = True
        panel.tree, panel.canvas = object(), object()
        panel.children = ['button', 'label']
        panel._class = lambda name: name
        panel._root = lambda: None
        scope.assign_object = lambda *a, **kw: operations.append('restore-root')
        panel._call = lambda child, *a, **kw: operations.append('remove-' + child)
        return panel, operations

    def test_close_native_before_tree_before_lease_release(self):
        panel, operations = self.panel()
        self.assertTrue(panel.close())
        self.assertEqual(operations, ['native-close', 'restore-root', 'remove-label', 'remove-button', 'release'])
        self.assertTrue(panel.close())
        self.assertEqual(len(operations), 5)

    def test_deferred_native_close_preserves_tree_and_scope(self):
        panel, operations = self.panel()
        panel.menu.close = lambda: False
        self.assertFalse(panel.close())
        self.assertEqual(operations, [])
        self.assertTrue(panel.assigned)
        self.assertEqual(panel.children, ['button', 'label'])

    def test_unknown_mutation_never_retries_or_releases_tree(self):
        panel, operations = self.panel()
        mutate = Mock(side_effect=RuntimeError('lost acknowledgement'))
        with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
            panel._mutate(mutate)
        with self.assertRaisesRegex(RuntimeError, 'no retry'):
            panel._mutate(mutate)
        self.assertEqual(mutate.call_count, 1)
        with self.assertRaisesRegex(RuntimeError, 'preserve owner'):
            panel.close()
        self.assertEqual(operations, ['native-close'])
        self.assertTrue(panel.assigned)

    def test_visibility_uses_separate_label_input_policy_and_caches_success(self):
        panel, _ = self.panel()
        panel.buttons, panel.labels = ['button'], ['label']
        panel.visible, panel.invisible, panel.collapsed = 'visible', 'no-hit', 'collapsed'
        panel._function = lambda *args: args
        calls = []
        panel.scope.invoke_retained = lambda obj, fn, **kw: (calls.append((obj, kw['InVisibility'])) or nullcontext())
        panel.set_visible(0, False)
        panel.set_visible(0, False)
        panel.set_visible(0, True)
        self.assertEqual(calls, [('button', 'collapsed'), ('label', 'collapsed'),
                                 ('button', 'visible'), ('label', 'no-hit')])

    def test_cached_repaint_uses_scope_planner_and_never_falls_back(self):
        panel, _ = self.panel()
        panel.state = 'built'
        panel.buttons, panel.labels = ['button'], ['label']
        panel.visible, panel.invisible, panel.collapsed = 'visible', 'no-hit', 'collapsed'
        panel._function = lambda *args: args
        prepared = SimpleNamespace(invoke=Mock(side_effect=[nullcontext(), RuntimeError('lost reply')]))
        planner = SimpleNamespace(prepare=Mock(return_value=prepared), close=Mock())
        panel.scope.invocation_planner = Mock(return_value=planner)
        panel.scope.invoke_retained = Mock(side_effect=AssertionError('fallback forbidden'))
        panel.enable_cached_planning()
        panel.enable_cached_planning()
        panel.scope.invocation_planner.assert_called_once_with()
        with self.assertRaisesRegex(RuntimeError, 'lost reply'): panel.set_visible(0, False)
        self.assertTrue(panel.uncertain)
        self.assertNotIn(0, panel._visible)
        with self.assertRaisesRegex(RuntimeError, 'no retry'): panel.set_visible(0, False)
        self.assertEqual(prepared.invoke.call_count, 2)
        panel.scope.invoke_retained.assert_not_called()

    def test_planner_cleanup_follows_native_cleanup(self):
        panel, operations = self.panel()
        panel._planner = SimpleNamespace(close=lambda: operations.append('planner-close'))
        self.assertTrue(panel.close())
        self.assertEqual(operations[-2:], ['planner-close', 'release'])
        self.assertIsNone(panel._planner)

    def test_partial_visibility_failure_preserves_unknown_outcome(self):
        panel, _ = self.panel()
        panel.buttons, panel.labels = ['button'], ['label']
        panel.visible, panel.invisible, panel.collapsed = 'visible', 'no-hit', 'collapsed'
        panel._function = lambda *args: args
        panel.scope.invoke_retained = Mock(side_effect=[nullcontext(), RuntimeError('lost reply')])
        with self.assertRaisesRegex(RuntimeError, 'lost reply'): panel.set_visible(0, False)
        self.assertNotIn(0, panel._visible)
        with self.assertRaisesRegex(RuntimeError, 'no retry'): panel.set_visible(0, False)
        self.assertEqual(panel.scope.invoke_retained.call_count, 2)


if __name__ == '__main__':
    unittest.main()
