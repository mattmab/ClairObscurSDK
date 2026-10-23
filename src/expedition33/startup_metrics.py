"""Bounded, owner-thread startup timing; never records configuration payloads."""
from collections import deque
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time


class StartupMetrics:
    """Use a process anchor from the same monotonic clock as ``clock``.

    Phase names and optional module names are diagnostic identifiers only.
    Exception messages and arbitrary metadata are deliberately not accepted.
    """

    def __init__(self, *, process_started=None, clock=time.perf_counter,
                 wallclock=None, event_limit=256, phase_limit=128):
        if type(event_limit) is not int or not 1 <= event_limit <= 10000:
            raise ValueError('event_limit must be 1..10000')
        if type(phase_limit) is not int or not 1 <= phase_limit <= 1024:
            raise ValueError('phase_limit must be 1..1024')
        self._owner = threading.get_ident()
        self._clock = clock
        self._events = deque(maxlen=event_limit)
        self._summary = {}
        self._phase_limit = phase_limit
        self._dropped = 0
        self._sequence = 0
        self._last_time = self._number(clock())
        self._started = (self._last_time if process_started is None
                         else self._number(process_started))
        if self._started > self._last_time:
            raise ValueError('process_started is later than the current clock')
        self._wallclock = None if wallclock is None else self._number(wallclock)

    @staticmethod
    def _number(value):
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError('Timing values must be finite numbers')
        return float(value)

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Startup metrics belong to their owner thread')

    def _now(self):
        value = self._number(self._clock())
        if value < self._last_time:
            raise ValueError('Startup clock moved backwards')
        self._last_time = value
        return value

    @staticmethod
    def _identifier(value):
        if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', value):
            raise ValueError('Use a short diagnostic identifier')
        return value

    def _key(self, phase, module):
        phase = self._identifier(phase)
        module = None if module is None else self._identifier(module)
        key = (phase, module)
        if key not in self._summary:
            if len(self._summary) >= self._phase_limit:
                raise ValueError('Startup phase limit reached')
            self._summary[key] = dict(phase=phase, module=module, count=0,
                failed=0, total_ms=0., max_ms=0., last_ms=0.)
        return key

    def _record(self, key, start, end, success):
        elapsed = (end - start) * 1000.
        summary = self._summary[key]
        summary['count'] += 1
        summary['failed'] += not success
        summary['total_ms'] += elapsed
        summary['max_ms'] = max(summary['max_ms'], elapsed)
        summary['last_ms'] = elapsed
        self._sequence += 1
        if len(self._events) == self._events.maxlen:
            self._dropped += 1
        self._events.append(dict(sequence=self._sequence, phase=key[0],
            module=key[1], start_ms=(start-self._started)*1000.,
            duration_ms=elapsed, success=success))

    @contextmanager
    def phase(self, name, *, module=None):
        """Record one completed span, including failure, without exception text."""
        self._check()
        key = self._key(name, module)
        start = self._now()
        try:
            yield
        except BaseException:
            # A bad diagnostic clock must never replace the original failure.
            try:
                end = self._now()
            except Exception:
                end = self._last_time
            self._record(key, start, end, False)
            raise
        else:
            self._check()
            end = self._now()
            self._record(key, start, end, True)

    def snapshot(self):
        self._check()
        return dict(version=1, process_elapsed_ms=(self._last_time-self._started)*1000.,
            process_wallclock=self._wallclock, dropped_events=self._dropped,
            events=[dict(row) for row in self._events],
            summary=[dict(row) for row in self._summary.values()])

    def write_json(self, path):
        """Atomically replace an explicit local file; parent must already exist."""
        self._check()
        path = Path(path)
        if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
            raise ValueError('Provide an absolute local output path')
        if path.is_symlink() or path.is_dir():
            raise ValueError('Output must be a regular local file')
        payload = json.dumps(self.snapshot(), indent=2, allow_nan=False) + '\n'
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf8',
                    dir=path.parent, prefix='.'+path.name+'.', suffix='.tmp',
                    delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
