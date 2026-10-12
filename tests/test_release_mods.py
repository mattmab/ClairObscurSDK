import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from expedition33.release_mods import materialize
from expedition33.mod_archive import build_bytes


class ReleaseModsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sdk = self.root / 'SDK'; self.sdk.mkdir()
        self.archives = self.root / 'SDK_Mods'; self.archives.mkdir()
        source = self.root / 'source'; source.mkdir()
        (source / 'mod.py').write_text('class Mod: pass\n')
        data, _ = build_bytes(source)
        (self.archives / 'Example.sdkmod').write_bytes(data)

    def test_invalid_archive_preserves_previous_cache(self):
        target = materialize(self.archives, self.sdk)
        before = (target / 'Example/mod.py').read_bytes()
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('../outside.py', 'bad')
            archive.writestr('mod.py', 'class Mod: pass')
        (self.archives / 'Bad.sdkmod').write_bytes(data.getvalue())
        with self.assertRaises(ValueError):
            materialize(self.archives, self.sdk)
        self.assertEqual((target / 'Example/mod.py').read_bytes(), before)
        self.assertFalse((self.sdk / 'outside.py').exists())

    def test_unmanaged_folder_is_never_overwritten(self):
        target = self.sdk / 'mods'; target.mkdir()
        (target / 'mine.txt').write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            materialize(self.archives, self.sdk)
        self.assertEqual((target / 'mine.txt').read_text(), 'preserve')

    def test_interrupted_swap_recovers_and_refreshes(self):
        target = materialize(self.archives, self.sdk)
        target.rename(self.sdk / 'mods.previous')
        target = materialize(self.archives, self.sdk)
        self.assertTrue((target / 'Example/mod.py').is_file())
        self.assertFalse((self.sdk / 'mods.previous').exists())

    def test_archive_limit_is_checked_before_changes(self):
        for index in range(64):
            (self.archives / f'Mod{index}.sdkmod').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'between 1 and 64'):
            materialize(self.archives, self.sdk)
        self.assertFalse((self.sdk / 'mods').exists())


if __name__ == '__main__':
    unittest.main()
