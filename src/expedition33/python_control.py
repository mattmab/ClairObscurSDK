"""Explicit opt-in local Python control, using the SDK controller owner thread."""
from dataclasses import asdict
from pathlib import Path
import hashlib,json,os,threading
from .controller_commands import CommandServer,Command

class PythonControl:
    def __init__(self,session,directory):
        session._check();self.session=session;self.state='starting';self.original_poll=session.poll
        self.server=CommandServer({'python.execute':Command('python',self.execute),
            'python.file':Command('python',self.execute_file),
            'python.inspect':Command('inspect',self.inspect)},capabilities={'python','inspect'},queue_timeout=60.)
        try:self.connection_path=self.server.write_connection(Path(directory))
        except BaseException:self.server.close();raise
        self._poll=self.pump;session.poll=self._poll;self.state='active'
    def inspect(self):
        self.session._check()
        return dict(controller_pid=os.getpid(),game_pid=self.session.pid,persistent_namespace=True,queue_timeout=60.,state=self.state)
    def execute(self,source):
        self.session._check()
        if self.state!='active':raise RuntimeError('Local Python endpoint is closed')
        if type(source) is not str or not source.strip() or len(source.encode('utf8'))>6000:raise ValueError('Use python.file for a larger UTF-8 script')
        return self._execute(source)
    def _execute(self,source):
        result=asdict(self.session.console.dispatcher.execute('py '+source,native_fallback=False))
        raw=result['output'].encode('utf8',errors='replace')
        if len(raw)>16000:result['output']=raw[:16000].decode('utf8',errors='ignore');result['truncated']=True
        return result
    def execute_file(self,path,sha256):
        self.session._check()
        if self.state!='active':raise RuntimeError('Local Python endpoint is closed')
        if type(path) is not str or not Path(path).is_absolute():raise ValueError('Absolute local script path required')
        if type(sha256) is not str or len(sha256)!=64 or any(c not in '0123456789abcdef' for c in sha256):raise ValueError('Exact lowercase SHA256 required')
        script=Path(path).resolve(strict=True)
        if not script.is_file() or script.stat().st_size>1024*1024:raise ValueError('Expected a local script no larger than 1 MiB')
        raw=script.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha256:raise ValueError('Local script changed before dispatch; not executed')
        source=raw.decode('utf-8-sig')
        return self._execute('exec(compile('+repr(source)+','+repr(str(script))+',"exec"))')
    def pump(self):
        self.session._check();self.server.poll()
        if getattr(self.session,'_closed',False):return 0
        return self.original_poll()
    def close(self):
        if self.state=='closed':return True
        self.session._check();self.server.close()
        if self.session.poll is self._poll:self.session.poll=self.original_poll
        self.state='closed';return True

def enabled(directory):
    file=Path(directory)/'enabled.json'
    if not file.is_file():return False
    try:data=json.loads(file.read_text(encoding='utf8'))
    except (OSError,ValueError):return False
    return type(data) is dict and set(data)=={'enabled'} and data['enabled'] is True

def install(session,*,directory=None):
    session._check()
    previous=getattr(session,'_local_python_control',None)
    if previous is not None and previous.state!='closed':return previous
    if directory is None:
        from .paths import settings_dir
        directory=settings_dir()/'python-control'
    from ._metadata_stabilization import process_preparation
    scope=process_preparation(session).scope
    owner=PythonControl(session,directory)
    session._local_python_control=owner
    scope._reference_owners.append(owner)
    return owner
