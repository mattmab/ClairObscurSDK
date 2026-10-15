"""Install the verified RC7 archive payload with a reversible file journal."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

GAME = Path('S:/SteamLibrary/steamapps/common/Expedition 33')
ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'dist/rc7-final/game-root'
BACKUP = ROOT / 'backups/rc7-live-validation/install'
sys.path.insert(0, str(GAME / 'SDK/src'))
from expedition33.mod_lock import ModRootLock


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((STAGE / 'SDK/release-manifest.json').read_text())
    for name, digest in manifest['sdk_files'].items():
        assert sha(STAGE / 'SDK' / name) == digest, name
    lock = ModRootLock(GAME / 'SDK')
    try:
        BACKUP.mkdir(parents=True, exist_ok=False)
        journal = []
        sources = [(p, p.relative_to(STAGE)) for p in STAGE.rglob('*') if p.is_file()]
        sources += [(ROOT / 'dist/rc7-final/world-builder/E33WorldBuilder.sdkmod', Path('SDK_Mods/E33WorldBuilder.sdkmod'))]
        for source, relative in sources:
            target = GAME / relative
            if target.exists() and sha(source) == sha(target):
                continue
            existed = target.exists()
            if existed:
                saved = BACKUP / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            journal.append({'path': relative.as_posix(), 'existed': existed, 'sha256': sha(source)})
            (BACKUP / 'journal.json').write_text(json.dumps(journal, indent=2))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        print(json.dumps({'version': manifest['version'], 'changed_files': len(journal), 'backup': str(BACKUP)}))
    finally:
        lock.close()


if __name__ == '__main__':
    main()
