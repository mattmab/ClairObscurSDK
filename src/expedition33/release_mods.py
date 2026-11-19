"""Stage trusted mod payloads in a bounded cache before mod imports.

The caller holds the install-root controller lock. Settings live outside this
generated tree. Archives are Python code, not sandboxed or signed plugins.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from .mod_archive import (
    Candidate, MAX_ARCHIVE, MAX_ENTRIES, MAX_EXPANDED, MAX_FILE, _parts, inspect_bytes,
)

# Resource-bearing story packs already permit 768 MiB individually. The old
# 256 MiB aggregate rejected valid packs before their code could even load.
# Keep a finite aggregate budget, including all decoded resources and code.
MAX_COMBINED_EXPANDED = 1024 * 1024 * 1024


def _plain_tree(path):
    if path.is_symlink() or path.is_junction():
        raise ValueError('Redirected mod cache is not allowed')
    if path.exists():
        for child in path.rglob('*'):
            if child.is_symlink() or child.is_junction():
                raise ValueError('Redirected mod cache entry is not allowed')


def _remove_cache(path, root):
    if path.parent != root or not (path / '.sdk-generated.json').is_file():
        raise ValueError('Refusing to remove an unowned cache')
    _plain_tree(path)
    shutil.rmtree(path)


def read_bundled_candidate(sdk_root, row):
    """Read only the reviewed files belonging to a loose bundled mod."""
    folder, entries = row['folder'], row['files']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', folder):
        raise ValueError('Invalid bundled mod name')
    if not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError('Invalid bundled mod file count')
    bundles = Path(sdk_root) / 'bundled-mods'
    source = bundles / folder
    if bundles.is_symlink() or bundles.is_junction():
        raise ValueError('Redirected bundled mod root')
    _plain_tree(source)
    files, expanded, seen = [], 0, set()
    for entry in entries:
        name = entry['path']
        _parts(name)
        path = source / name
        if name.casefold() in seen or not path.is_file():
            raise ValueError('Duplicate or missing bundled mod file: ' + name)
        seen.add(name.casefold())
        with path.open('rb') as stream:
            data = stream.read(MAX_FILE + 1)
        expanded += len(data)
        if len(data) > MAX_FILE or expanded > MAX_EXPANDED:
            raise ValueError('Bundled mod exceeds file or expanded size limit')
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Bundled mod file changed: ' + name)
        files.append((name, data))
    if not any(name == 'mod.py' for name, _ in files):
        raise ValueError('Bundled mod requires root mod.py')
    return Candidate(row['sha256'], tuple(sorted(files)))


def materialize(archives, sdk_root, *, bundled_rows=()):
    archives, root = Path(archives), Path(sdk_root).resolve(strict=True)
    _plain_tree(archives)
    bundled_names = {row['folder'].casefold() for row in bundled_rows}
    if len(bundled_names) != len(bundled_rows):
        raise ValueError('Duplicate bundled mod name')
    # A loose core package may be extracted over earlier archived core mods.
    files = sorted(path for path in archives.glob('*.sdkmod') if path.stem.casefold() not in bundled_names)
    if not 1 <= len(files) + len(bundled_rows) <= 64:
        raise ValueError('Expected between 1 and 64 mod archives or loose bundled mods')
    payloads, identities, total = [], {}, 0

    def add_payload(name, candidate):
        nonlocal total
        total += sum(len(data) for _, data in candidate.files)
        if total > MAX_COMBINED_EXPANDED:
            raise ValueError('Combined expanded mod payloads exceed '+str(MAX_COMBINED_EXPANDED)+' bytes')
        identities[name.casefold()] = candidate.sha256
        payloads.append((name, candidate))

    for row in bundled_rows:
        add_payload(row['folder'], read_bundled_candidate(root, row))
    for file in files:
        name = file.stem
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name):
            raise ValueError('Invalid mod archive name')
        if name.casefold() in identities:
            raise ValueError('Duplicate mod archive name')
        with file.open('rb') as stream:
            payload = stream.read(MAX_ARCHIVE + 1)
        if len(payload) > MAX_ARCHIVE:
            raise ValueError('Mod archive exceeds size limit')
        digest = hashlib.sha256(payload).hexdigest()
        add_payload(name, inspect_bytes(payload, digest))
    target, backup = root / 'mods', root / 'mods.previous'
    # Recover an interrupted swap, never run a partly extracted tree.
    if backup.exists():
        if target.exists():
            _remove_cache(backup, root)
        else:
            _plain_tree(backup)
            backup.rename(target)
    if target.exists():
        _plain_tree(target)
        if not (target / '.sdk-generated.json').is_file():
            raise ValueError('SDK/mods contains unmanaged files; refusing replacement')
    staged = Path(tempfile.mkdtemp(prefix='mods-stage-', dir=root))
    (staged / '.sdk-generated.json').write_text(json.dumps(identities), encoding='utf8')
    try:
        for name, candidate in payloads:
            for relative, data in candidate.files:
                destination = staged / name / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(data)
        if target.exists():
            target.rename(backup)
        try:
            staged.rename(target)
        except BaseException:
            if backup.exists():
                backup.rename(target)
            raise
        if backup.exists():
            _remove_cache(backup, root)
    finally:
        if staged.exists():
            _remove_cache(staged, root)
    return target
