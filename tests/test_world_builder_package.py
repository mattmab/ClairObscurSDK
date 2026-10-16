import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_world_builder import build
from expedition33.mod_archive import read_candidate


class StandaloneWorldBuilderTests(unittest.TestCase):
    def test_standalone_archive_installs_without_private_state_or_core_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            result = build(Path(folder) / 'release')
            candidate = read_candidate(Path(folder) / 'release/SDK_Mods/E33WorldBuilder.sdkmod', result['mods'][0]['sha256'])
            self.assertIn('mod.py', dict(candidate.files))
            self.assertIn('e33.world-builder', dict(candidate.files)['mod.py'].decode())
            with zipfile.ZipFile(result['archive']) as archive:
                self.assertEqual(set(archive.namelist()), {
                    'SDK_Mods/E33WorldBuilder.sdkmod', 'README-WorldBuilder.txt', 'LICENSE'})
            self.assertEqual(result['requires_sdk'], '0.1.0-rc11')
