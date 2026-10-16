"""Package RC13 with explicit SDK, mod, catalog-image and committed-source inputs."""
import argparse,hashlib,io,json,shutil,struct,subprocess,zipfile
from pathlib import Path
from package_release_candidate import build as build_sdk
from package_world_builder import build as build_mod
from import_thumbnails import identity
ROOT=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(path):
    count=0
    def scan(z):
        nonlocal count
        for n in z.namelist():
            data=z.read(n);lower=n.lower();count+=1
            assert not any(x in lower for x in ('custom-source/','backup','settings/','logs/','.e33map.')),n
            if n.endswith(('.zip','.sdkmod')):
                with zipfile.ZipFile(io.BytesIO(data)) as nested:scan(nested)
        assert z.testzip() is None
    with zipfile.ZipFile(path) as z:scan(z)
    return count

def build(game,out):
    out.mkdir(parents=True,exist_ok=False)
    sdk=build_sdk(out/'sdk','0.1.0-rc13')
    mod=build_mod(out/'mod')
    for record in (sdk,mod):shutil.copy2(record['archive'],out/Path(record['archive']).name)
    for rel in ('research-probe-worldbuilder-v65-selection/research_probe.exe','runtime-session-worldbuilder-v65-selection/runtime_session_worldbuilder_v65_selection.dll'):
        assert digest(ROOT/'build/release'/rel)==digest(game/'SDK/build'/rel),'Live native mismatch: '+rel
    cache=game/'SDK/settings/E33WorldBuilder/cache/neutral-v1'
    catalog=json.loads((cache/'catalog.json').read_text())
    images={};unique={}
    for asset in catalog['meshes']:
        assert asset.startswith('/Game/')
        key=hashlib.sha256((catalog['build']+':neutral-v1b:'+asset).encode()).hexdigest()
        p=cache/(key+'.png')
        if not p.exists():continue
        data=p.read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(320,240)
        h=hashlib.sha256(data).hexdigest();images[asset]=h;unique[h]=p
    with zipfile.ZipFile(out/'E33WorldBuilder-thumbnails-rc13.zip','w',zipfile.ZIP_DEFLATED) as z:
        for h,p in sorted(unique.items()):z.write(p,'images/'+h+'.png')
        z.writestr('thumbnails.json',json.dumps(dict(version=1,game=identity(game),images=images,catalog_count=len(catalog['meshes']),missing=[a for a in catalog['meshes'] if a not in images]),indent=2))
        z.write(ROOT/'scripts/import_thumbnails.py','import_thumbnails.py')
        z.writestr('README.txt','RC13 neutral asset thumbnails. Close game and SDK before importing.\nExtract this archive, then run:\n"PATH-TO-GAME/SDK/runtime/python.exe" import_thumbnails.py --game "PATH-TO-GAME"\nExisting local thumbnails are preserved. No personal maps or settings included.\n')
    source=out/'ClairObscurSDK-rc13-source.zip'
    subprocess.run(['git','archive','--format=zip','--output='+str(source),'HEAD'],cwd=ROOT,check=True)
    with zipfile.ZipFile(source,'a',zipfile.ZIP_DEFLATED) as z:
        z.writestr('RC13-SOURCE.txt','Source commit: '+subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()+'\nBuild native using an x64 Visual Studio tools prompt and scripts/build-selection-candidate.cmd.\nPrepare the pinned Python runtime with scripts/prepare_runtime.py.\nBuild the bootstrap with scripts/build-bootstrap.cmd.\nPackage SDK using scripts/package_release_candidate.py NEW_DIRECTORY --version 0.1.0-rc13.\nPackage mod using scripts/package_world_builder.py NEW_DIRECTORY.\n')
    result={p.name:dict(sha256=digest(p),bytes=p.stat().st_size,audited_entries=audit(p)) for p in sorted(out.glob('*.zip'))}
    (out/'SHA256SUMS.txt').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in result.items()))
    (out/'artifacts.json').write_text(json.dumps(dict(images=len(images),catalog=len(catalog['meshes']),artifacts=result),indent=2))
    print(json.dumps(dict(images=len(images),catalog=len(catalog['meshes']),artifacts=result),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.game.resolve(),a.output.resolve())
