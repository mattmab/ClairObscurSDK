"""One installable scene-placement preview, from curated public inputs only."""
import argparse,hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from package_release_candidate import build as build_sdk
from package_mods import build_all
from package_rc18 import OPTIONAL,audit,validate_entry
from license_manifest import validate_source,verify_archive

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0-rc18-scene-placement-preview1'
NATIVE=231

def build(destination,*,live_verified=False):
    destination=Path(destination).resolve()
    result=build_sdk(destination,VERSION)
    stage=destination/'game-root';sdk=stage/'SDK'
    reader=ROOT/f'build/release/research-probe-cinematic-v{NATIVE}-retirement/research_probe.exe'
    dll=ROOT/f'build/release/runtime-session-cinematic-v{NATIVE}/runtime_session_cinematic_v{NATIVE}.dll'
    inputs=[(reader,f'build/{folder}/research_probe.exe') for folder in ('research-probe','readonly-worker','research-probe-picto-v4',*[f'research-probe-cinematic-v{v}-retirement' for v in range(216,NATIVE+1)])]
    inputs.append((dll,f'build/runtime-session-cinematic-v{NATIVE}/'+dll.name))
    for source,name in inputs:
        data=source.read_bytes();validate_entry('SDK/'+name,data)
        target=sdk/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    mods=build_all(ROOT/'mods',destination/'mods-complete',include=OPTIONAL|{'SDKManagement','IntrospectionHarness','LiveObjectViewer'})
    for name in ['manifest.json',*[row['archive'] for row in mods['mods']]]:
        shutil.copy2(destination/'mods-complete'/name,stage/'SDK_Mods'/name)
    manifest_path=sdk/'release-manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest['mods']=mods['mods']
    manifest['sdk_files']={p.relative_to(sdk).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(sdk.rglob('*')) if p.is_file() and p!=manifest_path}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    instructions=('' if live_verified else 'UNVERIFIED CANDIDATE: live flight, placement and playback validation is pending.\nDo not distribute as a tested release.\n\n')+(
        'ClairObscurSDK scene placement preview\n\n'
        'Close the game. Extract SDK, SDK_Mods and Sandfall into the Expedition 33 game folder; merge folders and replace package files.\n'
        'Launch normally through Steam. Mods is available at title and in Pause. Enable Scene Editor, then load a save.\n'
        'Press Insert: Game sequences, select a sequence, Load source, Open timeline.\n'
        'Start playback or seek inside a camera shot. Flight editor opens the 3D scene view.\n'
        'Hold right mouse: mouse look and WASD movement; E/Q or Space/Ctrl move up/down; Shift moves faster.\n'
        'Place whole scene here moves the scene one thousand centimeters in front of the view. Save retains the placement.\n'
        'Track library > Scene position also accepts exact [X,Y,Z] world coordinates in centimeters; Apply moves the scene.\n'
        'Seek to frame provides precise scrubbing. Drag scrubbing remains under investigation in this preview. Play resumes with the authored camera at the saved placement.\n'
        'Back to editor closes the temporary scene and restores gameplay.\n\n'
        'Includes SDK and 13 public mods. No saved games, personal settings, custom maps, logs or private testing harnesses are included.\n'
        'This is a development preview. Scene placement supports translation. Original level geometry and campaign dependencies are not imported.\n'
        'Game-authored scenes may depend on original actors, level effects or scripted events; broad scene compatibility remains under development.\n')
    (stage/'INSTALL.txt').write_text(instructions,encoding='utf8')
    archive=Path(result['archive'])
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for path in sorted(stage.rglob('*')):
            if not path.is_file():continue
            name=path.relative_to(stage).as_posix();data=path.read_bytes();validate_entry(name,data);out.writestr(name,data)
    result.update(bytes=archive.stat().st_size,mods=len(mods['mods']),native=NATIVE,
        validation_status='live-verified' if live_verified else 'awaiting-live-flight-placement-playback',
        sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),audited_entries=audit(archive),
        license_manifest_verification=verify_archive(archive,validate_source(ROOT)))
    (destination/'SHA256SUMS.txt').write_text(result['sha256']+'  '+archive.name+'\n',encoding='utf8')
    (destination/'artifact.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    parser.add_argument('--live-verified',action='store_true',help='Use only after verifying this build in-engine')
    args=parser.parse_args();print(json.dumps(build(args.destination,live_verified=args.live_verified)))
