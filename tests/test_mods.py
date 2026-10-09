import gc
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import weakref
from types import SimpleNamespace
from expedition33.mods import ModLoader, ModError
from expedition33._console_dispatch import CommandDispatcher


class FakeSession:
    instances = []
    def __init__(self):
        self.closed = False
        dispatcher = CommandDispatcher(self, lambda _: None)
        self.console = SimpleNamespace(poll=lambda: (), dispatcher=dispatcher,
            register=dispatcher.register, remove_owner=dispatcher.remove_owner,
            expose=lambda name, value: dispatcher.namespace.__setitem__(name, value),
            enable=lambda: None, set_toggle_key=lambda key: None)
        self.instances.append(self)
    def _check(self):
        if self.closed: raise RuntimeError('closed')
    def poll(self): return 0
    def close(self):
        self.closed = True
        self.console.dispatcher.close()


class ModTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch('expedition33.mods.Session', FakeSession)
        self.patch.start()
        FakeSession.instances.clear()
    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()
    def source(self, source):
        path = self.root / 'Specimen'
        path.mkdir(exist_ok=True)
        (path / 'mod.py').write_text(source, encoding='utf-8')
    def test_enable_failure_closes_even_when_disable_raises(self):
        self.source('class Mod:\n def enable(self, session): raise SystemExit("enable")\n def disable(self): raise RuntimeError("disable")\n')
        with ModLoader(self.root) as loader:
            loader.load('Specimen')
            with self.assertRaisesRegex(ModError, 'SystemExit.*cleanup.*RuntimeError'):
                loader.enable('Specimen')
            self.assertTrue(FakeSession.instances[0].closed)
            self.assertFalse(loader.status()[0].enabled)
    def test_unload_releases_module_and_instance(self):
        self.source('class Mod:\n def enable(self, session): pass\n def disable(self): pass\n')
        with ModLoader(self.root) as loader:
            loader.load('Specimen')
            key, instance, _ = loader._loaded['Specimen']
            reference = weakref.ref(instance)
            del instance
            loader.enable('Specimen')
            loader.unload('Specimen')
            gc.collect()
            self.assertIsNone(reference())
            self.assertNotIn(key, sys.modules)
            self.assertTrue(FakeSession.instances[0].closed)
    def test_import_failure_removes_temporary_module(self):
        self.source('raise SystemExit("import failure")\n')
        before = set(sys.modules)
        with ModLoader(self.root) as loader:
            with self.assertRaisesRegex(ModError, 'load failed: SystemExit'):
                loader.load('Specimen')
            self.assertFalse(any(key.startswith('_expedition33_mod_') for key in set(sys.modules) - before))
            self.assertEqual(loader.status(), ())

    def test_cleanup_failure_blocks_replacement_even_after_unload(self):
        self.source('class Mod:\n def enable(self, session):\n  session.console.register("specimen", lambda _: "old", owner=self)\n def disable(self): raise RuntimeError("cleanup failed")\n')
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            with self.assertRaisesRegex(ModError, 'cleanup failed'):
                loader.disable('Specimen')
            self.assertFalse(loader.status()[0].enabled)
            self.assertIn('cleanup failed', loader.status()[0].cleanup_error)
            self.assertIn('cleanup failed', loader.registry.views()[0]['cleanup_error'])
            self.assertNotIn('specimen', loader._session.console.dispatcher.command_names)
            with self.assertRaisesRegex(ModError, 'restart the controller'):
                loader.enable('Specimen')
            loader.unload('Specimen')
            # Replacing the file or dropping its module must not erase the failure.
            self.source('class Mod:\n def enable(self, session): pass\n def disable(self): pass\n')
            with self.assertRaisesRegex(ModError, 'restart the controller'):
                loader.load('Specimen')
        with ModLoader(self.root) as fresh:
            fresh.load('Specimen'); fresh.enable('Specimen')
            self.assertTrue(fresh.status()[0].enabled)

    def test_deferred_menu_cleanup_is_not_reported_as_success(self):
        self.source('class Mod:\n def enable(self, session): pass\n def disable(self): pass\n')
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            scope = loader._loaded['Specimen'][2]
            calls = []
            scope._menus.append(SimpleNamespace(close=lambda: calls.append('close') or False))
            with self.assertRaisesRegex(ModError, 'native menu cleanup deferred'):
                loader.disable('Specimen')
            self.assertEqual(calls, ['close'])
            self.assertTrue(scope._closed)
            with self.assertRaisesRegex(ModError, 'restart the controller'):
                loader.enable('Specimen')
            self.assertFalse(loader._session.closed)

    def test_owner_poll_exception_is_contained_and_cleanup_runs(self):
        self.source('class Mod:\n def enable(self, session): pass\n def poll(self): raise SystemExit("pump")\n def disable(self): pass\n')
        with ModLoader(self.root) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            with self.assertRaisesRegex(ModError, 'poll failed: SystemExit'):
                loader.poll('Specimen')
        self.assertTrue(FakeSession.instances[0].closed)

    def test_two_mods_share_session_and_cleanup_owned_commands(self):
        self.source('class Mod:\n def enable(self, session):\n  self.session=session\n  session.console.register("first", lambda _: "one", owner=self)\n def disable(self): pass\n')
        other = self.root / 'Other'; other.mkdir()
        (other / 'mod.py').write_text('class Mod:\n def enable(self, session):\n  self.session=session\n  session.console.register("second", lambda _: "two", owner=self)\n def disable(self): pass\n')
        with ModLoader(self.root) as loader:
            for name in ('Specimen', 'Other'):
                loader.load(name); loader.enable(name, console=True)
            self.assertEqual(len(FakeSession.instances), 1)
            shared = FakeSession.instances[0]
            stale = loader._loaded['Specimen'][2]
            first_mod = loader._loaded['Specimen'][1]
            self.assertIs(shared.console.dispatcher.namespace['my_mod'], first_mod)
            loader.disable('Specimen')
            self.assertFalse(shared.closed)
            self.assertEqual(shared.console.dispatcher.command_names, ('second',))
            self.assertNotIn('my_mod', shared.console.dispatcher.namespace)
            with self.assertRaisesRegex(RuntimeError, 'scope is closed'): stale.poll()
            self.assertEqual(shared.console.dispatcher.execute('second').output.strip(), "'two'")
            loader.enable('Specimen', console=True)
            self.assertEqual(set(shared.console.dispatcher.command_names), {'first','second'})
            loader.unload('Specimen'); loader.unload('Other')
            self.assertTrue(shared.closed)

    def test_console_callback_can_unload_last_mod_during_poll(self):
        self.source('class Mod:\n def enable(self, session): pass\n def disable(self): pass\n')
        with ModLoader(self.root) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            FakeSession.instances[0].console.poll = lambda: loader.unload('Specimen')
            self.assertEqual(loader.poll(), 0)

    def test_failed_second_enable_preserves_first_session(self):
        self.source('class Mod:\n def enable(self, session): pass\n def disable(self): pass\n')
        other = self.root / 'Other'; other.mkdir()
        (other / 'mod.py').write_text('class Mod:\n def enable(self, session): raise SystemExit("second")\n def disable(self): pass\n')
        with ModLoader(self.root) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            loader.load('Other')
            with self.assertRaises(ModError): loader.enable('Other')
            self.assertFalse(FakeSession.instances[0].closed)
            self.assertTrue(loader.status()[0].enabled)


if __name__ == '__main__':
    unittest.main()
