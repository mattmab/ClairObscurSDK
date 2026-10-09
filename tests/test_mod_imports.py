import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from expedition33.mods import ModLoader, ModError
from expedition33.mod_archive import build_bytes


SOURCE = '''from .nested.helper import VALUE
class Mod:
 value = VALUE
 def enable(self, session): pass
 def disable(self): pass
 def lazy(self):
  from . import lazy
  return lazy.VALUE
'''


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.loader = ModLoader(self.root)
        self.addCleanup(self.loader.close)

    def write(self, name, value):
        folder = self.root / name
        (folder / 'nested').mkdir(parents=True, exist_ok=True)
        (folder / 'mod.py').write_text(SOURCE)
        (folder / 'nested/__init__.py').write_text('from .helper import VALUE\n')
        (folder / 'nested/helper.py').write_text('VALUE=' + str(value))
        (folder / 'lazy.py').write_text('VALUE=' + str(value))
        return folder

    def test_mods_with_same_relative_names_are_isolated_and_unload_owned_tree(self):
        before_path = list(sys.path)
        for name, value in [('First', 1), ('Second', 2)]:
            self.write(name, value); self.loader.load(name)
        key1, first, _ = self.loader._loaded['First']
        key2, second, _ = self.loader._loaded['Second']
        self.assertEqual((first.value, second.value), (1, 2))
        self.assertEqual(first.lazy(), 1)
        self.assertIn(key1 + '.nested.helper', sys.modules)
        self.loader.unload('First')
        self.assertFalse(any(n == key1 or n.startswith(key1 + '.') for n in sys.modules))
        self.assertIn(key2 + '.nested.helper', sys.modules)
        self.assertEqual(second.lazy(), 2)
        self.assertEqual(sys.path, before_path)

    def test_lazy_source_is_captured_and_never_falls_through_to_new_disk_files(self):
        folder = self.write('First', 1); self.loader.load('First')
        key, instance, _ = self.loader._loaded['First']
        (folder / 'lazy.py').write_text('VALUE=999')
        self.assertEqual(instance.lazy(), 1)
        (folder / 'uncaptured.py').write_text('VALUE=5')
        with self.assertRaises(ModuleNotFoundError):
            __import__(key + '.uncaptured')

    def test_helper_only_change_requires_tree_digest_and_replaces_namespace(self):
        self.write('First', 1); self.loader.load('First')
        old_key = self.loader._loaded['First'][0]
        old_digest = self.loader.status()[0].package_sha256
        self.write('First', 2)
        entry_digest = hashlib.sha256((self.root / 'First/mod.py').read_bytes()).hexdigest()
        with self.assertRaisesRegex(ModError, 'expected_package_sha256'):
            self.loader.reload('First', expected_sha256=entry_digest, changed_only=True)
        self.assertEqual(self.loader._loaded['First'][0], old_key)
        snapshot = self.loader._read_source('First')
        self.assertEqual(build_bytes(self.root / 'First')[1].summary()['python_package_sha256'], snapshot[3].sha256)
        self.assertNotEqual(snapshot[3].sha256, old_digest)
        result = self.loader.reload('First', expected_sha256=entry_digest,
            expected_package_sha256=snapshot[3].sha256, changed_only=True)
        self.assertTrue(result['changed'])
        self.assertEqual(self.loader._loaded['First'][1].value, 2)
        self.assertFalse(any(n == old_key or n.startswith(old_key + '.') for n in sys.modules))

    def test_failed_import_evicts_children_and_finder_but_not_other_modules(self):
        folder = self.write('First', 1)
        (folder / 'mod.py').write_text(SOURCE + '\nraise RuntimeError("import failed")\n')
        before_modules, before_finders = set(sys.modules), tuple(sys.meta_path)
        with self.assertRaisesRegex(ModError, 'import failed'): self.loader.load('First')
        self.assertFalse(any(n.startswith('_expedition33_mod_') for n in set(sys.modules) - before_modules))
        self.assertEqual(tuple(sys.meta_path), before_finders)

    def test_helper_syntax_preflight_preserves_old_record(self):
        folder = self.write('First', 1); self.loader.load('First')
        record = self.loader._loaded['First']
        (folder / 'nested/helper.py').write_text('bad syntax !')
        with self.assertRaisesRegex(ModError, 'package preflight'):
            self.loader.reload('First', expected_sha256=self.loader.status()[0].source_sha256)
        self.assertIs(self.loader._loaded['First'], record)

    def test_implicit_package_supported_and_ambiguous_module_rejected(self):
        folder = self.root / 'First'; (folder / 'implicit').mkdir(parents=True)
        (folder / 'mod.py').write_text(SOURCE.replace('nested.helper', 'implicit.helper'))
        (folder / 'implicit/helper.py').write_text('VALUE=7')
        self.loader.load('First')
        self.assertEqual(self.loader._loaded['First'][1].value, 7)
        self.loader.unload('First')
        (folder / 'implicit.py').write_text('VALUE=8')
        with self.assertRaisesRegex(ModError, 'also a package directory'): self.loader.load('First')
