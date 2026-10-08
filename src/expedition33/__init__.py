"""Independent, read-only Expedition 33 research API.

Every objects() call invokes our native reader against the running game.
Returned values are observations, not durable UObject handles. Native class
metadata is supported; property values, invocation, hooks and mod loading remain
unimplemented.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


class RuntimeQueryError(RuntimeError):
    """The native runtime query failed or returned an incomplete snapshot."""


@dataclass(frozen=True)
class ObjectSnapshot:
    pid: int
    index: int
    serial: int
    address: int
    name: str
    class_name: str
    metaclass_name: str
    class_index: int


@dataclass(frozen=True)
class PropertyMetadata:
    owner: str
    name: str
    type: str
    offset: int
    element_size: int
    dimension: int


@dataclass(frozen=True)
class ClassMetadata:
    pid: int
    name: str
    hierarchy: tuple[str, ...]
    sizes: tuple[int, ...]
    properties: tuple[PropertyMetadata, ...]


def objects(*, limit: int = 0) -> list[ObjectSnapshot]:
    """Read current objects through our native bridge (0 = all occupied slots).

The reader validates this supported build, unique anchors, names and registry
relationships. It does not pin Unreal objects or provide a GC-atomic snapshot.
Do not retain addresses for later memory access.
"""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100000000:
        raise ValueError('limit must be an integer from 0 to 100000000')
    start, samples = _query(['--limit', str(limit)])
    try:
        if any(row['event'] != 'object' for row in samples):
            raise ValueError('Unexpected metadata event')
        return [ObjectSnapshot(pid=start['pid'], index=row['index'], serial=row['serial'],
                               address=int(row['address'], 16), name=row['name'],
                               class_name=row['class_name'], metaclass_name=row['metaclass_name'],
                               class_index=row['class_index']) for row in samples]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid object response: {error}') from error


def reflect_class(name: str) -> ClassMetadata:
    """Read a uniquely named native Class and inherited property metadata.

    This initial research path excludes BlueprintGeneratedClass and does not
    read property values, pin objects, or return callable engine handles.
    """
    if not isinstance(name, str) or not name or len(name) > 1023 or '\x00' in name:
        raise ValueError('name must be a nonempty native class name')
    start, samples = _query(['--reflect-class', name])
    try:
        objects_seen = [row for row in samples if row['event'] == 'object']
        classes = [row for row in samples if row['event'] == 'class_metadata']
        properties = [row for row in samples if row['event'] == 'property_metadata']
        if (len(objects_seen) != 1 or not classes or classes[0]['name'] != name or
                len(samples) != len(objects_seen) + len(classes) + len(properties)):
            raise ValueError('Incomplete reflection response')
        return ClassMetadata(start['pid'], name, tuple(row['name'] for row in classes),
                             tuple(row['size'] for row in classes),
                             tuple(PropertyMetadata(**{k: row[k] for k in
                                   ('owner', 'name', 'type', 'offset', 'element_size', 'dimension')})
                                   for row in properties))
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid reflection response: {error}') from error


def _query(arguments: list[str]) -> tuple[dict, list[dict]]:
    root = Path(__file__).resolve().parents[2]
    executable = root / 'build' / 'research-probe' / 'research_probe.exe'
    if not executable.is_file():
        raise RuntimeQueryError(f'Native bridge missing: run {root / "scripts" / "build-research-probe.cmd"}')
    try:
        result = subprocess.run([str(executable), *arguments],
                                capture_output=True, encoding='utf-8', errors='strict',
                                timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise RuntimeQueryError(f'Native bridge execution failed: {error}') from error
    if result.returncode:
        raise RuntimeQueryError(f'Native bridge rejected query: {result.stderr.strip()}')
    try:
        records = [json.loads(line) for line in result.stdout.splitlines()]
        start, end = records[0], records[-1]
        if start['event'] != 'snapshot_start' or end['event'] != 'snapshot_end':
            raise ValueError('Missing snapshot boundary')
        samples = records[1:-1]
        object_rows = [row for row in samples if row['event'] == 'object']
        if end['emitted'] != len(object_rows):
            raise ValueError('Invalid object count or event')
        if len({row['index'] for row in object_rows}) != len(object_rows):
            raise ValueError('Duplicate object indices')
        return start, samples
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid native bridge response: {error}') from error


__all__ = ['objects', 'reflect_class', 'ObjectSnapshot', 'ClassMetadata',
           'PropertyMetadata', 'RuntimeQueryError']
