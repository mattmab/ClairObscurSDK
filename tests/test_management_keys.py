from dataclasses import replace
import unittest
from unittest.mock import patch

import test_management as fixture
from expedition33.keys import normalize_key, VIRTUAL_KEYS
from expedition33.management import Keybind, ManagementError
from expedition33.management_console import ConsoleMenu
from expedition33.management_view import ManagementView
from expedition33.settings import SettingsStore
from test_mods import FakeSession


class ManagementKeysTests(unittest.TestCase):
    def setUp(self):
        fixture.ManagementTests.setUp(self)
        entry = self.registry._entries['specimen']
        instance = self.loader._loaded['Specimen'][1]
        entry.definition = replace(entry.definition,
            keybinds=(Keybind('read-key', 'Read key', 'F6', instance.read),))

    tearDown = fixture.ManagementTests.tearDown

    def test_normalization_rejects_chords_and_console_punctuation(self):
        self.assertEqual(normalize_key('f6'), 'F6')
        self.assertEqual(VIRTUAL_KEYS[normalize_key('a')], 65)
        self.assertIsNone(normalize_key(None))
        for key in ('Ctrl+F6', '`', '~', '', ' F6', True, 117):
            with self.assertRaises(ValueError): normalize_key(key)

    def test_punctuation_names_and_persistence(self):
        for alias, canonical, vk in [(',', ',', 188), ('Comma', ',', 188),
                                      ('.', '.', 190), ('Period', '.', 190), ('dot', '.', 190)]:
            self.assertEqual(normalize_key(alias),canonical)
            self.assertEqual(VIRTUAL_KEYS[canonical],vk)
            self.registry.set_keybind(self.registry.select('specimen'),'read-key',alias)
            self.assertEqual(SettingsStore(self.store.path).get('specimen')['keybinds']['read-key'],canonical)

    def test_mapping_persists_and_revokes_old_delivery(self):
        self.loader.enable('Specimen')
        selected = self.registry.select('specimen')
        self.assertEqual(self.registry.dispatch_key(selected, 'read-key', 'F6'), 3)
        new = self.registry.set_keybind(selected, 'read-key', 'f7')
        with self.assertRaisesRegex(ManagementError, 'Stale'):
            self.registry.dispatch_key(selected, 'read-key', 'F6')
        with self.assertRaisesRegex(ManagementError, 'mapping changed'):
            self.registry.dispatch_key(new, 'read-key', 'F6')
        self.assertEqual(self.registry.dispatch_key(new, 'read-key', 'F7'), 3)
        self.assertEqual(SettingsStore(self.store.path).get('specimen')['keybinds'], {'read-key': 'F7'})
        definition = self.registry._entries['specimen'].definition
        self.registry.unregister('Specimen')
        self.registry.register('Specimen', definition)
        self.assertEqual(self.registry.keybind(self.registry.select('specimen'), 'read-key'), 'F7')

    def test_failed_save_keeps_mapping_and_generation(self):
        self.loader.enable('Specimen')
        selected = self.registry.select('specimen')
        with patch.object(self.store, 'save', side_effect=OSError('full disk')):
            with self.assertRaises(OSError): self.registry.set_keybind(selected, 'read-key', 'F8')
        self.assertEqual(self.registry.select('specimen'), selected)
        self.assertEqual(self.registry.keybind(selected, 'read-key'), 'F6')

    def test_disable_unload_and_unbind_remove_routes(self):
        self.assertEqual(self.registry.key_routes(), ())
        self.loader.enable('Specimen')
        selected, binding, key, vk = self.registry.key_routes()[0]
        self.assertEqual((binding, key, vk), ('read-key', 'F6', 117))
        new = self.registry.set_keybind(selected, binding, None)
        self.assertEqual(self.registry.key_routes(), ())
        new = self.registry.set_keybind(new, binding, reset=True)
        self.assertEqual(len(self.registry.key_routes()), 1)
        self.loader.disable('Specimen')
        self.assertEqual(self.registry.key_routes(), ())
        with self.assertRaises(ManagementError): self.registry.dispatch_key(new, binding, key)
        self.loader.unload('Specimen')
        self.assertEqual(self.registry.key_routes(), ())

    def test_conflicts_suppress_all_owners_until_resolved(self):
        self.loader.enable('Specimen')
        entry = self.registry._entries['specimen']
        entry.definition = replace(entry.definition, keybinds=entry.definition.keybinds +
            (Keybind('duplicate', 'Duplicate', 'F6', entry.definition.keybinds[0].callback),))
        selected = self.registry.select('specimen')
        self.assertEqual(len(self.registry.key_conflicts()['F6']), 2)
        self.assertEqual(self.registry.key_routes(), ())
        with self.assertRaisesRegex(ManagementError, 'Conflicting'):
            self.registry.dispatch_key(selected, 'read-key', 'F6')
        self.registry.set_keybind(selected, 'duplicate', 'F7')
        self.assertEqual(len(self.registry.key_routes()), 2)
        self.assertEqual(self.registry.key_conflicts(), {})

    def test_callback_error_is_contained_without_replay(self):
        self.loader.enable('Specimen')
        entry = self.registry._entries['specimen']
        count = []
        def fail(_):
            count.append(1)
            raise SystemExit('bad mod')
        entry.definition = replace(entry.definition, keybinds=(Keybind('bad', 'Bad', 'F8', fail),))
        selected = self.registry.select('specimen')
        with self.assertRaisesRegex(ManagementError, 'Keybind callback failed.*SystemExit'):
            self.registry.dispatch_key(selected, 'bad', 'F8')
        self.assertEqual(count, [1])

    def test_console_remap_unbind_reset(self):
        console = FakeSession().console
        menu = ConsoleMenu(self.registry, console)
        for text in ('mods select specimen', 'mods bind read-key F7', 'mods keys',
                     'mods unbind read-key', 'mods resetkey read-key'):
            self.assertFalse(console.dispatcher.execute(text).failed, text)
        self.assertEqual(self.registry.keybind(menu.selection, 'read-key'), 'F6')
        menu.close()

    def test_native_presenter_picker_persists_and_revokes_old_control(self):
        view = ManagementView(self.registry)
        frame = view.render()
        def choose(label):
            nonlocal frame
            control = next(c for c in frame.controls if c.label.startswith(label))
            frame = view.activate(frame.revision, control.token)
        choose('Specimen'); choose('Keybinds'); choose('Read key')
        old = frame
        choose('Unbind')
        self.assertIsNone(self.registry.keybind(view.selection, 'read-key'))
        with self.assertRaisesRegex(ManagementError, 'Stale menu control'):
            view.activate(old.revision, 0)
        choose('Read key'); choose('Reset to default')
        self.assertEqual(self.registry.keybind(view.selection, 'read-key'), 'F6')


if __name__ == '__main__': unittest.main()
