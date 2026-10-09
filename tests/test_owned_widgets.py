import unittest
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


if __name__ == '__main__':
    unittest.main()
