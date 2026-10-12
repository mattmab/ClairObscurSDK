"""Bounded, payload-free development timings (opt-in)."""
import json
import logging
from logging.handlers import RotatingFileHandler
import time
from pathlib import Path
from threading import RLock

class Telemetry:
    def __init__(self, path):
        self._summary_path = Path(str(path) + '.summary.json')
        self._started = time.time()
        self._totals = {}
        self._lock = RLock()
        self._handler = RotatingFileHandler(path, maxBytes=262144, backupCount=2, encoding='utf8')
        self._handler.setFormatter(logging.Formatter('%(message)s'))

    def record(self, operation, category, start, duration, success, **counts):
        allowed = {'tool_calls', 'ipc_round_trips', 'cache_hits', 'cache_misses',
                   'controller_restarts', 'process_launches', 'native_round_trip_ms'}
        row = dict(operation=operation, category=category, start=start,
                   end=start+duration, duration_ms=duration*1000, success=bool(success))
        row.update({key:value for key,value in counts.items() if key in allowed and type(value) in (int,float)})
        # Never accept arguments, responses, exception text or connection credentials.
        self._handler.handle(logging.LogRecord('workflow', logging.INFO, '', 0,
                             json.dumps(row, allow_nan=False), (), None))
        with self._lock:
            key = (str(category)[:80], str(operation)[:120])
            # Fixed-size aggregate storage even if an instrumentation caller
            # accidentally supplies unbounded operation names.
            if key not in self._totals and len(self._totals) >= 63:
                key = ('overflow', 'other')
            total = self._totals.setdefault(key, dict(count=0, failures=0, duration_ms=0))
            total['count'] += 1
            total['failures'] += int(not success)
            total['duration_ms'] += row['duration_ms']
            for name in allowed:
                if name in row:
                    total[name] = total.get(name, 0) + row[name]

    def snapshot(self):
        """Session totals survive event rotation; no latency percentiles inferred."""
        with self._lock:
            return dict(start=self._started, end=time.time(),
                        operations=[dict(category=category, operation=operation, **values)
                                    for (category, operation), values in sorted(self._totals.items())])

    def poll_wait(self, seconds):
        """Measure deliberate polling sleep separately from native/handler time."""
        started, clock = time.time(), time.perf_counter()
        time.sleep(seconds)
        self.record('controller.poll_wait', 'poll_wait', started, time.perf_counter()-clock, True)

    def close(self):
        try:
            # A separate final snapshot avoids disk writes on every native poll.
            # Abrupt process death can lose totals; the rotated events remain.
            temporary = self._summary_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.snapshot(), allow_nan=False), encoding='utf8')
            temporary.replace(self._summary_path)
        finally:
            self._handler.close()
