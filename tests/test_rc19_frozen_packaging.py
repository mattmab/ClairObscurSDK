import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from package_rc19 import MODS, build, read_input, write_zip


class FrozenReleaseTests(unittest.TestCase):
    def test_manifest_hash_failure_creates_no_release_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stage=root/'stage';sdk=stage/'SDK';sdk.mkdir(parents=True)
            name='build/runtime-session-cinematic-v245/runtime_session_cinematic_v245.dll'
            native=sdk/name;native.parent.mkdir(parents=True);native.write_bytes(b'changed after qualification')
            (sdk/'release-manifest.json').write_text(json.dumps(dict(
                version='qualification',sdk_files={name:'0'*64},
                mods=[dict(archive=mod+'.sdkmod') for mod in MODS])))
            output=root/'release'
            with self.assertRaisesRegex(ValueError,'hash mismatch'):build(stage,output)
            self.assertFalse(output.exists())

    def test_nested_archive_cannot_hide_personal_settings(self):
        nested=io.BytesIO()
        with zipfile.ZipFile(nested,'w') as archive:
            archive.writestr('settings/local.json','{}')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Excluded release path'):
                write_zip(Path(directory)/'bad.zip',{'SDK_Mods/Example.sdkmod':nested.getvalue()})

    def test_manifest_path_cannot_escape_to_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'outside.txt').write_text('private')
            stage=root/'stage';stage.mkdir()
            with self.assertRaises(ValueError):read_input(stage,'../outside.txt')
