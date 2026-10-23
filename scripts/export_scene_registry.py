"""Export authoritative skeletal-mesh registry paths using isolated candidate."""
import argparse,importlib.util,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'mods')]
from expedition33 import sdk
from expedition33.mod_lock import ModRootLock
from SceneEditor.runtime import Runtime
from SceneEditor.registry import Registry
from expedition33._scope import SessionScope
p=argparse.ArgumentParser();p.add_argument('--version',type=int,default=18);p.add_argument('--pid',type=int,required=True);args=p.parse_args()
os.environ['E33_EXPECTED_GAME_PID']=str(args.pid)
old=sdk.SessionTransport;sdk.SessionTransport=lambda **kw:old(_executable=ROOT/f'build/release/research-probe-cinematic-v{args.version}/research_probe.exe')
lock=ModRootLock('S:/SteamLibrary/steamapps/common/Expedition 33/SDK')
try:
    with sdk.Session(multiple_pause_entries=True) as session:
        runtime=Runtime();runtime.session=SessionScope(session);registry=Registry(runtime)
        meshes=registry.catalog(0);animations=registry.catalog(1)
        out=ROOT/'evidence/scene-editor/game-asset-registry.json';out.write_text(json.dumps(dict(skeletal_meshes=meshes,animations=animations),indent=2)+'\n')
        print(json.dumps(dict(output=str(out),meshes=len(meshes),animations=len(animations),paintress=[p for p in meshes if 'paintress' in p.lower()])))
        runtime.session.close()
finally:lock.close();sdk.SessionTransport=old
