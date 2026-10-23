"""Fixed, collision-free tetrahedron live proof. No arbitrary execution endpoint."""
from pathlib import Path
import sys
import time
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import expedition33.sdk as sdk
from expedition33._scope import SessionScope
from expedition33.procedural_mesh import Tetrahedron
from expedition33.controller_commands import CommandServer,Command
from expedition33.lease_policy import statistics

original=sdk.SessionTransport
sdk.SessionTransport=lambda **kwargs:original(_executable=ROOT/'build/release/research-probe-mesh-v7/research_probe.exe')
output=ROOT/'dist/mesh-feasibility'
output.mkdir(parents=True,exist_ok=True)
def record(event,result):
    with (output/'live-events.jsonl').open('a',encoding='utf8') as stream:
        stream.write(json.dumps(dict(time=time.time(),event=event,result=result))+'\n')
    return result

with sdk.Session(leases=True) as session:
    scope=SessionScope(session,lease_owner='ProceduralMeshProof')
    model=None
    stopping=False
    def spawn():
        global model
        if model and not model.closed:raise RuntimeError('Destroy the existing model first')
        model=Tetrahedron(scope)
        try:return record('spawn',model.spawn())
        except BaseException as exc:
            record('spawn.error',str(exc));raise
    def destroy():
        return record('destroy',model.close() if model else None)
    def status():
        return record('status',dict(mesh=model.status() if model else None,leases=statistics(session),
            game_pid=session.pid,transport_pid=session._transport._process.pid))
    def shutdown():
        global stopping
        stopping=True
        return {'stopping':True}
    server=CommandServer({'mesh.spawn':Command('mesh',spawn),'mesh.destroy':Command('mesh',destroy),
        'mesh.status':Command('inspect',status),'sdk.shutdown':Command('lifecycle',shutdown)},
        capabilities={'mesh','inspect','lifecycle'})
    try:
        connection=server.write_connection(ROOT/'settings/mesh-controller')
        (output/'connection-path.txt').write_text(str(connection),encoding='utf8')
        record('ready',dict(game_pid=session.pid,transport_pid=session._transport._process.pid))
        while not stopping:
            server.poll()
            time.sleep(.01)
        time.sleep(.3)
    finally:
        server.close()
        scope.close()
        record('scope.closed',statistics(session))
