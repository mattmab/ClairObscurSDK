import unittest
from expedition33.widgets import display_text
from expedition33._text_wire import encode_units

class DisplayTextTests(unittest.TestCase):
    def test_native_text_limit_preserves_short_labels_and_marks_clipping(self):
        smile=chr(0x1f600)
        for value in ('x'*4095,smile*2047+'x','ordinary label',''):
            self.assertEqual(display_text(value),value)
        for value in ('x'*4096,smile*4096):
            shown=display_text(value)
            self.assertTrue(shown.endswith('[Display clipped]'))
            self.assertLessEqual(len(encode_units(shown)),8192)
            with self.assertRaises(ValueError):encode_units(value)

    def test_render_guard_applies_only_to_display_text_not_editable_values(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock
        from expedition33.widgets import OwnedMenuPanel
        panel=OwnedMenuPanel.__new__(OwnedMenuPanel)
        panel.latency=N(count=Mock(),measure=lambda *args:None)
        panel._function=lambda *args:args
        panel._planner=N(prepare=Mock(return_value=object()))
        panel._paint_queue=[]
        # Exercise the setter body without requiring a live runtime timer.
        fn=OwnedMenuPanel._render_call.__wrapped__
        text='x'*5000
        fn(panel,object(),'TextBlock','SetText',InText=text)
        shown=panel._planner.prepare.call_args.kwargs['InText']
        self.assertTrue(shown.endswith('[Display clipped]'))
        fn(panel,object(),'EditableText','SetText',InText=text)
        self.assertEqual(panel._planner.prepare.call_args.kwargs['InText'],text)
