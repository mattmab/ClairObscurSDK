"""Install the local v55 hairstyle candidate locally, with rollback copies."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('S:/SteamLibrary/steamapps/common/Expedition 33')
SDK = GAME / 'SDK'
SOURCE = ROOT / 'dist/native-hair-v55'
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.mod_archive import build_bytes, read_candidate
from expedition33.mod_lock import ModRootLock

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out = ROOT / 'dist/native-hair-installed' / time.strftime('%Y%m%d-%H%M%S')
    stage = out / 'mod'
    stage.mkdir(parents=True)
    for path in (SOURCE / 'mods/CatalogModels').iterdir():
        if path.is_file():
            shutil.copy2(path, stage / path.name)
    mod = stage / 'mod.py'
    text = mod.read_text(encoding='utf8')
    text = text.replace("version='0.3.0'", "version='0.3.1-local-hair'")
    text = text.replace('2B with native hairstyle (test)', '2B with game hairstyle (experimental)')
    text = text.replace('Ayane with native hairstyle (test)', 'Ayane with game hairstyle (experimental)')
    mod.write_text(text, encoding='utf8')
    browser = stage / 'browser.py'
    text = browser.read_text(encoding='utf8')
    text = text.replace("if row.get('replacement'):controls.insert(1,MenuControl(8,'Replace current character',row['available']))", "if row.get('replacement'):\n                controls.insert(1,MenuControl(8,'Replace current character',row['available']))\n                controls.insert(2,MenuControl(9,'Replace with game hairstyle (experimental)',row['available']))")
    text = text.replace("elif token==8:self.model.select_replacement(self.selected)", "elif token==8:self.model.select_replacement(self.selected)\n        elif token==9:self.model.select_replacement(self.selected,True)")
    browser.write_text(text, encoding='utf8')
    readme = stage / 'README.txt'
    readme.write_text('LOCAL DEVELOPMENT CANDIDATE: 0.3.1-local-hair\nRequires the accompanying v55 native runtime; stock public RC6 is insufficient for native hair.\n\nChoose 2B/Ayane with game hairstyle in the mod actions, or select the model in the catalog and choose Replace with game hairstyle. Normal replacement buttons retain the imported model hair. Change native hair using Wardrobe; the replacement follows the selected Wardrobe character. Destroy restores native appearance.\n\nExperimental: validated Sciel/Lune handoffs, not every hairstyle, combat or travel. Hair streaming can briefly interrupt the preview. User-owned native-hair asset variants are required; no model assets are included in this archive.\n\n' + readme.read_text(encoding='utf8'), encoding='utf8')
    for p in stage.glob('*.py'):
        compile(p.read_text(encoding='utf8'), str(p), 'exec')
    data, candidate = build_bytes(stage)
    (out / 'CatalogModels.sdkmod').write_bytes(data)
    lock = ModRootLock(SDK)
    try:
        settings_before = {str(p.relative_to(SDK)): digest(p) for p in (SDK/'settings').rglob('*') if p.is_file()}
        manifest = json.loads((SDK/'release-manifest.json').read_text(encoding='utf8'))
        changed = []
        def put(relative, payload):
            target = GAME / relative
            if target.exists() and target.read_bytes() == payload:
                return
            if target.exists():
                backup = out / 'backup' / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            changed.append(relative)
        for relative in ('src/expedition33/procedural_mesh.py', 'build/research-probe-mesh-v55/research_probe.exe', 'build/runtime-session-mesh-v55/runtime_session_mesh_v55.dll'):
            source = SOURCE / relative
            if relative.startswith('build/'):
                source = SOURCE / relative.replace('build/', 'build/release/', 1)
            put('SDK/' + relative, source.read_bytes())
            manifest['sdk_files'][relative] = digest(SDK/relative)
        relative = 'scripts/run_release_sdk.py'
        runner = (SDK/relative).read_text(encoding='utf8')
        assert any(version in runner for version in ('research-probe-mesh-v27','research-probe-mesh-v49','research-probe-mesh-v53','research-probe-mesh-v54','research-probe-mesh-v55'))
        put('SDK/'+relative, runner.replace('research-probe-mesh-v27','research-probe-mesh-v55').replace('research-probe-mesh-v49','research-probe-mesh-v55').replace('research-probe-mesh-v53','research-probe-mesh-v55').replace('research-probe-mesh-v54','research-probe-mesh-v55').encode('utf8'))
        manifest['sdk_files'][relative] = digest(SDK/relative)
        put('SDK_Mods/CatalogModels.sdkmod', data)
        # Local user-owned assets only: preserve corrected eyes and provide hair-omitted variants.
        for model in ('2b', 'ayane', '2b-native-hair', 'ayane-native-hair'):
            source = ROOT / 'dist/eye-material-candidate/assets' / model
            for p in source.rglob('*'):
                if p.is_file():
                    put('SDK_Assets/'+model+'/'+p.relative_to(source).as_posix(), p.read_bytes())
        manifest['local_candidate'] = 'native-hair-v55 / CatalogModels 0.3.1-local-hair'
        put('SDK/release-manifest.json', (json.dumps(manifest,indent=2)+'\n').encode('utf8'))
        assert settings_before == {str(p.relative_to(SDK)): digest(p) for p in (SDK/'settings').rglob('*') if p.is_file()}
        read_candidate(GAME/'SDK_Mods/CatalogModels.sdkmod', candidate.sha256)
        result = dict(backup=str(out/'backup'), archive_sha256=candidate.sha256, changed=changed, settings_preserved=True)
        (out/'install.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(dict(backup=result['backup'], changed_files=len(changed), settings_preserved=True, archive_sha256=candidate.sha256)))
    finally:
        lock.close()

if __name__ == '__main__':
    main()
