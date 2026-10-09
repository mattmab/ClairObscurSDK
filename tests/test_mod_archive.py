from dataclasses import FrozenInstanceError
import hashlib
import contextlib
import io
from pathlib import Path
import stat
import tempfile
import runpy
import unittest
from unittest.mock import patch
import zipfile

from expedition33.mod_archive import ArchiveError, inspect_bytes, read_candidate, build_bytes


def pack(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as output:
        for name, payload in entries:
            output.writestr(name, payload)
    return stream.getvalue()


def inspect(data):
    return inspect_bytes(data, hashlib.sha256(data).hexdigest())


class ArchiveTests(unittest.TestCase):
    def test_cli_build_inspect_and_refuse_overwrite(self):
        main = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/mod_archive.py'))['main']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.mkdir()
            (source / 'mod.py').write_text('VALUE=1')
            archive = root / 'candidate.zip'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['build', str(source), str(archive)]), 0)
                before = archive.read_bytes()
                self.assertEqual(main(['build', str(source), str(archive)]), 1)
                self.assertEqual(archive.read_bytes(), before)
                digest = hashlib.sha256(before).hexdigest()
                self.assertEqual(main(['inspect', str(archive), '--expected-sha256', digest]), 0)
                self.assertEqual(main(['inspect', str(archive), '--expected-sha256', '0' * 64]), 1)
                self.assertEqual(main(['build', str(source), str(source / 'archive.zip')]), 1)
            self.assertFalse((source / 'archive.zip').exists())

    def test_reproducible_build_excludes_bytecode_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'mod.py').write_text('VALUE=1')
            (root / '__pycache__').mkdir()
            (root / '__pycache__/mod.pyc').write_bytes(b'not source')
            (root / 'assets').mkdir()
            (root / 'assets/data.json').write_text('{"x": 3}')
            data, candidate = build_bytes(root)
            self.assertEqual(build_bytes(root), (data, candidate))
            self.assertEqual([n for n, _ in candidate.files], ['assets/data.json', 'mod.py'])
            self.assertEqual((root / 'mod.py').read_text(), 'VALUE=1')

    def test_complete_immutable_candidate_with_resources_does_not_execute(self):
        data = pack([('mod.py', 'raise RuntimeError("must not execute")'),
                     ('helpers/__init__.py', 'VALUE = 42'), ('assets/text.json', '{"a":1}')])
        candidate = inspect(data)
        self.assertEqual(candidate.summary()['file_count'], 3)
        self.assertIsInstance(candidate.files, tuple)
        self.assertTrue(all(type(payload) is bytes for _, payload in candidate.files))
        with self.assertRaises(FrozenInstanceError): candidate.sha256 = 'other'
        summary = candidate.summary(); summary['files'].clear()
        self.assertEqual(candidate.summary()['file_count'], 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.zip'; path.write_bytes(data)
            captured = read_candidate(path, candidate.sha256)
            path.write_bytes(b'changed')
            self.assertEqual(captured, candidate)

    def test_traversal_windows_aliases_links_and_collisions_rejected(self):
        paths = ('../escape.py', '/absolute.py', 'C:/drive.py',
                 'folder//file.py', 'folder/./file.py', 'file:stream', 'AUX.txt',
                 'folder/CON .txt', 'CONOUT$', 'COM¹.txt', 'trailing.', 'trailing ',
                 '.git/config', '__pycache__/cache', 'cache.pyc', 'nul\x01file')
        for name in paths:
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                inspect(pack([('mod.py', ''), (name, b'x')]))
        # Windows ZipInfo normalizes backslashes when writing. Replace both
        # stored header spellings to exercise an actual incoming archive.
        backslash = pack([('mod.py', ''), ('folder/file.py', '')]).replace(
            b'folder/file.py', b'folder\\file.py')
        with self.assertRaises(ArchiveError): inspect(backslash)
        for entries in ([('mod.py', ''), ('MOD.py', '')],
                        [('mod.py', ''), ('folder', ''), ('folder/child', '')],
                        [('mod.py', ''), ('Assets/a', ''), ('assets/b', '')]):
            with self.assertRaises(ArchiveError): inspect(pack(entries))
        link = zipfile.ZipInfo('link'); link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ArchiveError): inspect(pack([('mod.py', ''), (link, 'target')]))

    def test_digest_syntax_missing_entry_and_corruption_rejected(self):
        data = pack([('mod.py', '')])
        for digest in ('0' * 64, None, 'A' * 64, True):
            with self.assertRaises(ArchiveError): inspect_bytes(data, digest)
        for entries in ([], [('nested/mod.py', '')], [('mod.py', ''), ('helper.py', 'bad syntax !')]):
            with self.assertRaises(ArchiveError): inspect(pack(entries))
        with self.assertRaises(ArchiveError): inspect(data[:-10])
        with self.assertRaises(ArchiveError): inspect(b'not a ZIP')

    def test_bounded_compressed_and_expanded_inputs(self):
        data = pack([('mod.py', ''), ('resource', b'x' * 1024)])
        for field, limit in (('MAX_ARCHIVE', 5), ('MAX_FILE', 100), ('MAX_EXPANDED', 100), ('MAX_ENTRIES', 1)):
            with self.subTest(field=field), patch('expedition33.mod_archive.' + field, limit):
                with self.assertRaises(ArchiveError): inspect(data)

    def test_explicit_directory_and_regular_permissions_are_supported(self):
        directory = zipfile.ZipInfo('helpers/'); directory.create_system = 3
        directory.external_attr = (stat.S_IFDIR | 0o755) << 16
        candidate = inspect(pack([('mod.py', ''), (directory, ''), ('helpers/a.py', 'VALUE=1')]))
        self.assertEqual(candidate.summary()['file_count'], 2)
