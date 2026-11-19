import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
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

    def bundled_example(self):
        directory = self.sdk / 'bundled-mods' / 'Example'
        directory.mkdir(parents=True)
        (directory / 'mod.py').write_text('class Mod: bundled = True\n', encoding='utf8')
        (directory / 'resource.txt').write_bytes(b'bundled payload')
        _, candidate = build_bytes(directory)
        return directory, dict(candidate.summary(), folder='Example', layout='loose')

    def test_loose_bundle_loads_without_an_archive_directory(self):
        (self.archives / 'Example.sdkmod').unlink()
        self.archives.rmdir()
        _, row = self.bundled_example()
        target = materialize(self.archives, self.sdk, bundled_rows=(row,))
        self.assertEqual((target / 'Example/mod.py').read_text(encoding='utf8'),
                         'class Mod: bundled = True\n')
        self.assertEqual((target / 'Example/resource.txt').read_bytes(), b'bundled payload')

    def test_loose_bundle_takes_precedence_and_optional_archive_still_loads(self):
        old_archive = (self.archives / 'Example.sdkmod').read_bytes()
        (self.archives / 'Optional.sdkmod').write_bytes(old_archive)
        _, row = self.bundled_example()
        target = materialize(self.archives, self.sdk, bundled_rows=(row,))
        self.assertEqual((target / 'Example/mod.py').read_text(encoding='utf8'),
                         'class Mod: bundled = True\n')
        self.assertEqual((target / 'Optional/mod.py').read_text(encoding='utf8'), 'class Mod: pass\n')
        self.assertEqual((self.archives / 'Example.sdkmod').read_bytes(), old_archive)

    def test_changed_loose_file_preserves_existing_cache(self):
        directory, row = self.bundled_example()
        target = materialize(self.archives, self.sdk, bundled_rows=(row,))
        (directory / 'resource.txt').write_bytes(b'altered payload')
        with self.assertRaises(ValueError):
            materialize(self.archives, self.sdk, bundled_rows=(row,))
        self.assertEqual((target / 'Example/resource.txt').read_bytes(), b'bundled payload')
        self.assertFalse(any(self.sdk.glob('mods-stage-*')))

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

    def test_combined_budget_counts_expanded_resources_and_preserves_cache(self):
        target=materialize(self.archives,self.sdk)
        before=(target/'Example/mod.py').read_bytes()
        payload=(self.archives/'Example.sdkmod').read_bytes()
        (self.archives/'Second.sdkmod').write_bytes(payload)
        with patch('expedition33.release_mods.MAX_COMBINED_EXPANDED',len(before)*2):
            materialize(self.archives,self.sdk)
        with patch('expedition33.release_mods.MAX_COMBINED_EXPANDED',len(before)*2-1):
            with self.assertRaisesRegex(ValueError,'Combined expanded'):materialize(self.archives,self.sdk)
        self.assertEqual((target/'Example/mod.py').read_bytes(),before)
        self.assertFalse(any(self.sdk.glob('mods-stage-*')))

    def test_aggregate_can_accommodate_one_valid_maximum_pack(self):
        from expedition33.release_mods import MAX_COMBINED_EXPANDED
        from expedition33.mod_archive import MAX_EXPANDED
        self.assertGreaterEqual(MAX_COMBINED_EXPANDED,MAX_EXPANDED)


if __name__ == '__main__':
    unittest.main()
