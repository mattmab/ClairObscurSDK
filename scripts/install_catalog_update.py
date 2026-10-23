"""Local catalog integration. Back up every replaced file; preserve user settings."""
from pathlib import Path
import sys,json,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.mod_lock import ModRootLock
from expedition33.mod_archive import build_bytes
from expedition33.settings import SettingsStore

def install(game):
    sdk=game/'SDK';backup=ROOT/'dist/catalog-integrated'/('backup-'+time.strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=False)
    lock=ModRootLock(sdk)
    try:
        manifest=json.loads((sdk/'release-manifest.json').read_text())
        for relative in ('release-manifest.json','settings/management.json'):
            destination=backup/'SDK'/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(sdk/relative,destination)
        files={f'src/expedition33/{name}':ROOT/f'src/expedition33/{name}' for name in ('_session.py','_scope.py','procedural_mesh.py','_material_candidates.py')}
        files['scripts/run_release_sdk.py']=ROOT/'scripts/run_release_sdk.py'
        files['build/research-probe-mesh-v27/research_probe.exe']=ROOT/'build/release/research-probe-mesh-v27/research_probe.exe'
        files['build/runtime-session-mesh-v27/runtime_session_mesh_v27.dll']=ROOT/'build/release/runtime-session-mesh-v27/runtime_session_mesh_v27.dll'
        for relative,source in files.items():
            target=sdk/relative
            if target.exists():
                destination=backup/'SDK'/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,destination)
            target.parent.mkdir(parents=True,exist_ok=True)
            # Native DLLs remain mapped until the game exits. Identical bytes
            # require no replacement and must not be opened for writing.
            source_digest=hashlib.sha256(source.read_bytes()).hexdigest()
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=source_digest:
                shutil.copy2(source,target)
            manifest['sdk_files'][relative]=hashlib.sha256(target.read_bytes()).hexdigest()
        archive=game/'SDK_Mods/CatalogModels.sdkmod'
        if archive.exists():shutil.copy2(archive,backup/'CatalogModels.sdkmod')
        data,candidate=build_bytes(ROOT/'mods/CatalogModels');archive.write_bytes(data)
        (ROOT/'dist/catalog-integrated/CatalogModels.sdkmod').write_bytes(data)
        manifest['version']='0.1.0-rc5.catalog3-local'
        (sdk/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
        settings=SettingsStore(sdk/'settings/management.json')
        record=settings.get('sdk.catalog-models');record.update(enabled=True,folder='CatalogModels');settings.save('sdk.catalog-models',record)
        result=dict(backup=str(backup),version=manifest['version'],archive_sha256=candidate.sha256,changed=list(files))
        (ROOT/'dist/catalog-integrated/install.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    finally:lock.close()
if __name__=='__main__':install(Path(sys.argv[1]).resolve())
