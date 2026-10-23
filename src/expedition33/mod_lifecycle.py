"""Pre-import lifecycle declaration for trusted mods; not a Python sandbox.

Absent metadata preserves legacy world-deferred import. An early declaration
certifies only import, construction, management and optional prepare safety;
it neither enables the mod nor authorizes world UObject access.
"""
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_LIFECYCLE_BYTES = 4096
_NAME = 'lifecycle.json'


class LifecycleMetadataError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LifecycleMetadataError('Duplicate lifecycle field: ' + key)
        result[key] = value
    return result


@dataclass(frozen=True)
class LifecyclePolicy:
    prepare_at_startup: bool = False
    version: int | None = None
    world_uobject_access: bool = False


def parse_lifecycle(data):
    """Parse captured immutable bytes, never imports or touches a process."""
    if data is None:
        return LifecyclePolicy()
    if type(data) is not bytes or not data or len(data) > MAX_LIFECYCLE_BYTES:
        raise LifecycleMetadataError('lifecycle.json must contain 1–4096 immutable bytes')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise LifecycleMetadataError('Invalid lifecycle.json: ' + str(error)) from None
    if type(value) is not dict or set(value) != {'version', 'prepare_at_startup', 'world_uobject_access'}:
        raise LifecycleMetadataError('lifecycle.json requires exactly version, prepare_at_startup and world_uobject_access')
    if type(value['version']) is not int or value['version'] != 1:
        raise LifecycleMetadataError('Unsupported lifecycle version; expected integer 1')
    if type(value['prepare_at_startup']) is not bool:
        raise LifecycleMetadataError('prepare_at_startup must be bool')
    if value['world_uobject_access'] is not False:
        raise LifecycleMetadataError('Process preparation must declare world_uobject_access false')
    return LifecyclePolicy(value['prepare_at_startup'], 1, False)


def _digest(package_digest, metadata):
    # Domain separation and explicit absence: marker changes participate in reload
    # identity even though PackageSources.sha256 hashes Python sources only.
    return hashlib.sha256(b'e33-lifecycle-v1\0' + package_digest.encode('ascii') +
                          (b'\0absent' if metadata is None else b'\0present\0' + metadata)).hexdigest()


@dataclass(frozen=True)
class LifecycleCapture:
    policy: LifecyclePolicy
    metadata: bytes | None
    package_sha256: str
    lifecycle_sha256: str
    sources: object = field(repr=False, compare=False)


def _read_marker(root):
    path = root / _NAME
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None, None
    if path.is_symlink() or path.is_junction() or not stat.S_ISREG(before.st_mode):
        raise LifecycleMetadataError('lifecycle.json must be a regular, non-link file')
    if path.resolve(strict=True).parent != root:
        raise LifecycleMetadataError('lifecycle.json escapes mod directory')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(MAX_LIFECYCLE_BYTES + 1)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    # Windows path stat and handle fstat expose differing legacy ctime values.
    # Compare stable file identity/size/write time, and exact bytes across capture.
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if not (signature(before) == signature(opened) == signature(finished) == signature(after)):
        raise LifecycleMetadataError('lifecycle.json changed during capture')
    parse_lifecycle(data)
    return data, signature(after)


def capture_package(entry_path, entry_code, entry_digest, *, package_factory=None):
    """Capture marker around existing PackageSources, before any module executes.

    Pass the exact captured mod.py code/digest from ModLoader._read_source.
    Consumers execute capture.sources, never recapture/reimport for activation.
    """
    if package_factory is None:
        from .mod_imports import PackageSources
        package_factory = PackageSources
    path = Path(entry_path)
    if path.is_symlink() or path.is_junction() or path.parent.is_symlink() or path.parent.is_junction():
        raise LifecycleMetadataError('Linked mod roots or entrypoints are unsupported')
    root = path.parent.resolve(strict=True)
    before, signature = _read_marker(root)
    # Detect entry changes between the loader's source read and this capture.
    def check_entry():
        with path.open('rb') as stream:
            source = stream.read(4 * 1024 * 1024 + 1)
        if len(source) > 4 * 1024 * 1024 or hashlib.sha256(source).hexdigest() != entry_digest:
            raise LifecycleMetadataError('mod.py changed before lifecycle capture completed')
    check_entry()
    sources = package_factory(path, entry_code, entry_digest)
    check_entry()
    after, after_signature = _read_marker(root)
    if before != after or signature != after_signature:
        raise LifecycleMetadataError('lifecycle.json changed while capturing Python sources')
    return LifecycleCapture(parse_lifecycle(before), before, sources.sha256,
                            _digest(sources.sha256, before), sources)


def policy_from_candidate(candidate):
    """Read only an already bounded/hash-verified mod_archive.Candidate snapshot."""
    entries = [(name, data) for name, data in candidate.files if name.casefold() == _NAME]
    if len(entries) > 1 or entries and entries[0][0] != _NAME:
        raise LifecycleMetadataError('Use one root lifecycle.json with exact spelling')
    return parse_lifecycle(entries[0][1] if entries else None)


@dataclass(frozen=True, slots=True)
class PreparationContext:
    """Static facts only: no session, transport, memory, scope or UObject APIs."""
    sdk_version: str
    mod_name: str
    package_sha256: str

    def __post_init__(self):
        if any(type(v) is not str or not v or len(v) > 256 for v in
               (self.sdk_version, self.mod_name, self.package_sha256)):
            raise ValueError('Preparation facts must be nonempty bounded strings')
        if len(self.package_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.package_sha256):
            raise ValueError('Preparation package SHA256 must be lowercase hex')


class PreparationOnce:
    """Small per-loaded-record guard, not another loader or lifecycle framework.

    The loaded record owns this guard alongside its retained module/instance.
    Failed prepare is never retried automatically; activation uses the same
    instance only after successful preparation or explicit legacy world load.
    """
    def __init__(self, instance):
        self.instance = instance
        self.state = 'new'
        self.error = None

    def run(self, context):
        if type(context) is not PreparationContext:
            raise TypeError('Expected read-only PreparationContext')
        if self.state == 'prepared':
            return False
        if self.state != 'new':
            raise RuntimeError('Preparation already attempted; no automatic replay')
        self.state = 'preparing'
        try:
            callback = getattr(self.instance, 'prepare_startup', None)
            if callback is not None:
                if not callable(callback):
                    raise TypeError('prepare_startup must be callable when present')
                callback(context)
        except BaseException as error:
            self.state = 'failed'
            self.error = type(error).__name__
            raise
        self.state = 'prepared'
        return True
