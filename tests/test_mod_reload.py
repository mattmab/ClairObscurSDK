import hashlib
import os
import py_compile
import sys
import unittest
from unittest.mock import Mock

import test_mods
from test_mods import FakeSession
from expedition33.mods import ModLoader, ModError
from expedition33.management import ModDefinition


class ReloadTests(unittest.TestCase):
    setUp = test_mods.ModTests.setUp
    tearDown = test_mods.ModTests.tearDown
    source = test_mods.ModTests.source
    def specimen(self, value=1, suffix=''):
        self.source('class Mod:\n value = ' + str(value) + '\n'
                    ' def enable(self, session):\n'
                    '  session.actions.register("specimen.value", lambda: self.value, mutates=False)\n'
                    ' def disable(self): pass\n' + suffix)
        return hashlib.sha256((self.root / 'Specimen/mod.py').read_bytes()).hexdigest()

    def test_reload_changes_actions_revokes_scope_and_ignores_stale_bytecode(self):
        self.specimen(1)
        path = self.root / 'Specimen/mod.py'
        py_compile.compile(str(path), doraise=True)
        original_stat = path.stat()
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            old_key, old_mod, old_scope = loader._loaded['Specimen']
            old_action = loader.actions.actions['specimen.value']['callback']
            old_selection = loader.registry.select('specimen')
            digest = self.specimen(2)
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            result = loader.reload('Specimen', expected_sha256=digest)
            self.assertTrue(result['changed'] and result['enabled'])
            self.assertEqual(result['sha256'], digest)
            self.assertEqual(loader.actions.dispatch({'op':'action', 'name':'specimen.value'})['result'], 2)
            self.assertNotIn(old_key, sys.modules)
            self.assertIsNot(loader._loaded['Specimen'][1], old_mod)
            with self.assertRaisesRegex(RuntimeError, 'scope is closed'): old_action()
            with self.assertRaisesRegex(RuntimeError, 'Stale'): loader.registry.view(old_selection)
            self.assertEqual(loader.status()[0].source_sha256, digest)

    def test_preflight_failure_and_unchanged_skip_leave_original_enabled(self):
        digest = self.specimen()
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            record = loader._loaded['Specimen']
            record[1].disable = Mock()
            result = loader.reload('Specimen', expected_sha256=digest, changed_only=True)
            self.assertFalse(result['changed'])
            for bad in ('0' * 64, None, True, 'A' * 64):
                with self.assertRaises(ModError): loader.reload('Specimen', expected_sha256=bad)
            self.source('invalid python syntax !')
            bad_digest = hashlib.sha256((self.root / 'Specimen/mod.py').read_bytes()).hexdigest()
            with self.assertRaisesRegex(ModError, 'compile'):
                loader.reload('Specimen', expected_sha256=bad_digest)
            record[1].disable.assert_not_called()
            self.assertIs(loader._loaded['Specimen'], record)
            self.assertTrue(loader.status()[0].enabled)

    def test_captured_source_cannot_change_during_cleanup(self):
        self.specimen()
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            loader._loaded['Specimen'][1].disable = lambda: self.specimen(3)
            digest = self.specimen(2)
            loader.reload('Specimen', expected_sha256=digest)
            self.assertEqual(loader._loaded['Specimen'][1].value, 2)
            self.assertEqual(loader.status()[0].source_sha256, digest)

    def test_cleanup_error_stops_replacement_and_import_failure_has_no_rollback(self):
        self.specimen()
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            record = loader._loaded['Specimen']
            record[1].disable = Mock(side_effect=RuntimeError('uncertain'))
            digest = self.specimen(2)
            with self.assertRaisesRegex(ModError, 'uncertain'):
                loader.reload('Specimen', expected_sha256=digest)
            self.assertIs(loader._loaded['Specimen'], record)
            self.assertFalse(loader.actions.actions)
            with self.assertRaisesRegex(ModError, 'restart the controller'):
                loader.reload('Specimen', expected_sha256=digest)
            record[1].disable.assert_called_once()
        self.specimen()
        with ModLoader(self.root, session=FakeSession()) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            digest = self.specimen(2, 'raise SystemExit("import")\n')
            with self.assertRaisesRegex(ModError, 'load failed: SystemExit'):
                loader.reload('Specimen', expected_sha256=digest)
            self.assertFalse(loader.status())
            self.assertFalse(loader.actions.actions)

    def test_disabled_mod_stays_disabled_and_core_reload_is_rejected(self):
        digest = self.specimen()
        with ModLoader(self.root) as loader:
            loader.load('Specimen')
            self.assertFalse(loader.reload('Specimen', expected_sha256=digest)['enabled'])
            self.assertFalse(FakeSession.instances)
            loader.registry._entries['specimen'].definition = ModDefinition('specimen', 'Core', protected=True)
            with self.assertRaisesRegex(ModError, 'protected'):
                loader.reload('Specimen', expected_sha256=digest)

    def test_sole_owned_session_and_python_namespace_survive_reload(self):
        digest = self.specimen()
        with ModLoader(self.root) as loader:
            loader.load('Specimen'); loader.enable('Specimen')
            shared = loader._session
            shared.console.dispatcher.namespace['persistent_value'] = 42
            loader.reload('Specimen', expected_sha256=digest)
            self.assertIs(loader._session, shared)
            self.assertFalse(shared.closed)
            self.assertEqual(shared.console.dispatcher.namespace['persistent_value'], 42)
            self.assertEqual(len(FakeSession.instances), 1)
