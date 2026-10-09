from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from expedition33.mods import ModLoader, ModError
from expedition33.mod_archive import build_bytes
from test_mods import FakeSession

SOURCE = '''class Mod:
 value = 1
 def enable(self, session):
  session.actions.register('test.value', lambda: self.value, mutates=False)
 def disable(self): pass
'''


class StagedLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mods = self.root / 'mods'; (self.mods / 'Example').mkdir(parents=True)
        (self.mods / 'Example/mod.py').write_text(SOURCE)
        (self.root / 'staging').mkdir()
        self.source = self.root / 'source'; self.source.mkdir()
        self.loader = ModLoader(self.mods, session=FakeSession())
        self.addCleanup(self.loader.close)
        self.loader.load('Example'); self.loader.enable('Example')

    def stage(self, extra=''):
        (self.source / 'mod.py').write_text(SOURCE.replace('value = 1', 'value = 2') + extra)
        archive, candidate = build_bytes(self.source)
        (self.root / 'staging/Example.zip').write_bytes(archive)
        return candidate.sha256

    def test_success_replaces_actions_preserves_backup_and_loads_after_restart(self):
        old_scope = self.loader._loaded['Example'][2]
        result = self.loader.install_staged('Example', expected_sha256=self.stage())
        self.assertEqual(result['phase'], 'committed')
        self.assertTrue(old_scope._closed)
        self.assertIn('value = 1', (Path(result['backup']) / 'mod.py').read_text())
        self.assertEqual(self.loader.actions.dispatch({'op':'action', 'name':'test.value'})['result'], 2)
        self.loader.close()
        with ModLoader(self.mods) as fresh:
            fresh.load('Example')
            self.assertEqual(fresh._loaded['Example'][1].value, 2)

    def test_import_failure_blocks_load_in_fresh_loader(self):
        digest = self.stage('\nraise RuntimeError("replacement failed")\n')
        with self.assertRaisesRegex(ModError, 'replacement failed'):
            self.loader.install_staged('Example', expected_sha256=digest)
        self.assertFalse(self.loader.actions.actions)
        self.assertFalse(self.loader.status())
        with ModLoader(self.mods) as fresh:
            with self.assertRaisesRegex(ModError, 'Unresolved installation'):
                fresh.load('Example')

    def test_cleanup_failure_preserves_old_files_and_blocks_restart_load(self):
        self.loader._loaded['Example'][1].disable = Mock(side_effect=RuntimeError('cleanup failed'))
        with self.assertRaisesRegex(ModError, 'cleanup failed'):
            self.loader.install_staged('Example', expected_sha256=self.stage())
        self.assertIn('value = 1', (self.mods / 'Example/mod.py').read_text())
        with ModLoader(self.mods) as fresh:
            with self.assertRaisesRegex(ModError, 'Unresolved installation'):
                fresh.load('Example')

    def test_bad_archive_does_not_disable_mod(self):
        self.stage()
        old = self.loader._loaded['Example']
        with self.assertRaises(ValueError):
            self.loader.install_staged('Example', expected_sha256='0' * 64)
        self.assertIs(self.loader._loaded['Example'], old)
        self.assertFalse(old[2]._closed)

    def test_bridge_requires_consent_and_routes_to_fixed_staging_path(self):
        digest = self.stage()
        request = dict(op='mod_install_staged', mod='Example', expected_sha256=digest)
        self.assertFalse(self.loader.actions.dispatch(request)['success'])
        reply = self.loader.actions.dispatch(dict(request, allow_mutation=True))
        self.assertTrue(reply['success'], reply)
        self.assertEqual(reply['result']['phase'], 'committed')
