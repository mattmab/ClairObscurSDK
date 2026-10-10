from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from expedition33.mod_lock import ModRootLock
from expedition33.mods import ModLoader, ModError


class ModLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def child(self, source):
        sdk_source = str(Path(__file__).resolve().parents[1] / 'src')
        source = f'import sys; sys.path.insert(0, {sdk_source!r}); ' + source
        return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', source, str(self.root)],
                              capture_output=True, text=True, timeout=10)

    def test_same_and_other_processes_are_excluded_until_close(self):
        loader = ModLoader(self.root)
        self.addCleanup(loader.close)
        with self.assertRaisesRegex(RuntimeError, 'already owned'):
            ModLoader(self.root)
        source = 'import sys; from expedition33.mod_lock import ModRootLock; lock=ModRootLock(sys.argv[1])'
        conflict = self.child(source)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn('already owned', conflict.stderr)
        loader.close()
        with self.assertRaisesRegex(ModError, 'closed'):
            loader.load('Example')
        available = self.child(source)
        self.assertEqual(available.returncode, 0, available.stderr)
        self.assertTrue((self.root / '.sdk-loader.lock').exists())

    def test_process_exit_releases_lock_without_cleanup(self):
        child = self.child('import os, sys; from expedition33.mod_lock import ModRootLock; '
                           'lock=ModRootLock(sys.argv[1]); os._exit(0)')
        self.assertEqual(child.returncode, 0, child.stderr)
        lock = ModRootLock(self.root)
        lock.close()

    def test_distinct_roots_can_share_one_controller(self):
        other = self.root / 'other'; other.mkdir()
        with ModLoader(self.root), ModLoader(other):
            pass
