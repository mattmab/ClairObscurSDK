"""Install the locally built adapter and archive with retained rollback copies.
Run only after orderly SDK controller shutdown. Does not restart the game.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent
GAME = Path('S:/SteamLibrary/steamapps/common/Expedition 33')
SDK = GAME / 'SDK'
sys.path.insert(0, str(SDK / 'src'))
from expedition33.mod_archive import build_bytes
from expedition33.mod_lock import ModRootLock

archive, candidate = build_bytes(ROOT / 'mods/E33WorldBuilder')
(ROOT / 'E33WorldBuilder.sdkmod').write_bytes(archive)
for p in (ROOT / 'mods/E33WorldBuilder').glob('*.py'):
    compile(p.read_text(), str(p), 'exec')
backup = ROOT / 'backups' / time.strftime('%Y%m%d-%H%M%S')
lock = ModRootLock(SDK)
try:
    manifest = json.loads((SDK / 'release-manifest.json').read_text())
    def put(relative, data):
        dst = GAME / relative
        if dst.exists() and dst.read_bytes()==data:return
        if dst.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, saved)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        if relative.startswith('SDK/') and relative != 'SDK/release-manifest.json' and not relative.startswith('SDK/settings/'):
            manifest['sdk_files'][relative[4:]] = hashlib.sha256(data).hexdigest()
    for relative in ('thumbnail-worker-v2/thumbnail_worker.dll', 'research-probe-worldbuilder-v53/research_probe.exe', 'runtime-session-worldbuilder-v53/runtime_session_worldbuilder_v53.dll'):
        put('SDK/build/' + relative, (ROOT / 'build/release' / relative).read_bytes())
    adapter = (SDK / 'src/expedition33/procedural_mesh.py').read_text()
    marker = '    version,op,error,state,owner=HEADER.unpack_from(data)'
    if '# World Builder bounded adapter' in adapter:
        start = adapter.index('    # World Builder bounded adapter')
        end = adapter.index('    if version!=3', start)
        adapter = adapter[:start] + adapter[end:]
    if True:
        adapter = adapter.replace(marker, marker + '''
    # World Builder bounded adapter; independently checked again on game thread.
    if 20 <= op <= 61:
        if version != 3 or error or state or not owner or any(data[24:88]):
            raise ValueError('Builder header')
        if op == 20:
            if any(data[2136:]): raise ValueError('Builder initialization padding')
        elif op in (30,31):
            if any(data[120:2000]) or any(data[2096:]): raise ValueError('Builder scene mutation padding')
        elif op in (33,34,40,45,46,54,57,58):
            if any(data[104:]): raise ValueError('Builder owned deletion padding')
        elif op in (37,38,48):
            if any(data[88:2000]) or any(data[2068:]) or struct.unpack_from('<I',data,2000)[0]>1 or any(c not in b'0123456789abcdef' for c in data[2004:2068]):raise ValueError('Builder thumbnail cache request')
        elif op == 47:
            path=data[2000:2512].split(b'\\0',1)[0]
            if any(data[88:2000]) or any(data[2000+len(path):]) or not path.startswith(b'/Game/') or len(path)>=512:raise ValueError('Builder asset names request')
        elif op in (35,51):
            if any(data[88:2000]) or any(data[2004:]) or struct.unpack_from('<I',data,2000)[0]>250000:raise ValueError('Builder registry page')
        elif op in (21,24,42,44,52,56):
            if any(data[88:2000]) or any(data[2064:]): raise ValueError('Builder motion padding')
            if any(not math.isfinite(v) or abs(v)>(1e7 if op in (42,52) else 10000) for v in struct.unpack_from('<8d',data,2000)):
                raise ValueError('Builder motion bounds')
        elif op in (50,53):
            count=struct.unpack_from('<I',data,2000)[0];stride=192 if op==50 else 16
            if not 1<=count<=(64 if op==50 else 128) or any(data[88:2000]) or any(data[2004:4096]) or any(data[4096+count*stride:]):raise ValueError('Builder bulk padding/count')
            if op==50:
                for i in range(count):
                    at=4096+i*stride;values=struct.unpack_from('<12d',data,at+8)
                    if struct.unpack_from('<I',data,at+4)[0]>1 or any(data[at+104:at+192]) or any(not math.isfinite(v) or abs(v)>1e8 for v in values):raise ValueError('Builder bulk row')
        elif op == 28:
            if any(data[88:20976]) or any(data[20980:]) or struct.unpack_from('<I',data,20976)[0]>1: raise ValueError('Builder automatic flag')
        elif any(data[88:]): raise ValueError('Builder empty command payload')
        return
''')
    put('SDK/src/expedition33/procedural_mesh.py', adapter.encode())
    assets=(SDK/'src/expedition33/assets.py').read_text()
    assets=assets.replace(r"([A-Za-z0-9_]+)\.\1'",r"([A-Za-z0-9_]+)\.(?i:\1)'")
    put('SDK/src/expedition33/assets.py',assets.encode())
    # v23 expands the bounded native delegate pool without changing its wire ABI.
    widgets=(SDK/'src/expedition33/widgets.py').read_text().replace('controls <= 16','controls <= 64').replace('between1 and16 controls','between1 and64 controls')
    put('SDK/src/expedition33/widgets.py',widgets.encode())
    put('SDK/src/expedition33/_ui_batch.py', (ROOT/'sdk_overlays/expedition33/_ui_batch.py').read_bytes())
    session=(SDK/'src/expedition33/_session.py').read_text().replace('type(capacity) is int and capacity == 16)\n\n\ndef supports_traces','type(capacity) is int and capacity in (16,64))\n\n\ndef supports_traces')
    put('SDK/src/expedition33/_session.py',session.encode())
    controls=(SDK/'src/expedition33/multi_controls.py').read_text().replace('len(self.controls) >= 16','len(self.controls) >= 64').replace('len(self.controls) + len(bindings) > 16','len(self.controls) + len(bindings) > 64')
    put('SDK/src/expedition33/multi_controls.py',controls.encode())
    runner = re.sub(r'research-probe-(?:mesh-v55|worldbuilder-v\d+)', 'research-probe-worldbuilder-v53', (SDK / 'scripts/run_release_sdk.py').read_text())
    runner=re.sub(r'hard_limit=\d+, owner_quota=\d+, cleanup_reserve=\d+', 'hard_limit=8192, owner_quota=7000, cleanup_reserve=512',runner)
    for relative in ('lease_policy.py','_lease_wire.py'):
        path=SDK/'src/expedition33'/relative
        put('SDK/src/expedition33/'+relative,path.read_text().replace('4096','8192').encode())
    put('SDK/scripts/run_release_sdk.py', runner.encode())
    put('SDK_Mods/E33WorldBuilder.sdkmod', archive)
    # Preserve every existing preference; only enable the newly requested mod.
    settings = json.loads((SDK / 'settings/management.json').read_text())
    settings['mods']['e33.world-builder'] = {'enabled': True, 'folder': 'E33WorldBuilder'}
    settings['revision'] += 1
    put('SDK/settings/management.json', (json.dumps(settings, indent=2)+'\n').encode())
    manifest['local_candidate'] = 'worldbuilder-v53; retains native-hair-v55 capabilities'
    put('SDK/release-manifest.json', (json.dumps(manifest, indent=2)+'\n').encode())
    (ROOT / 'last-install.json').write_text(json.dumps({'backup': str(backup), 'archive_sha256': candidate.sha256}, indent=2))
    print(json.dumps({'installed': True, 'backup': str(backup), 'archive_sha256': candidate.sha256}))
finally:
    lock.close()
