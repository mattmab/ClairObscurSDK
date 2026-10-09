from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from expedition33.management import ManagementError
from expedition33.management_console import ConsoleMenu
from expedition33.mods import ModLoader, ModError
from expedition33.settings import SettingsStore
from test_mods import FakeSession


SOURCE = '''from expedition33.management import Action, ModDefinition, Option
class Mod:
 def __init__(self): self.value = None; self.calls = 0
 def management(self):
  return ModDefinition('specimen', 'Specimen', options=(
   Option('count', 'Count', 'int', 3, minimum=0, maximum=10, on_change=self.change),
   Option('toggle', 'Toggle', 'bool', True),
   Option('choice', 'Choice', 'choice', 'a', choices=('a', 'b'))),
   actions=(Action('read', 'Read current value', self.read),
            Action('fail', 'Fail safely', self.fail)))
 def enable(self, session): self.session = session
 def disable(self): self.session = None
 def change(self, value): self.value = value
 def read(self, argument): self.calls += 1; return self.value
 def fail(self, argument): raise SystemExit('contained')
'''


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        folder = self.root / 'Specimen'; folder.mkdir()
        (folder / 'mod.py').write_text(SOURCE, encoding='utf-8')
        self.patch = patch('expedition33.mods.Session', FakeSession)
        self.patch.start()
        self.store = SettingsStore(self.root / 'settings.json')
        self.loader = ModLoader(self.root, settings=self.store)
        self.loader.load('Specimen')
        self.registry = self.loader.registry
    def tearDown(self):
        self.loader.close()
        self.patch.stop()
        self.temp.cleanup()

    def test_saved_options_apply_on_enable_and_views_are_copies(self):
        selection = self.registry.select('specimen')
        self.registry.set_option(selection, 'count', 7)
        self.assertIsNone(self.loader._loaded['Specimen'][1].value)
        self.loader.enable('Specimen')
        with self.assertRaisesRegex(ManagementError, 'Stale'): self.registry.view(selection)
        selection = self.registry.select('specimen')
        self.assertEqual(self.registry.invoke(selection, 'read'), 7)
        view = self.registry.view(selection); view['options'][0]['value'] = 999
        self.assertEqual(self.registry.option(selection, 'count'), 7)
        self.registry.set_option(selection, 'count', 8)
        self.assertEqual(self.registry.invoke(selection, 'read'), 8)
        self.loader.unload('Specimen'); self.loader.load('Specimen'); self.loader.enable('Specimen')
        selection = self.registry.select('specimen')
        self.assertEqual(self.registry.invoke(selection, 'read'), 8)
        self.assertEqual(SettingsStore(self.store.path).get('specimen')['options']['count'], 8)

    def test_disabled_and_stale_action_callbacks_are_rejected(self):
        selection = self.registry.select('specimen')
        with self.assertRaisesRegex(ManagementError, 'Enable'): self.registry.invoke(selection, 'read')
        selection = self.registry.set_enabled(selection, True)
        original_instance = self.loader._loaded['Specimen'][1]
        self.loader.unload('Specimen'); self.loader.load('Specimen'); self.loader.enable('Specimen')
        with self.assertRaises(ManagementError): self.registry.invoke(selection, 'read')
        self.assertEqual(original_instance.calls, 0)
        self.assertEqual(self.registry.invoke(self.registry.select('specimen'), 'read'), 3)
        self.assertEqual(len(self.registry.views()), 1)

    def test_native_action_uses_registry_and_rejects_reload(self):
        from test_button_actions import ButtonActionsTests
        native = ButtonActionsTests()
        native.setUp()
        self.loader.enable('Specimen')
        selected = self.registry.select('specimen')
        instance = self.loader._loaded['Specimen'][1]
        action = native.menu.bind_action(self.registry.action_callback(selected, 'read'))
        native.events = [native.event(action)]
        self.assertEqual(action._poll(), 1)
        self.assertEqual(instance.calls, 1)
        self.loader.unload('Specimen')
        self.loader.load('Specimen')
        self.loader.enable('Specimen')
        native.events = [native.event(action, 2)]
        self.assertEqual(action._poll(), 1)
        self.assertIn('Stale mod selection', action.failures[0])
        self.assertEqual(instance.calls, 1)
        self.assertEqual(self.loader._loaded['Specimen'][1].calls, 0)
        self.assertTrue(native.menu.close())
        self.assertEqual(action._poll(), 0)

    def test_action_callback_captures_arguments_and_checks_each_delivery(self):
        self.loader.enable('Specimen')
        selected = self.registry.select('specimen')
        from dataclasses import replace
        from expedition33.management import Action
        entry = self.registry._entries['specimen']
        seen = []
        def receive(value):
            seen.append(value['items'][:])
            value['items'].append('callback mutation')
        entry.definition = replace(entry.definition, actions=(Action('capture', 'Capture', receive),))
        argument = {'items': [1]}
        callback = self.registry.action_callback(selected, 'capture', argument)
        argument['items'].append(2)
        callback(object()); callback(object())
        self.assertEqual(seen, [[1], [1]])
        self.loader.disable('Specimen')
        with self.assertRaises(ManagementError): callback(object())
        self.assertEqual(len(seen), 2)

    def test_action_callback_rejects_invalid_binding_before_dispatch(self):
        selected = self.registry.select('specimen')
        with self.assertRaisesRegex(ManagementError, 'Enable'):
            self.registry.action_callback(selected, 'read')
        self.loader.enable('Specimen')
        selected = self.registry.select('specimen')
        with self.assertRaisesRegex(ManagementError, 'Unknown'):
            self.registry.action_callback(selected, 'missing')
        with self.assertRaisesRegex(ManagementError, '64 KiB'):
            self.registry.action_callback(selected, 'read', 'x' * 65537)
        self.assertEqual(self.loader._loaded['Specimen'][1].calls, 0)

    def test_invalid_option_and_failed_persistence_do_not_change_runtime(self):
        self.loader.enable('Specimen'); selection = self.registry.select('specimen')
        for value in (True, 11, 10**1000, float('nan')):
            with self.assertRaises(ManagementError): self.registry.set_option(selection, 'count', value)
        with patch.object(self.store, 'save', side_effect=OSError('disk failed')):
            with self.assertRaises(OSError): self.registry.set_option(selection, 'count', 7)
        self.assertEqual(self.registry.invoke(selection, 'read'), 3)
        self.assertEqual(self.registry.option(selection, 'count'), 3)

    def test_application_failure_reports_committed_preference_and_no_replay(self):
        self.loader.enable('Specimen'); selection = self.registry.select('specimen')
        # A supported callback can fail after touching runtime state; do not claim
        # a rollback or automatically repeat it.
        count = []
        def fail(value): count.append(value); raise SystemExit('application')
        entry = self.registry._entries['specimen']
        from dataclasses import replace
        entry.definition = replace(entry.definition, options=(replace(entry.definition.options[0], on_change=fail),))
        with self.assertRaisesRegex(ManagementError, 'saved.*application failed'):
            self.registry.set_option(selection, 'count', 6)
        self.assertEqual(count, [6])
        self.assertEqual(self.store.get('specimen')['options']['count'], 6)
        self.assertIn('SystemExit', self.registry.view(selection)['error'])

    def test_console_navigation_preserves_other_routes_and_cleanup(self):
        shared = FakeSession()
        menu = ConsoleMenu(self.registry, shared.console)
        dispatch = shared.console.dispatcher
        result = dispatch.execute('mods')
        self.assertFalse(result.failed); self.assertIn('specimen', result.output)
        self.assertFalse(dispatch.execute('mods select specimen').failed)
        self.assertFalse(dispatch.execute('mods enable').failed)
        self.assertFalse(dispatch.execute('mods set count 9').failed)
        self.assertIn('9', dispatch.execute('mods action read').output)
        self.assertTrue(dispatch.execute('mods action fail').failed)
        self.assertEqual(dispatch.execute('py x = 4; x').output.strip(), '4')
        self.assertEqual(dispatch.execute('stat fps').route, 'native')
        self.assertFalse(dispatch.execute('mods quit').failed)
        self.assertTrue(dispatch.execute('mods actions').failed)
        self.assertFalse(dispatch.execute('mods').failed)
        menu.close(); self.assertNotIn('mods', dispatch.command_names)
        with self.assertRaises(ManagementError): menu.command('')

    def test_core_protection_duplicate_id_and_owner_thread(self):
        other = self.root / 'Other'; other.mkdir()
        (other / 'mod.py').write_text(SOURCE, encoding='utf-8')
        with self.assertRaisesRegex(ModError, 'Duplicate'): self.loader.load('Other')
        self.assertEqual(len(self.loader.status()), 1)
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        entry.definition = replace(entry.definition, protected=True)
        selection = self.registry.select('specimen')
        with self.assertRaisesRegex(ManagementError, 'protected'): self.registry.set_enabled(selection, False)
        with self.assertRaisesRegex(ManagementError, 'protected'): self.registry.unload(selection)
        errors = []
        def foreign():
            try: self.registry.views()
            except ManagementError as error: errors.append(str(error))
        thread = threading.Thread(target=foreign); thread.start(); thread.join()
        self.assertIn('owner thread', errors[0])

    def test_borrowed_session_survives_loader_cleanup(self):
        shared = FakeSession()
        with ModLoader(self.root, session=shared) as borrowed:
            borrowed.load('Specimen'); borrowed.enable('Specimen')
            borrowed.disable('Specimen')
            self.assertFalse(shared.closed)
            borrowed.enable('Specimen')
        self.assertFalse(shared.closed)
        self.assertEqual(borrowed.registry.views(), ())

    def test_shutdown_request_defers_cleanup_until_host_exits(self):
        self.loader.enable('Specimen')
        shared = self.loader._session
        self.registry.request_shutdown()
        self.assertTrue(self.loader.stop_requested)
        self.assertFalse(shared.closed)
        self.assertEqual(self.registry.invoke(self.registry.select('specimen'), 'read'), 3)
        self.loader.close()
        self.assertTrue(shared.closed)

    def test_recursive_option_change_rejected_before_persistence(self):
        self.loader.enable('Specimen'); selection = self.registry.select('specimen')
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        def recurse(value): self.registry.set_option(selection, 'count', value + 1)
        entry.definition = replace(entry.definition, options=(replace(entry.definition.options[0], on_change=recurse),))
        with self.assertRaisesRegex(ManagementError, 'Recursive'): self.registry.set_option(selection, 'count', 4)
        self.assertEqual(self.store.get('specimen')['options']['count'], 4)

    def test_actions_rejected_during_enable_and_failed_option_application_cleans_scope(self):
        instance = self.loader._loaded['Specimen'][1]
        original_enable = instance.enable
        def enable(session):
            original_enable(session)
            with self.assertRaisesRegex(ManagementError, 'Enable'):
                self.registry.invoke(self.registry.select('specimen'), 'read')
        instance.enable = enable
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        def fail(value): raise RuntimeError('bad option application')
        entry.definition = replace(entry.definition, options=(replace(entry.definition.options[0], on_change=fail),))
        with self.assertRaisesRegex(ModError, 'bad option application'): self.loader.enable('Specimen')
        self.assertFalse(self.loader.status()[0].enabled)
        self.assertIsNone(self.loader._session)
        self.assertIsNone(instance.session)


if __name__ == '__main__': unittest.main()
