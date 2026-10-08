import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from expedition33.settings import SettingsError, SettingsStore, SettingsVersionError


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'management.json'

    def test_roundtrip_shared_records_and_defensive_copies(self):
        store = SettingsStore(self.path)
        record = {'enabled': True, 'options': {'scale': 1.2}, 'keybinds': {'open': 'F6'}}
        store.save('management', record)
        store.save('introspection', {'options': {'depth': 2}})
        record['options']['scale'] = 999
        loaded = SettingsStore(self.path)
        self.assertEqual(loaded.revision, 2)
        self.assertEqual(loaded.get('management')['options']['scale'], 1.2)
        result = loaded.get('management'); result['options']['scale'] = 0
        self.assertEqual(loaded.get('management')['options']['scale'], 1.2)
        self.assertEqual(loaded.get('introspection')['options']['depth'], 2)

    def test_corrupt_primary_recovers_previous_and_preserves_raw(self):
        store = SettingsStore(self.path)
        store.save('example', {'options': {'value': 1}})
        store.save('example', {'options': {'value': 2}})
        self.path.write_bytes(b'broken primary')
        recovered = SettingsStore(self.path)
        self.assertIn('last-good', recovered.recovery)
        self.assertEqual(recovered.get('example')['options']['value'], 1)
        recovered.save('example', {'options': {'value': 3}})
        self.assertEqual(recovered.preserved_corrupt.read_bytes(), b'broken primary')
        self.assertEqual(SettingsStore(self.path).get('example')['options']['value'], 3)

    def test_future_version_is_not_replaced_by_backup(self):
        store = SettingsStore(self.path); store.save('example', {})
        future = {'version': 2, 'revision': 10, 'mods': {}}
        self.path.write_text(json.dumps(future))
        with self.assertRaises(SettingsVersionError): SettingsStore(self.path)
        self.assertEqual(json.loads(self.path.read_text()), future)

    def test_stale_writer_and_existing_lock_rejected(self):
        first, second = SettingsStore(self.path), SettingsStore(self.path)
        first.save('first', {})
        with self.assertRaisesRegex(SettingsError, 'changed on disk'): second.save('second', {})
        first.lock.write_text('existing writer')
        with self.assertRaisesRegex(SettingsError, 'lock'): first.save('first', {})
        self.assertEqual(first.lock.read_text(), 'existing writer')
        self.assertEqual(SettingsStore(self.path).revision, 1)

    def test_failed_replace_does_not_publish_memory_state(self):
        store = SettingsStore(self.path); store.save('example', {'enabled': False})
        replace = os.replace
        def fail_primary(source, destination):
            if Path(destination) == self.path: raise OSError('simulated disk failure')
            return replace(source, destination)
        with patch('expedition33.settings.os.replace', side_effect=fail_primary):
            with self.assertRaises(OSError): store.save('example', {'enabled': True})
        self.assertFalse(store.get('example')['enabled'])
        self.assertFalse(SettingsStore(self.path).get('example')['enabled'])
        self.assertFalse(store.lock.exists())
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_invalid_values_never_touch_disk(self):
        store = SettingsStore(self.path)
        invalid = ({'enabled': 1}, {'options': {'number': float('nan')}},
                   {'keybinds': {'open': 5}}, {'options': {'../escape': 2}}, {'unknown': 1})
        for record in invalid:
            with self.assertRaises(SettingsError): store.save('example', record)
        self.assertFalse(self.path.exists())
        with self.assertRaises(SettingsError): store.save('../example', {})

    def test_duplicate_keys_and_corruption_without_backup_rejected(self):
        self.path.write_text('{"version":1,"version":1,"revision":0,"mods":{}}')
        with self.assertRaises(SettingsError): SettingsStore(self.path)
        self.assertIn('"version":1,"version":1', self.path.read_text())


if __name__ == '__main__': unittest.main()
