"""Bounded, immutable preflight of trusted mod archives. Does not install or run.

Archives contain mod.py at their root plus source/resources beneath it. Hashes
identify reviewed bytes; they are not signatures or a Python sandbox.
"""
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile

MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_FILE = 4 * 1024 * 1024
MAX_ENTRIES = 512
_DEVICE = re.compile(r'^(CON|CONIN\$|CONOUT\$|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])$', re.I)


class ArchiveError(ValueError):
    pass


def python_source_digest(inventory):
    """Hash sorted relative Python-path/content-digest pairs, excluding resources."""
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Candidate:
    sha256: str
    files: tuple[tuple[str, bytes], ...]

    def summary(self):
        return {'sha256': self.sha256, 'file_count': len(self.files),
                'python_package_sha256': python_source_digest({name: hashlib.sha256(data).hexdigest()
                    for name, data in self.files if name.endswith('.py')}),
                'expanded_bytes': sum(len(data) for _, data in self.files),
                'files': [{'path': name, 'size': len(data),
                           'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in self.files]}


def _parts(name):
    if not name or len(name) > 240 or '\\' in name:
        raise ArchiveError('Invalid archive path')
    parts = name.split('/')
    for part in parts:
        if (not part or part in ('.', '..') or part[-1] in ' .' or
                any(ord(c) < 32 or c in '<>:"|?*' for c in part) or
                _DEVICE.match(part.split('.')[0].rstrip(' '))):
            raise ArchiveError('Archive path is not a portable relative path: ' + repr(name))
        if part.casefold() in ('.git', '__pycache__') or part.lower().endswith(('.pyc', '.pyo')):
            raise ArchiveError('VCS metadata and bytecode are not mod source: ' + name)
    return parts


def inspect_bytes(data, expected_sha256):
    """Verify complete candidate before any installed mod is stopped or altered."""
    if type(data) is not bytes or len(data) > MAX_ARCHIVE:
        raise ArchiveError('Archive must be immutable bytes, at most 32 MiB')
    if (type(expected_sha256) is not str or len(expected_sha256) != 64 or
            any(c not in '0123456789abcdef' for c in expected_sha256)):
        raise ArchiveError('Supply a lowercase archive SHA256')
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ArchiveError('Archive SHA256 mismatch')
    files, paths, spellings, expanded = [], {}, {}, 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ENTRIES:
                raise ArchiveError('Archive must contain 1–512 entries')
            for entry in entries:
                # ZipInfo truncates at NUL; validate the original spelling too.
                if entry.orig_filename != entry.filename:
                    raise ArchiveError('Truncated archive path')
                directory = entry.is_dir()
                name = entry.filename[:-1] if directory else entry.filename
                parts = _parts(name)
                for i in range(1, len(parts) + 1):
                    prefix = '/'.join(parts[:i])
                    previous = spellings.setdefault(prefix.casefold(), prefix)
                    if previous != prefix:
                        raise ArchiveError('Case-colliding path component: ' + prefix)
                folded = name.casefold()
                if folded in paths:
                    raise ArchiveError('Duplicate or case-colliding archive path: ' + name)
                mode = (entry.external_attr >> 16) & 0xffff
                if entry.external_attr & 0x400:
                    raise ArchiveError('Windows reparse entries are unsupported')
                kind = stat.S_IFMT(mode)
                if kind not in (0, stat.S_IFDIR if directory else stat.S_IFREG):
                    raise ArchiveError('Archive links and special files are unsupported')
                if entry.flag_bits & 1:
                    raise ArchiveError('Encrypted mod archives are unsupported')
                paths[folded] = directory
                if directory:
                    if entry.file_size:
                        raise ArchiveError('Directory entry contains data')
                    continue
                expanded += entry.file_size
                if entry.file_size > MAX_FILE or expanded > MAX_EXPANDED:
                    raise ArchiveError('Archive expanded size exceeds limit')
                with archive.open(entry) as stream:
                    payload = stream.read(MAX_FILE + 1)
                if len(payload) != entry.file_size or len(payload) > MAX_FILE:
                    raise ArchiveError('Archive entry size mismatch')
                if name.endswith('.py'):
                    try:
                        compile(payload, '<mod archive>/' + name, 'exec', dont_inherit=True)
                    except (SyntaxError, ValueError) as error:
                        raise ArchiveError('Invalid Python source: ' + name + ': ' + str(error)) from None
                files.append((name, payload))
            for name in paths:
                components = name.split('/')
                if any(paths.get('/'.join(components[:i])) is False for i in range(1, len(components))):
                    raise ArchiveError('A file is also used as a parent directory')
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as error:
        raise ArchiveError('Unreadable mod archive: ' + str(error)) from None
    if not any(name == 'mod.py' for name, _ in files):
        raise ArchiveError('Archive requires root mod.py')
    return Candidate(digest, tuple(sorted(files)))


def read_candidate(path, expected_sha256):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_ARCHIVE + 1)
    return inspect_bytes(data, expected_sha256)


def build_bytes(directory):
    """Build a reproducible candidate from a trusted source folder, without installing."""
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ArchiveError('Mod source must be a directory')
    contents, expanded = [], 0
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if any(p.casefold() in ('.git', '__pycache__') for p in relative.parts):
            continue
        if path.suffix.lower() in ('.pyc', '.pyo'):
            continue
        if path.is_symlink() or path.is_junction():
            raise ArchiveError('Source links/junctions are unsupported: ' + str(relative))
        if path.is_dir():
            continue
        if not path.is_file():
            raise ArchiveError('Source must contain regular files')
        _parts(relative.as_posix())
        with path.open('rb') as stream:
            payload = stream.read(MAX_FILE + 1)
        expanded += len(payload)
        if len(payload) > MAX_FILE or expanded > MAX_EXPANDED or len(contents) >= MAX_ENTRIES:
            raise ArchiveError('Mod source exceeds archive limits')
        contents.append((relative.as_posix(), payload))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(contents):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, payload)
    data = stream.getvalue()
    return data, inspect_bytes(data, hashlib.sha256(data).hexdigest())
