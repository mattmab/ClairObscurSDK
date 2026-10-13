import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from license_manifest import MANIFEST, validate_source, verify_archive
from prepare_runtime import URL, SHA256
import package_release_candidate


def digest(data):
    return hashlib.sha256(data).hexdigest()


class LicenseManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('runtime/python.exe', b'reviewed runtime fixture')
        self.write('licenses/Expat/COPYING', b'copyright and permission fixture\n')
        self.manifest = {
            'schema': 1,
            'runtime': {'version': URL.split('/')[-2], 'archive_url': URL,
                        'archive_sha256': SHA256, 'source_revision': 'reviewed-source',
                        'files': {'python.exe': digest(b'reviewed runtime fixture')}},
            'notices': {'licenses/Expat/COPYING': digest(b'copyright and permission fixture\n')},
            'components': [{'id': 'expat', 'version': 'fixture', 'reviewed_version': 'fixture',
                            'status': 'unresolved applicability',
                            'notice_paths': ['licenses/Expat/COPYING']}],
        }
        self.save()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def save(self):
        self.write(MANIFEST, json.dumps(self.manifest).encode())

    def archive(self, omitted=None, changed=None):
        path = self.root / 'candidate.zip'
        with zipfile.ZipFile(path, 'w') as out:
            for item in self.root.rglob('*'):
                if item.is_file() and item != path:
                    name = item.relative_to(self.root).as_posix()
                    if name != omitted:
                        out.writestr('SDK/' + name, (changed or {}).get(name, item.read_bytes()))
        return path

    def test_review_status_is_not_mistaken_for_clearance(self):
        manifest = validate_source(self.root)
        result = verify_archive(self.archive(), manifest)
        self.assertTrue(result['verified'])
        self.assertEqual(manifest['components'][0]['status'], 'unresolved applicability')

    def test_missing_empty_changed_notice_rejected(self):
        path = self.root / 'licenses/Expat/COPYING'
        for data in (None, b'', b' ', b'changed copyright'):
            with self.subTest(data=data):
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
                with self.assertRaises(ValueError):
                    validate_source(self.root)

    def test_runtime_upgrade_requires_review(self):
        baseline = copy.deepcopy(self.manifest)
        for field, value in [('version', '3.14.0'), ('archive_url', 'https://example.com/python.zip'),
                             ('archive_sha256', '0' * 64)]:
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(baseline)
                self.manifest['runtime'][field] = value
                self.save()
                with self.assertRaises(ValueError):
                    validate_source(self.root)

    def test_component_version_change_requires_review(self):
        self.manifest['components'][0]['version'] = 'unreviewed upgrade'
        self.save()
        with self.assertRaisesRegex(ValueError, 'version changed'):
            validate_source(self.root)

    def test_verified_components_require_notices(self):
        component = self.manifest['components'][0]
        component['notice_paths'] = []
        for status in ('verified-notices', 'verified-applicable'):
            with self.subTest(status=status):
                component['status'] = status
                self.save()
                with self.assertRaisesRegex(ValueError, 'lacks notices'):
                    validate_source(self.root)
        component['status'] = 'not-applicable'
        self.save()
        validate_source(self.root)

    def test_runtime_byte_changes_and_extra_files_rejected(self):
        self.write('runtime/python.exe', b'upgrade')
        with self.assertRaises(ValueError):
            validate_source(self.root)
        self.write('runtime/python.exe', b'reviewed runtime fixture')
        self.write('runtime/new.dll', b'new dependency')
        with self.assertRaises(ValueError):
            validate_source(self.root)

    def test_path_traversal_and_untracked_component_notices_rejected(self):
        for path in ('../LICENSE', '/absolute', 'licenses/../outside', 'licenses\\notice', 'C:/notice'):
            with self.subTest(path=path):
                self.manifest['notices'] = {path: 'a' * 64}
                self.save()
                with self.assertRaises(ValueError):
                    validate_source(self.root)

    def test_final_zip_missing_or_changed_notice_rejected(self):
        reviewed = validate_source(self.root)
        with self.assertRaises(ValueError):
            verify_archive(self.archive(omitted='licenses/Expat/COPYING'), reviewed)
        with self.assertRaises(ValueError):
            verify_archive(self.archive(changed={'licenses/Expat/COPYING': b'altered'}), reviewed)

    def test_embedded_manifest_cannot_self_authorize_changed_notice(self):
        reviewed = validate_source(self.root)
        self.manifest['notices']['licenses/Expat/COPYING'] = digest(b'changed')
        self.save()
        with self.assertRaises(ValueError):
            verify_archive(self.archive(changed={'licenses/Expat/COPYING': b'changed'}), reviewed)

    def test_packager_copies_notices_and_verifies_actual_zip(self):
        for name in ('src/expedition33/__init__.py', 'scripts/run_release_sdk.py',
                     'scripts/sdk_command.py', 'docs/INSTALLABLE_RELEASE.md', 'LICENSE',
                     'THIRD_PARTY_NOTICES.md',
                     'build/release/research-probe-viewer-v2/research_probe.exe',
                     'build/release/runtime-session-viewer-v2/runtime_session_viewer_v2.dll',
                     'build/bootstrap/version.dll', 'mods/SDKManagement/mod.py',
                     'mods/IntrospectionHarness/mod.py', 'mods/LiveObjectViewer/mod.py'):
            self.write(name, b'# fixture\n')
        original = package_release_candidate.ROOT
        self.addCleanup(setattr, package_release_candidate, 'ROOT', original)
        package_release_candidate.ROOT = self.root
        result = package_release_candidate.build(self.root / 'output', 'notice-test')
        self.assertTrue(result['license_manifest_verification']['verified'])
        self.assertEqual(result['mods'], 3)
        with zipfile.ZipFile(result['archive']) as archive:
            self.assertIn('SDK_Mods/LiveObjectViewer.sdkmod', archive.namelist())
            self.assertIn('SDK/build/runtime-session-viewer-v2/runtime_session_viewer_v2.dll', archive.namelist())
            self.assertEqual(archive.read('SDK/licenses/Expat/COPYING'),
                             b'copyright and permission fixture\n')
        self.write('runtime/new.dll', b'new')
        with self.assertRaises(ValueError):
            package_release_candidate.build(self.root / 'rejected', 'notice-test')
        self.assertFalse((self.root / 'rejected').exists())


if __name__ == '__main__':
    unittest.main()
