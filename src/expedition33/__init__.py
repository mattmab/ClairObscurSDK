"""Independent, read-only Expedition 33 research API.

Every objects() call invokes our native reader against the running game.
Returned values are observations, not durable UObject handles. Reflection,
invocation, hooks and mod loading are not implemented by this initial bridge.
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


def objects(*, limit: int = 0) -> list[ObjectSnapshot]:
    """Read current objects through our native bridge (0 = all occupied slots).

The reader validates this supported build, unique anchors, names and registry
relationships. It does not pin Unreal objects or provide a GC-atomic snapshot.
Do not retain addresses for later memory access.
"""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100000000:
        raise ValueError('limit must be an integer from 0 to 100000000')
    root = Path(__file__).resolve().parents[2]
    executable = root / 'build' / 'research-probe' / 'research_probe.exe'
    if not executable.is_file():
        raise RuntimeQueryError(f'Native bridge missing: run {root / "scripts" / "build-research-probe.cmd"}')
    try:
        result = subprocess.run([str(executable), '--limit', str(limit)],
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
        if end['emitted'] != len(samples) or any(row['event'] != 'object' for row in samples):
            raise ValueError('Invalid object count or event')
        if len({row['index'] for row in samples}) != len(samples):
            raise ValueError('Duplicate object indices')
        return [ObjectSnapshot(pid=start['pid'], index=row['index'], serial=row['serial'],
                               address=int(row['address'], 16), name=row['name'],
                               class_name=row['class_name'], metaclass_name=row['metaclass_name'],
                               class_index=row['class_index']) for row in samples]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid native bridge response: {error}') from error


__all__ = ['objects', 'ObjectSnapshot', 'RuntimeQueryError']
