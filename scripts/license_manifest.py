"""Fail-closed checks for reviewed runtime bytes and supplemental notices.

Integrity checks do not constitute legal clearance. Component review statuses,
including unresolved applicability, are preserved verbatim in the distribution.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from prepare_runtime import URL, SHA256

MANIFEST = 'licenses/runtime-dependencies.json'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _path(value, prefix=None):
    if not isinstance(value, str) or '\\' in value or ':' in value:
        raise ValueError(f'Invalid manifest path: {value!r}')
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError(f'Invalid manifest path: {value!r}')
    if prefix and (not value.startswith(prefix + '/') or value == MANIFEST):
        raise ValueError(f'Notice must be inside {prefix}: {value!r}')
    return value


def _hashes(mapping, prefix=None):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Reviewed file hash inventory must not be empty')
    for name, digest in mapping.items():
        _path(name, prefix)
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError(f'Invalid SHA256 for {name}')


def _schema(manifest):
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported runtime notice manifest schema')
    runtime = manifest.get('runtime', {})
    version = URL.split('/')[-2]
    if (runtime.get('version') != version or runtime.get('archive_url') != URL
            or runtime.get('archive_sha256') != SHA256):
        raise ValueError('Runtime pin changed: explicit notice review required')
    if not runtime.get('source_revision'):
        raise ValueError('Missing reviewed CPython source revision')
    _hashes(runtime.get('files'))
    _hashes(manifest.get('notices'), 'licenses')
    components = manifest.get('components')
    if not isinstance(components, list) or not components:
        raise ValueError('Missing component review inventory')
    ids = set()
    for component in components:
        if not all(component.get(k) for k in ('id', 'version', 'status')):
            raise ValueError('Incomplete component review identity/status')
        if component.get('reviewed_version') != component['version']:
            raise ValueError(f"Component version changed without notice review: {component['id']}")
        if component['id'] in ids:
            raise ValueError('Duplicate component identity')
        ids.add(component['id'])
        paths = component.get('notice_paths')
        if not isinstance(paths, list):
            raise ValueError('Component notice_paths must be explicit')
        if not paths and component['status'] in ('verified-notices', 'verified-applicable'):
            raise ValueError(f"Verified component lacks notices: {component['id']}")
        for path in paths:
            if path not in manifest['notices']:
                raise ValueError(f'Component references untracked notice: {path}')


def _files(root):
    result = {}
    if root.is_symlink() or root.is_junction():
        raise ValueError(f'Link not permitted in reviewed payload: {root}')
    for path in root.rglob('*'):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f'Link not permitted in reviewed payload: {path}')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
    return result


def validate_source(root):
    """Check inputs before creating a staging directory; return reviewed manifest."""
    root = Path(root)
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf8'))
    _schema(manifest)
    runtime = _files(root / 'runtime')
    if set(runtime) != set(manifest['runtime']['files']):
        raise ValueError('Runtime file inventory changed: explicit review required')
    for name, path in runtime.items():
        if _sha(path.read_bytes()) != manifest['runtime']['files'][name]:
            raise ValueError(f'Unreviewed runtime bytes: {name}')
    licenses = {'licenses/' + name: path for name, path in _files(root / 'licenses').items()}
    if set(licenses) != set(manifest['notices']) | {MANIFEST}:
        raise ValueError('License file inventory differs from reviewed manifest')
    for name, digest in manifest['notices'].items():
        data = licenses[name].read_bytes()
        if not data.strip() or _sha(data) != digest:
            raise ValueError(f'Missing, empty or changed notice: {name}')
    return manifest


def verify_archive(archive_path, reviewed_manifest):
    """Verify the actual ZIP, including missing/extra entries and notice hashes."""
    _schema(reviewed_manifest)
    with zipfile.ZipFile(archive_path) as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        for name in names:
            _path(name)
        embedded = json.loads(archive.read('SDK/' + MANIFEST))
        if embedded != reviewed_manifest:
            raise ValueError('Packaged manifest differs from reviewed input')
        expected = {'SDK/runtime/' + name: digest
                    for name, digest in embedded['runtime']['files'].items()}
        expected.update({'SDK/' + name: digest for name, digest in embedded['notices'].items()})
        actual = {name for name in names if name.startswith(('SDK/runtime/', 'SDK/licenses/'))}
        if actual != set(expected) | {'SDK/' + MANIFEST}:
            raise ValueError('Archive omits or adds reviewed runtime/license files')
        for name, digest in expected.items():
            data = archive.read(name)
            if not data or _sha(data) != digest:
                raise ValueError(f'Archive runtime/notice checksum mismatch: {name}')
    return {'runtime_files': len(embedded['runtime']['files']),
            'notice_files': len(embedded['notices']), 'verified': True}
