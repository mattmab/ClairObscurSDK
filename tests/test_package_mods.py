import json
from pathlib import Path
import runpy
import tempfile
import unittest
import zipfile

build_all = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/package_mods.py'))['build_all']


class PackageMods(unittest.TestCase):
    def test_resources_reproducible_and_no_source_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'mods' / 'One'
            source.mkdir(parents=True)
            (source / 'mod.py').write_text("raise RuntimeError('must not execute')\n", encoding='utf8')
            (source / 'catalog.json').write_text('{"scenes":[]}', encoding='utf8')
            a = build_all(root / 'mods', root / 'a')
            b = build_all(root / 'mods', root / 'b')
            self.assertEqual(a, b)
            self.assertEqual((root / 'a/One.sdkmod').read_bytes(), (root / 'b/One.sdkmod').read_bytes())
            with zipfile.ZipFile(root / 'a/One.sdkmod') as archive:
                self.assertEqual(json.loads(archive.read('catalog.json')), {'scenes': []})
            with self.assertRaises(FileExistsError):
                build_all(root / 'mods', root / 'a')

    def test_bad_source_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'mods/Bad'
            source.mkdir(parents=True)
            (source / 'mod.py').write_text('def !', encoding='utf8')
            with self.assertRaises(ValueError):
                build_all(root / 'mods', root / 'output')
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
