"""Explicit local cinematic candidate bundle; never inventory the game folder."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_mods import build_all,archive

def main():
    destination=ROOT/'dist/runtime-cinematic-demo-v12'
    destination.mkdir(parents=True,exist_ok=False)
    manifest=build_all(ROOT/'mods',destination/'SDK_Mods',include={'RuntimeCinematicDemo'})
    row=manifest['mods'][0]
    candidate=archive['read_candidate'](destination/'SDK_Mods'/row['archive'],row['sha256'])
    if {name for name,_ in candidate.files}!={'mod.py','README.txt'}:
        raise ValueError('Unexpected nested mod archive inputs')
    for name,data in candidate.files:
        target=destination/'verified-mods/RuntimeCinematicDemo'/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    inputs=(
        'build/release/runtime-session-cinematic-v12/runtime_session_cinematic_v12.dll',
        'build/release/research-probe-cinematic-v12/research_probe.exe',
        'mods/RuntimeCinematicDemo/README.txt',
    )
    for relative in inputs:
        target=destination/'candidate'/Path(relative).name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
    files=[dict(path=str(p.relative_to(destination)).replace('\\','/'),
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
        for p in sorted(destination.rglob('*')) if p.is_file()]
    (destination/'MANIFEST.json').write_text(json.dumps(dict(schema=1,
        purpose='Local development candidate; requires matching development SDK source/runtime',
        native_version=12,files=files),indent=2)+'\n')
    for entry in files:
        if hashlib.sha256((destination/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Bundle integrity failure')
    print(json.dumps(dict(destination=str(destination),verified_files=len(files),nested_entries=[n for n,_ in candidate.files])))

if __name__=='__main__':main()
