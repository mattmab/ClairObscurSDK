"""Explicitly owned read-only worker; no cached runtime observations or retries."""
from contextvars import ContextVar
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

from . import RuntimeQueryError

_active = ContextVar('expedition33_read_batch', default=None)
_SELECTED = frozenset(('--catalog-select', '--catalog-match', '--describe', '--read-values', '--describe-enums'))


def active_reader():
    return _active.get()


class ReadBatch:
    """Reuse startup validation during an explicitly owned context.

    The default context owns one operation. An opt-in ``share=True`` owner
    permits same-thread, same-process operation contexts to borrow its worker.
    Only that outer owner closes it; query failures remain terminal until exit.

    The native worker pins the original process and deny-write/delete image
    handle. Every request reads current runtime data and checks live anchors.
    Failure terminates this read-only child and forbids subsequent requests;
    it never retries and owns no hooks, widgets, leases, or engine mutations.
    """
    def __init__(self, pid, *, share=False, _executable=None):
        if type(pid) is not int or not 0 < pid <= 0xffffffff:
            raise ValueError('Expected a process ID')
        self.pid = pid
        self._executable = _executable
        self._share = bool(share)
        self._borrowed = None
        self._owner = threading.get_ident()
        self._process = self._thread = self._token = None
        self._lines = queue.Queue(maxsize=256)
        self._stop = threading.Event()
        self._closed = False
        self._sequence = 0

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeQueryError('Read batch requires its owning thread')
        if self._closed:
            raise RuntimeQueryError('Read batch is closed after completion or failure')

    def _read(self):
        def deliver(value):
            while not self._stop.is_set():
                try:
                    self._lines.put(value, timeout=.1)
                    return
                except queue.Full:
                    pass
        try:
            while not self._stop.is_set():
                line = self._process.stdout.readline(1048577)
                if not line:
                    break
                if len(line) > 1048576 or not line.endswith('\n'):
                    raise RuntimeQueryError('Read worker line exceeded bounds or was truncated')
                deliver(line)
        except BaseException as error:
            deliver(error)
        finally:
            deliver(None)

    def _line(self, deadline):
        try:
            value = self._lines.get(timeout=max(0., deadline - time.monotonic()))
        except queue.Empty:
            raise RuntimeQueryError('Read worker timed out; request was not retried') from None
        if isinstance(value, BaseException):
            raise RuntimeQueryError(f'Read worker stream failed: {value}') from value
        if value is None:
            raise RuntimeQueryError('Read worker exited before completing its response')
        return value

    def __enter__(self):
        self._check()
        parent = _active.get()
        if self._process is not None or self._borrowed is not None:
            raise RuntimeQueryError('Read batches cannot be nested or reentered')
        if parent is not None:
            parent._check()
            if not parent._share or parent.pid != self.pid or self._share:
                raise RuntimeQueryError('Read batches cannot be nested across owners or processes')
            self._borrowed = parent
            return self
        executable = self._executable or Path(__file__).resolve().parents[2] / 'build/readonly-worker/research_probe.exe'
        try:
            self._process = subprocess.Popen([str(executable), '--reader-session', str(self.pid)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding='utf-8', errors='strict', creationflags=subprocess.CREATE_NO_WINDOW)
            self._thread = threading.Thread(target=self._read, name='e33-read-worker', daemon=True)
            self._thread.start()
            ready = json.loads(self._line(time.monotonic() + 120))
            if ready != {'event': 'reader_ready', 'version': 1, 'pid': self.pid}:
                raise RuntimeQueryError(f'Read worker rejected startup: {ready}')
            self._token = _active.set(self)
            return self
        except BaseException:
            self.close()
            raise

    def query(self, arguments):
        self._check()
        if self._borrowed is not None:
            return self._borrowed.query(arguments)
        if self._token is None:
            raise RuntimeQueryError('Enter the read batch before querying')
        allowed = (arguments == ['--catalog'] or
            (len(arguments) == 3 and arguments[0] in _SELECTED and arguments[1] == str(self.pid)))
        if not allowed or any(type(arg) is not str or any(c in arg for c in '\r\n\t\0') for arg in arguments):
            raise RuntimeQueryError('Operation is not allowed in a read batch')
        request = '\t'.join(arguments) + '\n'
        if len(request.encode('utf-8')) > 131072:
            raise RuntimeQueryError('Read worker request exceeded bounds')
        try:
            self._sequence += 1
            self._process.stdin.write(request)
            self._process.stdin.flush()
            deadline = time.monotonic() + 120
            lines, size = [], 0
            while True:
                line = self._line(deadline)
                size += len(line)
                if size > 128 * 1024 * 1024:
                    raise RuntimeQueryError('Read worker response exceeded bounds')
                if line.startswith('{"event":"reader_result",'):
                    end = json.loads(line)
                    if end != {'event': 'reader_result', 'sequence': self._sequence, 'code': 0}:
                        raise RuntimeQueryError('Read worker rejected query: ' + ''.join(lines)[-4096:])
                    return ''.join(lines)
                if line.startswith('{"event":"reader_error",'):
                    raise RuntimeQueryError('Read worker rejected request: ' + line.strip())
                lines.append(line)
        except BaseException:
            self.close()
            raise

    def close(self):
        if threading.get_ident() != self._owner:
            raise RuntimeQueryError('Read batch cleanup requires its owning thread')
        if self._closed:
            return
        self._closed = True
        if self._borrowed is not None:
            # Only the outer owner may close the shared worker. A failed query
            # closes that owner directly and remains terminal for all borrowers.
            self._borrowed = None
            return
        # Keep a failed instance in context until __exit__: no implicit return
        # to one-shot queries during the same failed operation.
        self._stop.set()
        process = self._process
        if process is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()  # This child is read-only, with no engine owners.
                process.wait(timeout=2)
            if self._thread is not None:
                self._thread.join(timeout=2)
            process.stdout.close()

    def __exit__(self, *_error):
        try:
            self.close()
        finally:
            if self._token is not None:
                _active.reset(self._token)
                self._token = None
