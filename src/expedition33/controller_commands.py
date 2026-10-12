"""Opt-in, authenticated loopback commands. Never evaluates Python source.

Network input is queued; only poll() on the session owner thread invokes an
explicitly registered handler. Request IDs are retained for the entire server
session, preventing duplicate execution after a lost response.
"""
from dataclasses import dataclass
import hmac
import json
import secrets
import socket
import threading
import uuid
import os
from pathlib import Path
import subprocess
import csv
import time
import math


def _reject_constant(value):
    raise ValueError("Non-finite JSON number")


@dataclass(frozen=True)
class Command:
    capability: str
    handler: object


class CommandServer:
    def __init__(self, commands, *, capabilities, queue_timeout=10.0, telemetry=None):
        if not math.isfinite(queue_timeout) or not 0 < queue_timeout <= 60:
            raise ValueError("Queue timeout must be in (0, 60]")
        self._queue_timeout = queue_timeout
        self._telemetry = telemetry
        self._connection_path = None
        self._owner = threading.get_ident()
        self._commands = dict(commands)
        self._capabilities = frozenset(capabilities)
        self._commands['sdk.capabilities'] = Command('inspect', lambda: {
            'session': self.session,
            'commands': {name:cmd.capability for name,cmd in self._commands.items()
                         if cmd.capability in self._capabilities}})
        self._requests = {}
        self._queue = []
        self._lock = threading.Lock()
        self._closed = False
        self.session = uuid.uuid4().hex
        self._token = secrets.token_hex(32)
        self._socket = socket.socket()
        self._socket.bind(('127.0.0.1', 0))
        self._socket.listen(4)
        self._socket.settimeout(.2)
        self._thread = threading.Thread(target=self._serve, daemon=True, name='sdk-commands')
        self._thread.start()

    def connection(self):
        return dict(version=1, host='127.0.0.1', port=self._socket.getsockname()[1],
                    session=self.session, token=self._token)

    def _receive(self, request):
        if not isinstance(request, dict) or set(request) != {'token','session','id','command','arguments'}:
            return {'error':'invalid_request'}
        token = request['token']
        if not isinstance(token,str) or len(token)!=64 or not token.isascii() or not hmac.compare_digest(token,self._token):
            return {'error':'unauthorized'}
        if request['session'] != self.session:
            return {'error':'wrong_session'}
        rid, name, arguments = request['id'], request['command'], request['arguments']
        if not isinstance(rid,str) or len(rid)!=32 or any(c not in '0123456789abcdef' for c in rid):
            return {'error':'invalid_id'}
        if not isinstance(name,str) or not isinstance(arguments,dict):
            return {'error':'invalid_command'}
        with self._lock:
            if self._closed: return {'error':'closed'}
            existing = self._requests.get(rid)
            if name == 'request.cancel':
                if arguments: return {'error':'invalid_arguments'}
                if not existing: return {'error':'unknown_request'}
                if existing['reply']['state']=='queued':
                    self._queue.remove(rid)
                    existing['reply']={'id':rid,'state':'cancelled'}
                elif existing['reply']['state']=='running':
                    return {'id':rid,'state':'running','error':'not_preemptible'}
                return dict(existing['reply'])
            if name == 'request.status':
                if arguments: return {'error':'invalid_arguments'}
                return dict(existing['reply']) if existing else {'error':'unknown_request'}
            if existing:
                if existing['command'] != name or existing['arguments'] != arguments:
                    return {'error':'id_conflict'}
                return dict(existing['reply'])
            command = self._commands.get(name)
            if command is None: return {'error':'unknown_command'}
            if command.capability not in self._capabilities: return {'error':'capability_denied'}
            if len(self._requests)>=2048 or len(self._queue)>=16: return {'error':'capacity'}
            item = dict(queued_clock=time.perf_counter(), queued_time=time.time(),
                        deadline=time.monotonic()+self._queue_timeout, command=name, arguments=arguments, reply={'id':rid,'state':'queued'})
            self._requests[rid] = item
            self._queue.append(rid)
            return dict(item['reply'])

    def _serve(self):
        while not self._closed:
            try:
                client, _ = self._socket.accept()
            except socket.timeout: continue
            except OSError: return
            with client:
                client.settimeout(1)
                try:
                    data = bytearray()
                    while b'\n' not in data and len(data)<=8192:
                        part = client.recv(min(4096,8193-len(data)))
                        if not part: break
                        data.extend(part)
                    if len(data)>8192 or not data.endswith(b'\n') or data.count(b'\n')!=1:
                        reply = {'error':'invalid_frame'}
                    else:
                        reply = self._receive(json.loads(data, parse_constant=_reject_constant))
                    client.sendall(json.dumps(reply,allow_nan=False).encode()+b'\n')
                except (OSError,ValueError,RecursionError):
                    pass

    def poll(self):
        if threading.get_ident()!=self._owner:
            raise RuntimeError('Commands require the controller owner thread')
        with self._lock:
            if self._closed or not self._queue: return False
            rid = self._queue.pop(0)
            item = self._requests[rid]
            if time.monotonic() >= item['deadline']:
                item['reply']={'id':rid,'state':'expired'}
                return True
            item['reply'] = {'id':rid,'state':'running'}
        started = time.time()
        clock = time.perf_counter()
        if self._telemetry is not None:
            self._telemetry.record(item['command'], 'controller_queue_wait', item['queued_time'],
                                   clock-item['queued_clock'], True)
        try:
            value = self._commands[item['command']].handler(**item['arguments'])
            encoded = json.dumps(value,allow_nan=False)
            if len(encoded.encode())>65536: raise ValueError('Result exceeds command output limit')
            reply = {'id':rid,'state':'completed','result':json.loads(encoded)}
        except Exception as error:
            reply = {'id':rid,'state':'failed','error':type(error).__name__,'message':str(error)[:2048]}
        with self._lock: item['reply'] = reply
        if self._telemetry is not None:
            self._telemetry.record(item['command'], 'controller', started,
                time.perf_counter()-clock, reply['state']=='completed')
        return True

    def close(self):
        if threading.get_ident()!=self._owner:
            raise RuntimeError('Close requires the controller owner thread')
        with self._lock:
            self._closed = True
            for rid in self._queue:
                self._requests[rid]['reply'] = {'id':rid,'state':'cancelled'}
            self._queue.clear()
        self._socket.close()
        self._thread.join(timeout=2)
        self._commands.clear()
        if self._connection_path is not None:
            self._connection_path.unlink(missing_ok=True)
            self._connection_path = None

    def write_connection(self, directory):
        """Publish credentials only after granting access to the current OS user."""
        directory = Path(directory)
        directory.mkdir(parents=True,exist_ok=True)
        path = directory / f'controller-{self.session}.json'
        fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            if os.name=='nt':
                flags = subprocess.CREATE_NO_WINDOW
                who = subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,
                                     text=True,check=True,timeout=5,creationflags=flags)
                sid = next(csv.reader(who.stdout.splitlines()))[1]
                if not sid.startswith('S-1-'): raise RuntimeError('Cannot resolve credential-file owner')
                subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',f'*{sid}:(F)'],
                               capture_output=True,check=True,timeout=5,creationflags=flags)
            with os.fdopen(fd,'w',encoding='utf8') as stream:
                fd = None
                json.dump(self.connection(),stream)
        except BaseException:
            if fd is not None: os.close(fd)
            path.unlink(missing_ok=True)
            raise
        self._connection_path = path
        return path


class CommandClient:
    def __init__(self, connection):
        if connection.get('version')!=1 or connection.get('host')!='127.0.0.1':
            raise ValueError('Expected a version 1 loopback connection')
        self.connection = dict(connection)

    def request(self, command, arguments=None, *, request_id=None):
        rid = request_id or uuid.uuid4().hex
        request = dict(token=self.connection['token'],session=self.connection['session'],
                       id=rid,command=command,arguments={} if arguments is None else arguments)
        encoded = json.dumps(request,allow_nan=False).encode()+b'\n'
        if len(encoded)>8192: raise ValueError('Command exceeds input limit')
        # A timeout never retries execution. Keep the ID to query request.status.
        try:
            with socket.create_connection(('127.0.0.1',self.connection['port']),timeout=3) as sock:
                sock.sendall(encoded)
                with sock.makefile('rb') as stream:
                    data = stream.readline(131073)
                if len(data)>131072 or not data.endswith(b'\n'): raise ValueError('Invalid response frame')
                return json.loads(data)
        except OSError as error:
            raise RuntimeError(f'Command delivery uncertain; query request.status with id {rid}') from error
