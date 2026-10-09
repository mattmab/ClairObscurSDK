import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from expedition33.mod_archive import build_bytes
from expedition33.mod_install import PreparedInstall, InstallError, inspect_transaction, recover_transaction
from expedition33.mod_lock import ModRootLock


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mods = self.root / 'mods'; self.mods.mkdir()
        self.target = self.mods / 'Example'; self.target.mkdir()
        (self.target / 'mod.py').write_text('VERSION=1')
        self.source = self.root / 'source'; self.source.mkdir()
        (self.source / 'mod.py').write_text('from .helper import VERSION')
        (self.source / 'helper.py').write_text('VERSION=2')
        (self.source / 'data.json').write_text('{"version":2}')
        self.archive = self.root / 'candidate.zip'
        data, candidate = build_bytes(self.source)
        self.archive.write_bytes(data)
        self.digest = candidate.sha256

    def prepare(self):
        return PreparedInstall(self.mods, 'Example', self.archive, self.digest)

    def recover(self, transaction):
        return recover_transaction(self.mods, transaction.directory.name,
                                   expected_journal_sha256=transaction.inspect()['journal_sha256'])

    def test_offline_recovery_preserves_rejected_candidate_without_importing_it(self):
        transaction = self.prepare()
        transaction.activate(lambda: True)
        (self.target / 'mod.py').write_text('raise RuntimeError("must not execute")')
        result = self.recover(transaction)
        self.assertEqual(result['phase'], 'rolled_back')
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
        self.assertIn('must not execute', (transaction.directory / 'rejected/mod.py').read_text())
        with self.assertRaisesRegex(InstallError, 'not an unresolved'):
            self.recover(transaction)

    def test_recovery_before_swap_keeps_installed_folder_and_candidate(self):
        transaction = self.prepare()
        with self.assertRaises(InstallError): transaction.activate(lambda: False)
        result = self.recover(transaction)
        self.assertEqual(result['recovery'], 'kept_original')
        self.assertEqual(result['phase'], 'rolled_back')
        self.assertIn('installation_error', result)
        self.assertTrue(transaction.prepared.is_dir())
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')

    def test_recovery_after_backup_rename_restores_original(self):
        transaction = self.prepare()
        transaction._record('backup_pending')
        self.target.rename(transaction.backup)
        self.assertEqual(self.recover(transaction)['phase'], 'rolled_back')
        self.assertTrue(transaction.prepared.is_dir())
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')

    def test_recovery_requires_current_journal_and_exclusive_root(self):
        transaction = self.prepare()
        old = transaction.inspect()['journal_sha256']
        transaction._record('cleanup_pending')
        with self.assertRaisesRegex(InstallError, 'digest changed'):
            recover_transaction(self.mods, transaction.directory.name, expected_journal_sha256=old)
        lock = ModRootLock(self.mods)
        try:
            with self.assertRaisesRegex(RuntimeError, 'already owned'): self.recover(transaction)
        finally:
            lock.close()
        self.assertEqual(transaction.inspect()['phase'], 'cleanup_pending')

    def test_interrupted_recovery_resumes_from_observed_rename_outcomes(self):
        import expedition33.mod_install as implementation
        for failed_phase in ('recovery_restore_pending', 'rolled_back'):
            transaction = self.prepare()
            transaction.activate(lambda: True)
            writer = implementation._write_journal
            def fail(directory, state):
                if state['phase'] == failed_phase:
                    raise OSError('simulated journal write failure')
                return writer(directory, state)
            with patch.object(implementation, '_write_journal', fail):
                with self.assertRaisesRegex(OSError, 'write failure'): self.recover(transaction)
            result = self.recover(transaction)
            self.assertEqual(result['phase'], 'rolled_back')
            self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
            self.assertTrue((transaction.directory / 'rejected/helper.py').is_file())

    def test_committed_and_missing_backup_fail_without_file_changes(self):
        transaction = self.prepare()
        transaction.activate(lambda: True)
        transaction._record('committed')
        with self.assertRaisesRegex(InstallError, 'not an unresolved'): self.recover(transaction)
        transaction._record('installed')
        transaction.backup.rename(transaction.directory / 'displaced-backup')
        with self.assertRaisesRegex(InstallError, 'No original'): self.recover(transaction)
        self.assertTrue((self.target / 'helper.py').is_file())

    def test_cli_inspects_then_requires_digest_before_restoring(self):
        transaction = self.prepare()
        transaction.activate(lambda: True)
        script = Path(__file__).resolve().parents[1] / 'scripts/mod_recovery.py'
        def run(operation, *extra):
            return subprocess.run([sys.executable, '-I', '-S', '-B', str(script), operation,
                                   str(self.mods), transaction.directory.name, *extra],
                                  capture_output=True, text=True, timeout=10)
        inspected = run('inspect')
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        digest = json.loads(inspected.stdout)['journal_sha256']
        denied = run('restore')
        self.assertEqual(denied.returncode, 1)
        self.assertIn('requires', json.loads(denied.stdout)['error'])
        restored = run('restore', '--expected-journal-sha256', digest)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(json.loads(restored.stdout)['phase'], 'rolled_back')
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')

    def test_prepare_does_not_execute_or_change_installed_source_and_swap_retains_backup(self):
        transaction = self.prepare()
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
        calls = []
        def cleanup():
            calls.append('cleanup')
            self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
            self.assertFalse(transaction.backup.exists())
            return True
        result = transaction.activate(cleanup)
        self.assertEqual(calls, ['cleanup'])
        self.assertEqual(result['phase'], 'installed')
        self.assertTrue(result['target_exists'] and result['backup_exists'])
        self.assertFalse(result['prepared_exists'])
        self.assertEqual((transaction.backup / 'mod.py').read_text(), 'VERSION=1')
        self.assertEqual((self.target / 'helper.py').read_text(), 'VERSION=2')
        self.assertEqual(json.loads(Path(result['journal']).read_text())['phase'], 'installed')
        with self.assertRaisesRegex(InstallError, 'replayed'): transaction.activate(cleanup)
        self.assertEqual(calls, ['cleanup'])

    def test_cleanup_failure_never_moves_installed_folder(self):
        for result in (False, None, 1):
            transaction = self.prepare()
            with self.assertRaisesRegex(InstallError, 'confirm completion'):
                transaction.activate(lambda: result)
            self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
            self.assertFalse(transaction.backup.exists())
            self.assertEqual(transaction.inspect()['phase'], 'cleanup_pending')
            self.assertIn('error', transaction.inspect())

    def test_modified_prepared_bytes_abort_before_cleanup_or_move(self):
        transaction = self.prepare()
        (transaction.prepared / 'helper.py').write_text('VERSION=999')
        called = []
        with self.assertRaisesRegex(InstallError, 'bytes changed'):
            transaction.activate(lambda: called.append(True) or True)
        self.assertFalse(called)
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
        transaction = self.prepare()
        def cleanup():
            (transaction.prepared / 'new.py').write_text('')
            return True
        with self.assertRaisesRegex(InstallError, 'unexpected file'): transaction.activate(cleanup)
        self.assertFalse(transaction.backup.exists())

    def test_failed_second_rename_preserves_backup_and_candidate_without_replay(self):
        transaction = self.prepare()
        rename = Path.rename
        def fault(path, target):
            if path == transaction.prepared:
                raise OSError('simulated sharing violation')
            return rename(path, target)
        with patch.object(Path, 'rename', fault):
            with self.assertRaisesRegex(OSError, 'sharing violation'):
                transaction.activate(lambda: True)
        state = transaction.inspect()
        self.assertEqual(state['phase'], 'install_pending')
        self.assertFalse(state['target_exists'])
        self.assertTrue(state['backup_exists'] and state['prepared_exists'])
        recovered = inspect_transaction(self.mods, transaction.directory.name)
        self.assertEqual(recovered, state)
        self.assertEqual((transaction.backup / 'mod.py').read_text(), 'VERSION=1')
        with self.assertRaisesRegex(InstallError, 'replayed'): transaction.activate(lambda: True)

    def test_journal_paths_are_data_not_recovery_instructions(self):
        transaction = self.prepare()
        journal = transaction.directory / 'journal.json'
        state = json.loads(journal.read_text())
        state['backup'] = str(self.root.parent)
        journal.write_text(json.dumps(state))
        with self.assertRaisesRegex(InstallError, 'does not match'):
            inspect_transaction(self.mods, transaction.directory.name)
        with self.assertRaisesRegex(InstallError, 'Invalid transaction ID'):
            inspect_transaction(self.mods, '../outside')

    def test_invalid_hash_name_and_package_fail_before_installed_mod_changes(self):
        with self.assertRaises(ValueError): PreparedInstall(self.mods, 'Example', self.archive, '0' * 64)
        for name in ('../Example', '.', 'Example/sub'):
            with self.assertRaises(InstallError): PreparedInstall(self.mods, name, self.archive, self.digest)
        (self.source / '__init__.py').write_text('')
        data, candidate = build_bytes(self.source); self.archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'root __init__'):
            PreparedInstall(self.mods, 'Example', self.archive, candidate.sha256)
        self.assertEqual((self.target / 'mod.py').read_text(), 'VERSION=1')
