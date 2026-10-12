import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33.widgets import OwnedMenuPanel


class OwnedWidgetCleanupTests(unittest.TestCase):
    def test_rejected_prepare_allows_cleanup_but_unknown_remains_latched(self):
        from expedition33.menu import MenuError
        for outcome, code, uncertain in [('returned', 811, False), ('unknown', 814, True)]:
            panel, _ = self.panel()
            panel.state = 'built'
            panel.widget, panel.buttons, panel.player = object(), [object()], object()
            panel.scope.prepare_menu = Mock(side_effect=MenuError('rejected', outcome=outcome, native_error=code))
            with self.assertRaises(MenuError):
                panel.open()
            self.assertEqual(panel.uncertain, uncertain)

    def test_layout_queue_prepares_after_creation_and_stops_after_failed_group(self):
        panel, _ = self.panel()
        panel.state = 'building'
        panel._layout_queue = []
        panel._planner = SimpleNamespace(prepare=Mock(side_effect=lambda *a, **kw: (a, kw)))
        panel._function = lambda owner, name: (owner, name)
        for index in range(55):
            OwnedMenuPanel._call(panel, index, 'CanvasPanelSlot', 'SetSize', InSize={'X': 3., 'Y': 4.})
        panel._planner.prepare.assert_not_called()
        with patch('expedition33._ui_batch.invoke_setters', side_effect=RuntimeError('batch failed')) as invoke:
            with self.assertRaisesRegex(RuntimeError, 'batch failed'):
                panel._flush_layout()
        self.assertEqual(panel._planner.prepare.call_count, 48)
        self.assertEqual(len(invoke.call_args.args[1]), 48)
        self.assertTrue(panel.uncertain)
        self.assertIsNone(panel._layout_queue)

    def test_selected_root_read_has_no_full_scan_or_stale_fallback(self):
        panel, _ = self.panel()
        panel._selected_results = True
        panel.scope.pid = 10
        panel.tree = SimpleNamespace(index=11, serial=12, address=0x10000)
        panel.canvas = SimpleNamespace(index=21, serial=22, address=0x20000)
        panel._class = lambda _: SimpleNamespace(index=31)
        catalog = SimpleNamespace(resolve=lambda obj: obj)
        values = SimpleNamespace(values={(31, 'RootWidget'): panel.canvas})
        with patch('expedition33.widgets.capture', side_effect=AssertionError('full scan')), \
                patch('expedition33.widgets.capture_selected', return_value=catalog) as selected, \
                patch('expedition33.widgets.read_values', return_value=values):
            self.assertIs(OwnedMenuPanel._root(panel), panel.canvas)
            selected.assert_called_once_with(10, ((11, 12, 0x10000), (21, 22, 0x20000)))
            selected.side_effect = RuntimeError('identity changed')
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                OwnedMenuPanel._root(panel)

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

    def test_hide_revokes_native_ownership_but_keeps_tree_until_disposal(self):
        panel, operations = self.panel()
        self.assertTrue(panel.hide())
        self.assertEqual(operations, ['native-close'])
        self.assertEqual(panel.state, 'built')
        self.assertTrue(panel.assigned)
        self.assertIsNone(panel.menu)
        self.assertTrue(panel.close())
        self.assertEqual(operations[-1], 'release')

    def test_selected_teardown_does_not_enumerate_the_world(self):
        panel, operations = self.panel()
        panel._selected_results = True
        panel._planner = SimpleNamespace(_catalog=None, refresh=Mock(side_effect=AssertionError('full scan')),
            close=lambda: operations.append('planner-close'))
        panel._render_call = lambda child, *a: operations.append('remove-' + child)
        self.assertTrue(panel.close())
        panel.scope.close = Mock(side_effect=AssertionError('second release'))
        self.assertTrue(panel.close())
        self.assertEqual(operations, ['native-close', 'restore-root', 'remove-label',
                                     'remove-button', 'planner-close', 'release'])

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

    def test_construction_uses_result_catalog_and_keeps_scalar_result_scoped(self):
        panel, _ = self.panel()
        panel.state = 'building'
        panel._function = lambda *args: args
        prepared = SimpleNamespace(invoke=Mock(return_value=nullcontext()))
        planner = SimpleNamespace(prepare=Mock(return_value=prepared))
        panel._planner = planner
        # Restore the actual method hidden by the cleanup fixture.
        OwnedMenuPanel._call(panel, 'slot', 'CanvasPanelSlot', 'SetSize', InSize={'X':10., 'Y':20.})
        planner.prepare.assert_called_once_with('slot', ('CanvasPanelSlot', 'SetSize'), InSize={'X':10., 'Y':20.})
        prepared.invoke.assert_called_once_with(refresh_from_result=True)
        self.assertFalse(panel.uncertain)

    def test_failed_construction_retains_unknown_state_without_fallback(self):
        panel, _ = self.panel()
        panel.state = 'building'
        prepared = SimpleNamespace(invoke=Mock(side_effect=RuntimeError('lost acknowledgement')))
        panel._planner = SimpleNamespace(prepare=Mock(return_value=prepared))
        panel.scope.invoke_retained = Mock(side_effect=AssertionError('fallback forbidden'))
        with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
            panel._construction_call('target', 'function')
        with self.assertRaisesRegex(RuntimeError, 'no retry'):
            panel._construction_call('target', 'function')
        self.assertTrue(panel.uncertain)
        self.assertEqual(prepared.invoke.call_count, 1)
        panel.scope.invoke_retained.assert_not_called()

    def test_planner_cleanup_follows_native_cleanup(self):
        panel, operations = self.panel()
        panel._planner = SimpleNamespace(_catalog=None, refresh=lambda: operations.append('refresh'),
            close=lambda: operations.append('planner-close'))
        panel._render_call = lambda child, *a: operations.append('remove-' + child)
        self.assertTrue(panel.close())
        self.assertEqual(operations[:5], ['native-close', 'restore-root', 'refresh',
                                         'remove-label', 'remove-button'])
        self.assertEqual(operations[-2:], ['planner-close', 'release'])
        self.assertIsNone(panel._planner)

    def test_cached_cleanup_refresh_failure_preserves_children_and_leases(self):
        panel, operations = self.panel()
        panel._planner = SimpleNamespace(_catalog=None, refresh=Mock(side_effect=RuntimeError('scan failed')),
                                         close=Mock())
        with self.assertRaisesRegex(RuntimeError, 'scan failed'): panel.close()
        self.assertEqual(operations, ['native-close', 'restore-root'])
        self.assertEqual(panel.children, ['button', 'label'])
        self.assertFalse(panel.uncertain)  # No child mutation was dispatched.
        panel._planner.close.assert_not_called()

    def test_cached_cleanup_removes_each_child_through_validated_prepared_calls(self):
        panel, operations = self.panel()
        panel._function = lambda *args: args
        prepared = SimpleNamespace(invoke=Mock(side_effect=lambda: nullcontext()))
        planner = SimpleNamespace(_catalog=None, refresh=Mock(), prepare=Mock(return_value=prepared), close=Mock())
        panel._planner = planner
        panel.scope.invoke = Mock(side_effect=AssertionError('uncached fallback forbidden'))
        self.assertTrue(panel.close())
        planner.refresh.assert_called_once_with()
        self.assertEqual([call.args for call in planner.prepare.call_args_list],
            [('label', ('Widget', 'RemoveFromParent')), ('button', ('Widget', 'RemoveFromParent'))])
        self.assertEqual(prepared.invoke.call_count, 2)
        panel.scope.invoke.assert_not_called()
        self.assertEqual(panel.children, [])
        self.assertFalse(panel.uncertain)
        self.assertEqual(operations[-1], 'release')

    def test_cached_cleanup_unknown_reply_keeps_owner_and_does_not_retry(self):
        panel, operations = self.panel()
        panel._function = lambda *args: args
        prepared = SimpleNamespace(invoke=Mock(side_effect=RuntimeError('lost reply')))
        panel._planner = SimpleNamespace(_catalog=None, refresh=Mock(), prepare=Mock(return_value=prepared), close=Mock())
        with self.assertRaisesRegex(RuntimeError, 'lost reply'): panel.close()
        self.assertEqual(panel.children, ['button', 'label'])
        self.assertTrue(panel.uncertain)
        with self.assertRaisesRegex(RuntimeError, 'preserve owner'): panel.close()
        prepared.invoke.assert_called_once_with()
        panel._planner.refresh.assert_called_once_with()
        panel._planner.close.assert_not_called()
        self.assertNotIn('release', operations)

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
