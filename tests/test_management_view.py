import unittest
from dataclasses import replace

from expedition33.management import Action, ManagementError, ModDefinition
from expedition33.management_view import ManagementView
import test_management


class ManagementViewTests(unittest.TestCase):
    setUp = test_management.ManagementTests.setUp
    tearDown = test_management.ManagementTests.tearDown

    def click(self, frame, label, **values):
        control = next(c for c in frame.controls if c.label == label)
        return self.view.activate(frame.revision, control.token, **values)

    def details(self):
        self.view = ManagementView(self.registry)
        return self.click(self.view.render(), 'Specimen [disabled]')

    def test_shared_settings_enable_action_and_persistence(self):
        frame = self.details()
        frame = self.click(frame, 'Enable')
        frame = self.click(frame, 'Settings')
        editor = next(c.editor for c in frame.controls if c.label == 'Count: 3')
        self.assertEqual((editor.kind, editor.minimum, editor.maximum, editor.default), ('int', 0, 10, 3))
        choice = next(c.editor for c in frame.controls if c.label.startswith('Choice:'))
        self.assertEqual(choice.choices, ('a', 'b'))
        frame = self.click(frame, 'Count: 3', value=8)
        self.assertEqual(self.registry.option(self.registry.select('specimen'), 'count'), 8)
        self.assertEqual(self.store.get('specimen')['options']['count'], 8)
        frame = self.click(frame, 'Back')
        frame = self.click(frame, 'Actions')
        frame = self.click(frame, 'Read current value')
        self.assertEqual(frame.status, 'Result: 8')
        frame = self.click(frame, 'Fail safely')
        self.assertIn('SystemExit: contained', frame.status)
        self.assertFalse(frame.closed)

    def test_old_frame_callback_cannot_retarget_after_refresh(self):
        frame = self.details()
        callback = self.view.callback(frame, next(c for c in frame.controls if c.label == 'Enable'))
        self.view.render()
        with self.assertRaisesRegex(ManagementError, 'Stale menu'):
            callback()
        self.assertFalse(self.registry.view(self.registry.select('specimen'))['enabled'])

    def test_reload_between_render_and_click_rejects_old_selection(self):
        frame = self.details()
        self.loader.unload('Specimen')
        self.loader.load('Specimen')
        frame = self.click(frame, 'Enable')
        self.assertIn('Stale mod selection', frame.status)
        self.assertEqual(frame.title, 'SDK Mods')
        self.assertFalse(self.registry.view(self.registry.select('specimen'))['enabled'])

    def test_paging_search_and_close_revoke_controls(self):
        for i in range(18):
            self.registry.register('Other' + str(i), ModDefinition('other' + str(i), 'Other ' + str(i)))
        self.view = ManagementView(self.registry)
        frame = self.view.render()
        self.assertEqual(len(frame.controls), 12)
        self.assertEqual(frame.pages, 3)
        frame = self.click(frame, 'Next')
        self.assertEqual(frame.page, 1)
        frame = self.view.search('specimen')
        self.assertEqual(frame.pages, 1)
        self.assertEqual(frame.controls[0].label, 'Specimen [disabled]')
        frame = self.click(frame, 'Close')
        self.assertTrue(frame.closed)
        with self.assertRaisesRegex(ManagementError, 'closed'): self.view.render()
        for i in range(18): self.registry.unregister('Other' + str(i))

    def test_bad_value_is_shown_and_default_reset_uses_registry(self):
        frame = self.click(self.details(), 'Settings')
        frame = self.click(frame, 'Count: 3', value=1000)
        self.assertIn('Invalid value', frame.status)
        frame = self.click(frame, 'Count: 3', value=9)
        frame = self.click(frame, 'Count: 9', reset=True)
        self.assertEqual(self.registry.option(self.registry.select('specimen'), 'count'), 3)

    def test_disabled_protected_and_callback_arguments(self):
        frame = self.details()
        frame = self.click(frame, 'Actions')
        control = next(c for c in frame.controls if c.label == 'Read current value')
        self.assertFalse(control.enabled)
        with self.assertRaisesRegex(ManagementError, 'unavailable'):
            self.view.activate(frame.revision, control.token)
        self.loader.enable('Specimen')
        entry = self.registry._entries['specimen']
        seen = []
        entry.definition = replace(entry.definition, protected=True,
            actions=(Action('capture', 'Capture', lambda value: seen.append(value)),))
        frame = self.view.render()  # Reloaded generation returns to the list.
        frame = self.click(frame, 'Specimen [enabled]')
        self.assertFalse(next(c for c in frame.controls if c.label == 'Disable').enabled)
        frame = self.click(frame, 'Actions')
        control = next(c for c in frame.controls if c.label == 'Capture')
        value = {'list': [1]}
        callback = self.view.callback(frame, control, value=value)
        value['list'].append(2)
        callback()
        self.assertEqual(seen, [{'list': [1]}])
        with self.assertRaisesRegex(ManagementError, 'Stale menu'): callback()


if __name__ == '__main__':
    unittest.main()
