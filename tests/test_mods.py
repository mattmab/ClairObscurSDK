import gc
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import weakref
from expedition33.mods import ModLoader, ModError


class FakeSession:
    instances = []
    def __init__(self):
        self.closed = False
        self.instances.append(self)
    def close(self):
        self.closed = True


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


if __name__ == '__main__':
    unittest.main()
