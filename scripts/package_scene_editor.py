"""Explicit local Scene Editor addon and required SDK Management mod only."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_mods import build_all,archive

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',type=int,default=27);parser.add_argument('--revision',type=int,default=0);args=parser.parse_args()
    if args.revision<0:raise ValueError('Invalid package revision')
    destination=ROOT/(f'dist/scene-editor-v{args.version}'+(f'-r{args.revision}' if args.revision else ''))
    destination.mkdir(parents=True,exist_ok=False)
    manifest=build_all(ROOT/'mods',destination/'SDK_Mods',include={'SceneEditor','SDKManagement'})
    expected={'SceneEditor':{'assets.py','palette.py','palette.json','scene.py','runtime.py','registry.py','hud.py','timeline.py','view.py','mod.py','sample.scene.json','README.txt'},'SDKManagement':{'mod.py','LICENSE'}}
    for row in manifest['mods']:
        candidate=archive['read_candidate'](destination/'SDK_Mods'/row['archive'],row['sha256'])
        names={n for n,_ in candidate.files}
        if names!=expected[row['folder']]:raise ValueError('Unexpected nested mod content: '+str(names))
        for name,data in candidate.files:
            target=destination/'verified-mods'/row['folder']/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for relative in (f'build/release/runtime-session-cinematic-v{args.version}/runtime_session_cinematic_v{args.version}.dll',f'build/release/research-probe-cinematic-v{args.version}/research_probe.exe'):
        target=destination/'candidate'/Path(relative).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
    rows=[dict(path=p.relative_to(destination).as_posix(),size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(destination.rglob('*')) if p.is_file()]
    (destination/'MANIFEST.json').write_text(json.dumps(dict(schema=1,native_version=args.version,purpose='Local Scene Editor addon; requires matching development SDK source/runtime',files=rows),indent=2)+'\n',encoding='utf8')
    for row in rows:
        if hashlib.sha256((destination/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Bundle integrity mismatch')
    print(json.dumps(dict(destination=str(destination),verified_files=len(rows),mods=[r['folder'] for r in manifest['mods']])))

if __name__=='__main__':main()
