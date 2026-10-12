import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33 import _ui_batch
from expedition33.management_native import NativeManagementMenu

ROOT = Path(__file__).resolve().parents[1]
from expedition33 import widgets
spec = importlib.util.spec_from_file_location('cinematics_paint_fixture', ROOT / 'mods/Cinematics/mod.py')
cinematics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cinematics)


class SparsePaintTests(unittest.TestCase):
    def menu(self):
        panel = widgets.OwnedMenuPanel.__new__(widgets.OwnedMenuPanel)
        panel.scope = SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(ui_batch_protocol=1)))
        panel._planner = SimpleNamespace(prepare=Mock(side_effect=lambda obj, function, **args: (obj, function, args)))
        panel._function = lambda owner, name: name
        panel._paint_queue = None
        panel.state, panel.uncertain, panel.count = 'built', False, 12
        panel.title, panel.detail = SimpleNamespace(index=1), SimpleNamespace(index=2)
        panel.labels = [SimpleNamespace(index=10 + n) for n in range(12)]
        panel.buttons = [SimpleNamespace(index=30 + n) for n in range(12)]
        panel.button_art = [SimpleNamespace(index=50 + n) for n in range(12)]
        panel.visible, panel.invisible, panel.collapsed = 'visible', 'no_hit', 'collapsed'
        panel._text = {obj.index: 'previous populated menu' for obj in [panel.title, panel.detail] + panel.labels}
        panel._enabled = dict.fromkeys(range(12), True)
        panel._visible = dict.fromkeys(range(12), True)
        registry = SimpleNamespace(_check=lambda: None)
        model = SimpleNamespace(show_all=True, discovery={'state': 'unavailable', 'confirmed': []},
            reason='Current save manager has no loaded save object')
        view = cinematics.BrowserView(registry, model)
        menu = NativeManagementMenu.__new__(NativeManagementMenu)
        menu._presentation_suspended = False
        menu._presentation_dirty = False
        menu.panel, menu.frame = panel, view.render()
        menu.error = menu._logged_detail = None
        return menu

    def test_no_loaded_save_view_flushes53_setters_in_bounded_groups(self):
        menu = self.menu()
        batches = []
        def dispatch(scope, prepared):
            batches.append(tuple(prepared))
            # Exercise unchanged wire count admission as well as real renderer.
            _ui_batch.encode([('multi-button', bytes(2648)) for _ in prepared])
        with patch('expedition33._ui_batch.invoke_setters', side_effect=dispatch):
            menu._paint()
            self.assertEqual([len(batch) for batch in batches], [48, 5])
            self.assertFalse(menu.panel.uncertain)
            self.assertEqual(len(menu.frame.controls), 5)
            self.assertEqual(sum(menu.panel._visible.values()), 5)
            menu._paint()
            self.assertEqual(len(batches), 2, 'Unchanged frame must not dispatch')

    def test_first_group_failure_stops_remaining_and_invalidates_cached_paint(self):
        menu = self.menu()
        with patch('expedition33._ui_batch.invoke_setters', side_effect=RuntimeError('unknown result')) as dispatch:
            with self.assertRaisesRegex(RuntimeError, 'unknown result'):
                menu._paint()
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(len(dispatch.call_args.args[1]), 48)
        self.assertTrue(menu.panel.uncertain)
        self.assertEqual((menu.panel._text, menu.panel._enabled, menu.panel._visible), ({}, {}, {}))
        self.assertIsNone(menu.panel._paint_queue)

    def test_second_group_failure_never_retries_completed_first_group(self):
        menu = self.menu()
        with patch('expedition33._ui_batch.invoke_setters', side_effect=[None, RuntimeError('second failure')]) as dispatch:
            with self.assertRaisesRegex(RuntimeError, 'second failure'):
                menu._paint()
        self.assertEqual([len(call.args[1]) for call in dispatch.call_args_list], [48, 5])
        self.assertTrue(menu.panel.uncertain)


if __name__ == '__main__':
    unittest.main()

