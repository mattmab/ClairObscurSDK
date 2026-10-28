import unittest
from unittest.mock import Mock, patch

from expedition33.cinematic_context_panel import CinematicContextPanel


class CinematicContextPanelTests(unittest.TestCase):
    def test_context_requests_one_control_and_existing_cached_owned_paths(self):
        session = object()
        with patch('expedition33.cinematic_context_panel.OwnedMenuPanel.__init__') as initialize:
            CinematicContextPanel(session)
        initialize.assert_called_once_with(session, controls=1, cached_construction=True,
                                           selected_results=True)
        self.assertTrue(CinematicContextPanel.BATCH_CONSTRUCTION)

    def test_contents_construct_only_the_required_focus_button(self):
        panel = object.__new__(CinematicContextPanel)
        button = object()
        panel._spawn = Mock(return_value=button)
        panel._place = Mock()
        panel.buttons, panel.labels, panel.button_art = [], [], []
        panel._visible, panel._enabled = {}, {}
        panel._build_contents()
        panel._spawn.assert_called_once_with('Button')
        panel._place.assert_called_once_with(button, 0, 0, 1, 1)
        self.assertEqual(panel.buttons, [button])
        self.assertEqual(panel.labels, [])
        self.assertEqual(panel.button_art, [])
        self.assertEqual(panel._enabled, {0:True})

    def test_invisibility_is_set_once_on_the_owned_root_after_construction(self):
        panel = object.__new__(CinematicContextPanel)
        panel.widget = object()
        panel._render_call = Mock()
        with patch('expedition33.cinematic_context_panel.OwnedMenuPanel.build') as build:
            self.assertIs(panel.build(), panel)
        build.assert_called_once()
        panel._render_call.assert_called_once_with(panel.widget, 'Widget', 'SetRenderOpacity', InOpacity=0.)

    def test_unknown_opacity_outcome_is_not_retried_or_hidden(self):
        panel = object.__new__(CinematicContextPanel)
        panel.widget = object()
        panel._render_call = Mock(side_effect=RuntimeError('unknown mutation'))
        with patch('expedition33.cinematic_context_panel.OwnedMenuPanel.build'), \
                self.assertRaisesRegex(RuntimeError, 'unknown mutation'):
            panel.build()
        panel._render_call.assert_called_once()


if __name__ == '__main__':
    unittest.main()
