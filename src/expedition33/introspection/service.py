"""Original BL4 local-file protocol, serviced by the external SDK owner thread.

Adapted from Mattmab's BL4Introspection 1.3 entry point (MIT, adjacent LICENSE).
Claims are never replayed. An orphan .processing file records an unknown outcome.
"""
import json
import logging
import math
import os
from pathlib import Path
import threading
import time
import uuid


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False), encoding='utf-8')
    os.replace(temp, path)


class FileService:
    def __init__(self, data, harness, target_pid):
        self.data = Path(data).resolve()
        self.harness = harness
        self.target_pid = target_pid
        self.session = uuid.uuid4().hex
        self._owner = threading.get_ident()
        self._busy = False
        self._enabled = True
        self._closed = False
        self._last_poll = self._last_heartbeat = 0.0
        for directory in (self.data, self.data / 'requests', self.data / 'responses'):
            directory.mkdir(parents=True, exist_ok=True)
        self.heartbeat()

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('File service must run on its owning Python thread')

    def heartbeat(self):
        self._check()
        write_json(self.data / 'status.json', {
            'version': 'e33-port-1.3-stage1', 'session': self.session,
            'pid': os.getpid(), 'controller_pid': os.getpid(), 'target_pid': self.target_pid,
            'enabled': self._enabled, 'heartbeat': time.time(),
            'tick': 'external SDK owner-thread poll', 'lov_loaded': False,
            'operations': sorted(self.harness.SUPPORTED), 'parity_complete': False})
        self._last_heartbeat = time.monotonic()

    def pump(self):
        self._check()
        now = time.monotonic()
        if not self._enabled or self._busy or now - self._last_poll < .1:
            return
        self._last_poll, self._busy = now, True
        try:
            if now - self._last_heartbeat > 1:
                self.heartbeat()
            path = next((self.data / 'requests').glob('*.json'), None)
            if path is None:
                return
            request_id = path.stem
            claimed = path.with_suffix('.processing')
            # Do not replace a claim left by a crash, even if a client mistakenly
            # republishes its ID. Original clients always use a fresh UUID.
            if claimed.exists() or (self.data / 'responses' / path.name).exists():
                path.rename(path.with_suffix('.duplicate.' + uuid.uuid4().hex))
                return
            path.rename(claimed)
            response = {'id': request_id, 'session': self.session, 'time': time.time()}
            try:
                if claimed.stat().st_size > 65536:
                    raise ValueError('Request exceeds 64 KiB')
                request = json.loads(claimed.read_text(encoding='utf-8'))
                if not isinstance(request, dict):
                    raise ValueError('Request must be a JSON object')
                if request.get('session') != self.session:
                    raise ValueError('Stale session; read status.json and resubmit')
                expires = float(request['expires'])
                if not math.isfinite(expires) or not time.time() < expires:
                    raise ValueError('Request expired or expiry is invalid')
                result = self.harness.request(request)
                if len(json.dumps(result, allow_nan=False).encode('utf-8')) > 262144:
                    raise ValueError('Response exceeds 256 KiB; use smaller pages')
                response.update(ok=True, result=result)
            except BaseException as exc:
                try:
                    message = str(exc)[:2000]
                except BaseException:
                    message = '<exception formatting failed>'
                response.update(ok=False, error={'type': type(exc).__name__, 'message': message})
            encoded = json.dumps(response, ensure_ascii=True, allow_nan=False).encode('utf-8')
            if len(encoded) > 262144:
                response.pop('result', None)
                response.update(ok=False, error={'type': 'ValueError', 'message': 'Response envelope exceeds 256 KiB'})
            write_json(self.data / 'responses' / (request_id + '.json'), response)
            claimed.unlink()
            self.heartbeat()
        except Exception:
            logging.getLogger('expedition33.introspection').exception('File service failure; claimed work is not replayed')
        finally:
            self._busy = False

    def revoke(self):
        """Stop claiming queued requests; existing claims are never replayed."""
        self._check()
        self._enabled = False

    def close(self):
        self._check()
        if self._busy:
            raise RuntimeError('Cannot close file service during dispatch')
        if not self._closed:
            self._enabled = False
            self.heartbeat()
            self._closed = True
