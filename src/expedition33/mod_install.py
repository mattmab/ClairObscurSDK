"""Prepared folder swaps with retained backups and an inspection journal.

No mod executes here. The lifecycle owner must complete cleanup before the swap.
Failed/unknown outcomes are inspected, never automatically replayed or rolled back.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .mod_archive import read_candidate
from .mod_imports import PackageSources


class InstallError(RuntimeError):
    pass


def inspect_transaction(root, transaction_id):
    """Read a prior process's journal and current folder presence; never mutate."""
    root = Path(root).resolve(strict=True)
    if not re.fullmatch(r'[0-9a-f]{32}', transaction_id):
        raise InstallError('Invalid transaction ID')
    directory = root / '.transactions' / transaction_id
    for path in (directory.parent, directory, directory / 'journal.json'):
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root):
            raise InstallError('Journal path leaves the configured root')
    with (directory / 'journal.json').open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise InstallError('Journal exceeds size limit')
    state = json.loads(data)
    if (type(state) is not dict or state.get('version') != 1 or
            type(state.get('mod')) is not str or
            not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}', state['mod'])):
        raise InstallError('Invalid transaction journal')
    paths = {'target': root / state['mod'], 'prepared': directory / 'prepared', 'backup': directory / 'backup'}
    for key, path in paths.items():
        if state.get(key) != str(path):
            raise InstallError('Journal path does not match transaction layout')
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root):
            raise InstallError('Transaction folder is redirected')
    return dict(state, journal=str(directory / 'journal.json'),
                **{key + '_exists': path.exists() for key, path in paths.items()})


class PreparedInstall:
    def __init__(self, root, name, archive, expected_sha256):
        self.root = Path(root).resolve(strict=True)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}', name):
            raise InstallError('Staged mod folder must be an identifier')
        self.target = self.root / name
        self._checked(self.target)
        if not self.target.is_dir() or not (self.target / 'mod.py').is_file():
            raise InstallError('Staged replacement requires an installed mod folder')
        self.candidate = read_candidate(archive, expected_sha256)
        transactions = self.root / '.transactions'
        self._checked(transactions)
        transactions.mkdir(exist_ok=True)
        self.directory = transactions / uuid.uuid4().hex
        self.directory.mkdir()
        self.prepared = self.directory / 'prepared'
        self.backup = self.directory / 'backup'
        self.prepared.mkdir()
        self.used = False
        self.state = {'version': 1, 'mod': name, 'archive_sha256': self.candidate.sha256,
                      'target': str(self.target), 'prepared': str(self.prepared),
                      'backup': str(self.backup), 'phase': 'preparing'}
        self._record('preparing')
        try:
            for relative, data in self.candidate.files:
                path = self.prepared.joinpath(*relative.split('/'))
                self._checked(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as output:
                    output.write(data)
            source = self.prepared / 'mod.py'
            entry = source.read_bytes()
            package = PackageSources(source, compile(entry, str(source), 'exec', dont_inherit=True),
                                     hashlib.sha256(entry).hexdigest())
            self.state['python_package_sha256'] = package.sha256
            self._record('prepared')
        except BaseException as error:
            self._failed(error)
            raise

    def _checked(self, path):
        path = Path(path)
        if not path.resolve().is_relative_to(self.root) or path == self.root:
            raise InstallError('Transaction path is outside the configured mod root')
        for current in (path, *path.parents):
            if current == self.root:
                break
            if current.is_symlink() or current.is_junction():
                raise InstallError('Transaction links/junctions are unsupported')
        return path

    def _record(self, phase):
        self.state['phase'] = phase
        temporary = self.directory / 'journal.tmp'
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(self.state, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.directory / 'journal.json')

    def _failed(self, error):
        self.state['error'] = type(error).__name__ + ': ' + str(error)[:2000]
        # Preserve the last operation phase if recording the error itself fails.
        try:
            self._record(self.state['phase'])
        except OSError:
            pass

    def _verify_prepared(self):
        expected = dict(self.candidate.files)
        found = set()
        for path in self.prepared.rglob('*'):
            self._checked(path)
            if path.is_dir():
                continue
            relative = path.relative_to(self.prepared).as_posix()
            if relative not in expected:
                raise InstallError('Prepared candidate gained an unexpected file')
            with path.open('rb') as stream:
                data = stream.read(len(expected[relative]) + 1)
            if data != expected[relative]:
                raise InstallError('Prepared candidate bytes changed')
            found.add(relative)
        if found != set(expected):
            raise InstallError('Prepared candidate lost files')

    def activate(self, cleanup):
        if self.used or self.state['phase'] != 'prepared':
            raise InstallError('Transaction cannot be replayed; inspect its journal and folders')
        if not callable(cleanup):
            raise InstallError('A lifecycle cleanup callback is required')
        self.used = True
        try:
            self._verify_prepared()
            self._record('cleanup_pending')
            if cleanup() is not True:
                raise InstallError('Lifecycle cleanup did not confirm completion')
            # Recheck bytes/paths after cleanup, before moving either folder.
            self._verify_prepared()
            for path in (self.target, self.prepared, self.backup):
                self._checked(path)
            if self.backup.exists() or not self.target.is_dir():
                raise InstallError('Installed/backup directory state changed')
            self._record('backup_pending')
            self.target.rename(self.backup)
            self._record('backed_up')
            self._record('install_pending')
            self.prepared.rename(self.target)
            self._record('installed')
        except BaseException as error:
            self._failed(error)
            raise
        return self.inspect()

    def inspect(self):
        return dict(self.state, journal=str(self.directory / 'journal.json'),
                    target_exists=self.target.exists(), backup_exists=self.backup.exists(),
                    prepared_exists=self.prepared.exists())
