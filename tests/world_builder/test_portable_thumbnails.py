import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('import_thumbnails', Path(__file__).resolve().parents[2] / 'scripts/import_world_builder_thumbnails.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PortableThumbnailTests(unittest.TestCase):
    def test_rekeys_for_timestamp_and_preserves_local_image(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2] / 'build') as directory:
            root = Path(directory)
            game = root / 'game'
            executable = game / 'Sandfall/Binaries/Win64/SandFall-Win64-Shipping.exe'
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'fake test game')
            pack = root / 'pack'
            (pack / 'images').mkdir(parents=True)
            data = b'test image payload'
            digest = hashlib.sha256(data).hexdigest()
            (pack / 'images' / (digest + '.png')).write_bytes(data)
            asset = '/Game/Test.Test'
            manifest = dict(version=1, game=m.identity(game), images={asset: digest})
            (pack / 'thumbnails.json').write_text(json.dumps(manifest))
            old_key = m.build_key(game)
            os.utime(executable, ns=(1_000_000_000, 1_000_000_000))
            self.assertNotEqual(old_key, m.build_key(game))
            self.assertEqual(m.import_pack(pack, game)['imported'], 1)
            key = hashlib.sha256((m.build_key(game) + ':neutral-v1b:' + asset).encode()).hexdigest()
            target = game / 'SDK/settings/E33WorldBuilder/cache/neutral-v1' / (key + '.png')
            self.assertEqual(target.read_bytes(), data)
            target.write_bytes(b'local replacement')
            self.assertEqual(m.import_pack(pack, game)['already_present'], 1)
            self.assertEqual(target.read_bytes(), b'local replacement')
            (pack / 'images' / (digest + '.png')).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.import_pack(pack, game)
            executable.write_bytes(b'different build')
            with self.assertRaisesRegex(ValueError, 'different game build'):
                m.import_pack(pack, game)


if __name__ == '__main__':
    unittest.main()
