"""Load the verified CustomModel.sdkmod in an isolated mesh-capable controller."""
from pathlib import Path
import sys,time,json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import expedition33.sdk as sdk
from expedition33.mods import ModLoader
from expedition33.mod_archive import read_candidate
from expedition33.mod_lock import ModRootLock
from expedition33.controller_commands import CommandServer,Command
from expedition33.lease_policy import statistics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-root',type=Path,required=True,help='Installed SDK root; prevents simultaneous controllers')
args=parser.parse_args()
output=ROOT/'dist/custom-model'
archive=output/'CustomModel.sdkmod'
candidate=read_candidate(archive,hashlib.sha256(archive.read_bytes()).hexdigest())
mod_root=output/'live-mods';folder=mod_root/'CustomModel';folder.mkdir(parents=True,exist_ok=True)
for name,data in candidate.files:
    target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
original=sdk.SessionTransport
sdk.SessionTransport=lambda **kwargs:original(_executable=ROOT/'build/release/research-probe-mesh-v7/research_probe.exe')
def record(event,result):
    with (output/'live-events.jsonl').open('a',encoding='utf8') as stream:
        stream.write(json.dumps(dict(time=time.time(),event=event,result=result))+'\n')
    return result
lock=ModRootLock(args.sdk_root)
try:
    with sdk.Session(multiple_pause_entries=True) as session,ModLoader(mod_root,session=session) as loader:
        loader.load('CustomModel');loader.enable('CustomModel',console=True)
        model=loader._loaded['CustomModel'][1]
        def execute(name):
            try:return record(name,getattr(model,name)())
            except Exception as error:record(name+'.error',str(error));raise
        def status():return record('status',dict(mod=model.status(),leases=statistics(session),pid=session.pid))
        server=CommandServer({'model.spawn':Command('model',lambda:execute('spawn')),
            'model.destroy':Command('model',lambda:execute('destroy')),'model.status':Command('inspect',status),
            'sdk.shutdown':Command('lifecycle',loader.request_stop)},capabilities={'model','inspect','lifecycle'})
        try:
            connection=server.write_connection(ROOT/'settings/custom-model-controller')
            (output/'connection-path.txt').write_text(str(connection))
            record('ready',dict(pid=session.pid,archive_sha256=candidate.sha256))
            while not loader.stop_requested:
                server.poll();loader.poll();time.sleep(.01)
            time.sleep(.3)
        finally:
            server.close();model.destroy();record('cleanup',statistics(session))
finally:lock.close()
