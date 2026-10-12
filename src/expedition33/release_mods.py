"""Bounded startup extraction of trusted SDK_Mods archives, before mod imports.

The caller holds the install-root controller lock. Settings live outside this
generated tree. Archives are Python code, not sandboxed or signed plugins.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from .mod_archive import inspect_bytes, MAX_ARCHIVE


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


def materialize(archives, sdk_root):
    archives, root = Path(archives), Path(sdk_root).resolve(strict=True)
    _plain_tree(archives)
    files = sorted(archives.glob('*.sdkmod'))
    if not 1 <= len(files) <= 64:
        raise ValueError('Expected between 1 and 64 mod archives')
    payloads, identities, total = [], {}, 0
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
        candidate = inspect_bytes(payload, digest)
        total += sum(len(data) for _, data in candidate.files)
        if total > 256 * 1024 * 1024:
            raise ValueError('Combined mod archives exceed 256 MiB')
        identities[name.casefold()] = digest
        payloads.append((name, candidate))
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
