import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rc24_package', ROOT / 'scripts/package_rc24.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class RC24PackagingTests(unittest.TestCase):
    def test_core_and_optional_downloads_have_separate_ownership(self):
        self.assertEqual(release.CORE, {'SDKManagement', 'IntrospectionHarness', 'LiveObjectViewer'})
        self.assertFalse(release.CORE & release.OPTIONAL)
        self.assertIn('EnemyHealth', release.OPTIONAL)
        self.assertNotIn('E33MapOverlays', release.OPTIONAL)

    def test_sdk_tracks_one_mods_pin_instead_of_mod_sources(self):
        lines = release.git('ls-files', '--stage', 'mods').splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('160000 '))
        self.assertEqual(lines[0].split()[1], release.git('rev-parse', 'HEAD', cwd=ROOT / 'mods'))


if __name__ == '__main__':
    unittest.main()
