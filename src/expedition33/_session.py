"""Internal persistent native transport; public subscription API is a separate layer."""
import json
from pathlib import Path
import queue
import subprocess
import threading

from . import RuntimeQueryError


class SessionTransport:
    def __init__(self, *, _executable=None):
        self._owner = threading.get_ident()
        self._closed = False
        self._lines = queue.Queue(maxsize=256)
        executable = _executable or Path(__file__).resolve().parents[2] / 'build/research-probe/research_probe.exe'
        self._process = subprocess.Popen([str(executable), '--session'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',
            errors='strict', bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW)
        process = self._process
        lines = self._lines
        def reader():
            try:
                for line in process.stdout:
                    lines.put(line)
            except (OSError, UnicodeError) as error:
                lines.put(error)
            finally:
                lines.put(None)
        self._reader = threading.Thread(target=reader, daemon=True, name='expedition33-session-output')
        self._reader.start()
        try:
            self.start = self._read()
            self.objects = [self._read(), self._read()]
            ready = self._read()
            self.reflected_protocol = ready.get('reflected_protocol', 0)
            if (self.start.get('event') != 'snapshot_start' or
                any(row.get('event') != 'object' for row in self.objects) or
                ready.get('event') != 'session_ready' or ready['pid'] != self.start['pid'] or
                ready['game_thread_id'] != self.start['game_thread_id']):
                raise RuntimeQueryError('Incomplete native session handshake')
            identities = {(row['name'], row['class_name']) for row in self.objects}
            if identities != {('Default__Actor', 'Actor'), ('IsActorBeingDestroyed', 'Function')}:
                raise RuntimeQueryError('Native session target identity mismatch')
        except BaseException:
            self._abort()
            raise

    def _check_thread(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Native sessions must be used on their owning Python thread')

    def _read(self):
        try:
            line = self._lines.get(timeout=15)
        except queue.Empty as error:
            raise RuntimeQueryError('Native session response timed out') from error
        if line is None:
            raise RuntimeQueryError('Native session ended before acknowledging the request')
        if isinstance(line, BaseException):
            raise RuntimeQueryError(f'Native session output failed: {line}')
        try:
            if len(line) > 1_000_000:
                raise ValueError('Oversized response')
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError('Expected a JSON object')
        except (ValueError, TypeError) as error:
            raise RuntimeQueryError(f'Invalid native session response: {error}') from error
        if value.get('event') == 'error':
            raise RuntimeQueryError(value.get('message', 'Native session failed'))
        return value

    def command(self, command, payload=None):
        self._check_thread()
        if self._closed:
            raise RuntimeQueryError('Native session is closed')
        reflected = command == 'reflected-invoke'
        if reflected and getattr(self, 'reflected_protocol', 0) != 1:
            raise ValueError('Native session does not support reflected invocation')
        if not reflected and command not in ('enable', 'disable', 'invoke', 'drain', 'ping', 'close', 'console-attach', 'console-detach', 'console-status', 'console-poll', 'console-execute', 'console-print', 'console-names', 'console-key'):
            raise ValueError('Unsupported native session command')
        suffix = ''
        if reflected:
            from ._invocation_wire import SIZE
            if type(payload) is not bytes or len(payload) != SIZE:
                raise ValueError('Invalid reflected invocation payload')
            suffix = ' ' + payload.hex()
        elif payload is not None:
            if command not in ('console-execute', 'console-print', 'console-names', 'console-key') or not isinstance(payload, str) or '\0' in payload:
                raise ValueError('Invalid console payload')
            encoded = payload.encode('utf-16le')
            if len(encoded) > (8192 if command == 'console-execute' else 65536):
                raise ValueError('Console payload is too long')
            suffix = ' ' + encoded.hex()
        try:
            self._process.stdin.write(command + suffix + '\n')
            self._process.stdin.flush()
            response = self._read()
            if response.get('event') != 'session_response' or response.get('command') != command:
                raise RuntimeQueryError('Native session response does not match its command')
            if command == 'close':
                if response.get('closed') is not True or response.get('close_reason') != 1:
                    raise RuntimeQueryError('Native session close was not confirmed')
            elif response.get('closed') is not False:
                raise RuntimeQueryError('Native session closed unexpectedly')
            return response
        except BaseException:
            self._abort()
            raise

    def _abort(self):
        # Only our controller subprocess. Its exit wakes the target-owned cleanup
        # watcher; never terminate or force-unload anything from the game here.
        self._closed = True
        if self._process.poll() is None:
            self._process.kill()
        self._process.wait(timeout=10)
        try:
            self._process.stdin.close()
        except OSError:
            pass  # A dead controller can reject the buffered pipe flush.
        self._reader.join(timeout=2)
        self._process.stdout.close()

    def close(self):
        self._check_thread()
        if self._closed:
            return
        try:
            self.command('close')
            self._process.stdin.close()
            end = self._read()
            if end.get('event') != 'snapshot_end' or end.get('emitted') != 2:
                raise RuntimeQueryError('Native session final boundary is missing')
            if self._process.wait(timeout=10) != 0:
                raise RuntimeQueryError('Native session controller exited with an error')
            self._closed = True
            self._reader.join(timeout=2)
            self._process.stdout.close()
        except BaseException:
            self._abort()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
