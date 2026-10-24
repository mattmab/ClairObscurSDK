import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33.pause_menu import PauseMenuEntry
from expedition33 import RuntimeQueryError


class PauseBuildTests(unittest.TestCase):
    def test_gc_discovery_race_retries_only_before_any_mutation(self):
        for state, expected in (('new', 'new'), ('building', 'failed')):
            entry = PauseMenuEntry(NS(_session=NS(_transport=NS(
                pause_attachment_protocol=2, trace_renew_protocol=1))), NS())
            def fail():
                entry.state = state
                raise RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')
            entry.install = fail
            entry.poll()
            self.assertEqual(entry.state, expected)

    def entry(self, version=2):
        session = NS(_transport=NS(ui_batch_protocol=1, layout_batch_protocol=version))
        entry = PauseMenuEntry(NS(_session=session), NS())
        entry.scope = NS(_session=session)
        entry.planner = NS(_catalog='catalog', prepare=Mock(side_effect=lambda *a, **kw: (a, kw)),
                           adopt_observations=Mock())
        entry.fn = lambda owner, name: (owner, name)
        entry.cls = lambda name: name
        entry.call = Mock()
        return entry

    def test_detached_button_does_not_arm_world_specific_cleanup(self):
        entry=self.entry();entry.library='library';entry.player='player'
        entry.create=Mock(side_effect=('button','label','frame','slot'))
        entry.reference=Mock(side_effect=('tree','content'))
        entry.layout=Mock();entry._arm_button=Mock()
        entry._build_button('gameplay','style',(300.,60.),arm=False)
        entry._arm_button.assert_not_called()
        self.assertEqual(entry._label_widget,'label')
        self.assertEqual(entry.button,'button')

    def test_reference_projects_and_preserves_validated_metadata(self):
        entry = self.entry()
        with patch('expedition33.pause_menu.read_object_reference', return_value=('tree', 'fresh')) as read:
            self.assertEqual(entry.reference('widget', 'UserWidget', 'WidgetTree'), 'tree')
        read.assert_called_once_with('catalog', 'widget', 'UserWidget', 'WidgetTree', project=True)
        entry.planner.adopt_observations.assert_called_once_with('fresh')

    def test_layout_prepares_after_last_creation_and_obeys_native_limit(self):
        entry = self.entry()
        for i in range(49):
            entry.layout(i, 'GridSlot', 'SetPadding', InPadding={})
        entry.planner.prepare.assert_not_called()
        with patch('expedition33._ui_batch.invoke_setters') as invoke:
            entry.flush_layout()
        self.assertEqual([len(c.args[1]) for c in invoke.call_args_list], [48, 1])
        self.assertEqual(entry._layout_calls, [])
        entry.call.assert_not_called()

    def test_failure_stops_later_groups_and_cannot_replay(self):
        entry = self.entry()
        for i in range(49):
            entry.layout(i, 'GridSlot', 'SetPadding', InPadding={})
        with patch('expedition33._ui_batch.invoke_setters', side_effect=RuntimeError('unknown')) as invoke:
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                entry.flush_layout()
            entry.flush_layout()
        self.assertEqual(invoke.call_count, 1)
        entry.call.assert_not_called()

    def test_older_protocol_uses_only_supported_batch_operations(self):
        entry = self.entry(version=1)
        entry.layout('button', 'CommonButtonBase', 'SetMinDimensions', InMinWidth=1, InMinHeight=2)
        entry.call.assert_called_once()
        self.assertEqual(entry._layout_calls, [])

    def test_old_layout_protocol_does_not_batch_grid_slot_alignment(self):
        entry = self.entry(version=1)
        entry.layout('slot', 'GridSlot', 'SetHorizontalAlignment', InHorizontalAlignment=0)
        entry.call.assert_called_once()
        self.assertEqual(entry._layout_calls, [])


if __name__ == '__main__':
    unittest.main()
