"""Private v28 native-hair experiment; does not alter installed SDK/settings."""
from pathlib import Path
import json, os, sys, time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/native-hair-v49'
GAME = Path('S:/SteamLibrary/steamapps/common/Expedition 33')
sys.path.insert(0, str(OUT / 'src'))
os.environ['E33_ASSET_LIBRARY'] = str(ROOT / 'dist/eye-material-candidate/assets')
import expedition33.sdk as sdk
from expedition33.mods import ModLoader
from expedition33.mod_lock import ModRootLock
from expedition33.controller_commands import CommandServer, Command
from expedition33.lease_policy import statistics, configure

original = sdk.SessionTransport
sdk.SessionTransport = lambda **kw: original(_executable=OUT / 'build/release/research-probe-mesh-v49/research_probe.exe')

def record(event, value):
    with (OUT / 'live-events.jsonl').open('a', encoding='utf8') as f:
        f.write(json.dumps(dict(time=time.time(), event=event, value=value)) + '\n')
    return value

lock = ModRootLock(GAME / 'SDK')
try:
    with sdk.Session(multiple_pause_entries=True) as session, ModLoader(OUT / 'mods', session=session) as loader:
        configure(session, hard_limit=1024, owner_quota=256, cleanup_reserve=64)
        for name in ('SDKManagement', 'CatalogModels'):
            loader.load(name)
            loader.enable(name, console=True)
        model = loader._loaded['CatalogModels'][1]
        def status():
            return record('status', dict(model=model.status(), leases=statistics(session), pid=session.pid, registry=loader.registry.views()))
        server = CommandServer({
            'hair.start': Command('model', lambda: record('start', model.select_replacement('ayane',True))),
            'eye.2b': Command('model', lambda: record('eye-2b', model.select_replacement('2b',True))),
            'hair.normal': Command('model', lambda: record('normal', model.select_replacement('ayane'))),
            'hair.stop': Command('model', lambda: record('stop', model.destroy())),
            'hair.status': Command('inspect', status),
            'hair.inspect': Command('inspect', lambda: __import__('wardrobe_hair_inspection').inspect(session)),
            'hair.diagnostics': Command('inspect', lambda: record('diagnostics', model.model.render_probe())),
            'sdk.shutdown': Command('lifecycle', loader.request_stop),
        }, capabilities={'model', 'inspect', 'lifecycle'})
        try:
            connection = server.write_connection(OUT / 'connection')
            record('ready', dict(pid=session.pid, connection=str(connection)))
            while not loader.stop_requested:
                server.poll(); loader.poll();
                state=repr(model.last)
                if state!=locals().get('last_state'):record('transition',model.last);last_state=state
                time.sleep(.01)
            time.sleep(.3)
        finally:
            server.close()
            model.destroy()
            record('model-cleanup', statistics(session))
finally:
    lock.close()
