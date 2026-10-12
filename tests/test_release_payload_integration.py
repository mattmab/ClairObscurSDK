"""Archive refresh must preserve saved mod choices without a running game."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from expedition33.mod_archive import build_bytes
from expedition33.mods import ModLoader
from expedition33.release_mods import materialize
from expedition33.settings import SettingsStore
from test_mods import FakeSession


class ReleasePayloadIntegration(unittest.TestCase):
    def test_enabled_and_disabled_choices_survive_archive_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdk = root / 'SDK'
            sdk.mkdir()
            archives = root / 'SDK_Mods'
            archives.mkdir()
            source = root / 'source'
            source.mkdir()
            (source / 'mod.py').write_text(
                'class Mod:\n'
                ' def enable(self, session): self.active = True\n'
                ' def disable(self): self.active = False\n', encoding='utf8')
            data, _ = build_bytes(source)
            for name in ('One', 'Two'):
                (archives / (name + '.sdkmod')).write_bytes(data)
            settings = sdk / 'settings/management.json'
            with patch('expedition33.mods.Session', FakeSession):
                cache = materialize(archives, sdk)
                with ModLoader(cache, settings=SettingsStore(settings)) as loader:
                    for name in ('One', 'Two'):
                        loader.load(name)
                    loader.registry.set_enabled(loader.registry.select('one'), True)
                    loader.registry.set_enabled(loader.registry.select('two'), False)
                saved = settings.read_bytes()
                # Updating archive bytes rebuilds the extracted tree only.
                (source / 'resource.txt').write_text('updated payload', encoding='utf8')
                data, _ = build_bytes(source)
                (archives / 'One.sdkmod').write_bytes(data)
                cache = materialize(archives, sdk)
                self.assertEqual(settings.read_bytes(), saved)
                self.assertEqual((cache / 'One/resource.txt').read_text(), 'updated payload')
                with ModLoader(cache, settings=SettingsStore(settings)) as loader:
                    self.assertEqual(loader.registry.restore_enabled(), {})
                    loader.load('Two')
                    states = {row.name: row.enabled for row in loader.status()}
                    self.assertEqual(states, {'One': True, 'Two': False})
                self.assertEqual(settings.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
