import importlib.util
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.cinematics import presentation

from expedition33 import management_native as management


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.widget = SimpleNamespace(index=10, serial=4, address=0x20000)
        self.cls = SimpleNamespace(index=20)
        self.fn = SimpleNamespace(index=21, outer_index=20, name='SetRenderOpacity', class_name='Function')
        self.catalog = SimpleNamespace(objects=[self.fn], by_index={20: self.cls}, find_class=lambda _: self.cls)
        self.catalog.with_observations = lambda _: self.catalog
        self.opacity_calls = []
        self.planner = SimpleNamespace(close=Mock(), prepare=Mock(side_effect=self.prepared))
        self.scope = SimpleNamespace(pid=17, _check=Mock(), invocation_planner=Mock(return_value=self.planner))
        self.panel = SimpleNamespace(state='open', uncertain=False, scope=self.scope, widget=self.widget,
                                     hide=Mock(), close=Mock())
        self.panel._mutate = lambda method, *args: method(*args)
        self.menu = SimpleNamespace(panel=self.panel, _presentation_suspended=False, _restore_presentation_frame=Mock())
        self.guard = presentation.MenuPresentation(self.menu)
        self.values = SimpleNamespace(types={(20, 'RenderOpacity'): 'FloatProperty'},
            values={(20, 'RenderOpacity'): .75}, errors={}, truncated=set())
        for p in (patch.object(presentation, 'capture_matching', return_value=self.catalog),
                  patch.object(presentation, 'capture_selected', return_value=object()),
                  patch.object(presentation, 'read_values', return_value=self.values)):
            p.start(); self.addCleanup(p.stop)

    def prepared(self, widget, function, **arguments):
        opacity = arguments['InOpacity']
        return SimpleNamespace(invoke=lambda: self.opacity_calls.append(opacity) or nullcontext())

    def test_opacity_restores_exact_observed_value_without_changing_menu_owner(self):
        self.guard.prepare().suspend()
        self.assertEqual(self.opacity_calls, [0.])
        self.assertTrue(self.menu._presentation_suspended)
        self.assertEqual(self.panel.state, 'open')
        self.guard.restore()
        self.assertEqual(self.opacity_calls, [0., .75])
        self.assertFalse(self.menu._presentation_suspended)
        self.assertEqual(self.panel.state, 'open')
        self.panel.hide.assert_not_called()
        self.panel.close.assert_not_called()
        self.guard.restore()
        self.assertEqual(self.opacity_calls, [0., .75])

    def test_unknown_suspend_keeps_input_gate_and_never_retries_mutation(self):
        self.guard.prepare()
        self.panel._mutate = Mock(side_effect=RuntimeError('lost acknowledgement'))
        with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
            self.guard.suspend()
        self.assertTrue(self.menu._presentation_suspended)
        with self.assertRaisesRegex(RuntimeError, 'Unknown visual'):
            self.guard.restore()
        self.panel._mutate.assert_called_once()

    def test_closed_panel_needs_no_engine_restore_call(self):
        self.guard.prepare().suspend()
        self.panel.state = 'closed'
        self.guard.restore()
        self.assertEqual(self.opacity_calls, [0.])
        self.assertFalse(self.menu._presentation_suspended)

    def test_detached_reusable_panel_is_restored_and_changed_owner_rejected(self):
        self.guard.prepare().suspend()
        self.panel.state = 'built'
        self.guard.restore()
        self.assertEqual(self.opacity_calls, [0., .75])
        self.menu.panel = object()
        with self.assertRaises(RuntimeError):
            self.guard.suspend()

    def test_missing_or_undecoded_opacity_fails_before_mutation(self):
        self.values.errors[(20, 'RenderOpacity')] = 'unavailable'
        with self.assertRaisesRegex(RuntimeError, 'not verified'):
            self.guard.prepare()
        self.assertEqual(self.opacity_calls, [])
        self.assertFalse(self.menu._presentation_suspended)

    def test_invisible_controls_do_not_dispatch_actions_but_bindings_remain(self):
        menu = management.NativeManagementMenu.__new__(management.NativeManagementMenu)
        control = SimpleNamespace(enabled=True, editor=None, token=7)
        frame = SimpleNamespace(controls=[control], revision=1)
        bindings = []
        def bind(rows):
            bindings.extend(rows)
            return [object()]
        menu.panel = SimpleNamespace(buttons=[object()], menu=SimpleNamespace(bind_controls=bind))
        menu.frame, menu.actions = frame, []
        menu._presentation_suspended = True
        menu._accept_input = True
        menu.submit = Mock()
        menu._bind()
        bindings[0][1](None)
        menu.submit.assert_not_called()
        self.assertEqual(len(menu.actions), 1)
        menu._presentation_suspended = False
        bindings[0][1](None)
        menu.submit.assert_called_once_with(1, 7)

