"""Isolated local lifecycle test; terminate only the recorded probe to simulate loss."""
from pathlib import Path
import json,sys,time,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import expedition33.sdk as sdk
from expedition33._scope import SessionScope
from expedition33.mod_lock import ModRootLock
from expedition33.catalog import capture_matching
from expedition33.procedural_mesh import Tetrahedron,discover,MATERIAL_PROFILES
from expedition33.lease_policy import statistics

out=ROOT/'dist/verso-2b'
def record(event,**data):
    with (out/'disconnect.jsonl').open('a') as f:f.write(json.dumps(dict(time=time.time(),event=event,**data))+'\n')
original=sdk.SessionTransport
sdk.SessionTransport=lambda **kw:original(_executable=ROOT/'build/release/research-probe-mesh-v14/research_probe.exe')
lock=ModRootLock(Path('S:/SteamLibrary/steamapps/common/Expedition 33/SDK'))
try:
    with sdk.Session(multiple_pause_entries=True) as session:
        record('baseline',leases=statistics(session))
        scope=SessionScope(session,lease_owner='2BDisconnectTest')
        model=Tetrahedron(scope)
        try:
            pawn=discover(session.pid)[0]
            c=capture_matching(session.pid,names=('Body',))
            drivers=[o for o in c.objects if o.outer_index==pawn.index and o.name=='Body']
            if len(drivers)!=1:raise RuntimeError('Expected one exploration body')
            data=json.loads((out/'prepared-v14b/skin-provenance.json').read_text())
            model.spawn(ground=True)
            names=('SetVectorParameterValue','Default__KismetStringLibrary','Default__KismetRenderingLibrary','ImportFileAsTexture2D','CreateDynamicMaterialInstance','SetTextureParameterValue','K2_GetTextureParameterValue','Conv_StringToName','Texture2D','Texture','MaterialInterface','MaterialInstanceDynamic')
            names+=tuple(p.rsplit('.',1)[1] for p,_,_ in MATERIAL_PROFILES)
            catalog=capture_matching(session.pid,names=names)
            for i,row in enumerate(data['sections']):
                model.upload_section(row['mesh'],i)
                if row['texture']:model.set_image_plate_texture(catalog,row['texture'],i,profile=2)
            model.bind_skin(data['skin'],drivers[0].index)
            model.hide_driver()
            record('armed',python_pid=os.getpid(),probe_pid=session._transport._process.pid,native=model.status(),leases=statistics(session))
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                session.poll();time.sleep(.05)
            record('timeout')
        finally:
            scope.close()
except Exception as error:record('exit',error=repr(error))
finally:lock.close()
