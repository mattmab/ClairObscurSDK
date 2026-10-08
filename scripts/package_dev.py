"""Create a private development candidate, excluding all game data/evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
name = 'expedition33-0.1.0-candidate-' + stamp
destination = root / 'dist' / name
destination.mkdir(parents=True, exist_ok=False)
files = [root / 'README.md', root / 'DEVELOPMENT.md', root / 'launch.cmd', root / 'pyproject.toml']
for directory, pattern in [('src', '*.py'), ('mods', '*.py'), ('scripts', '*.py'), ('scripts', '*.cmd'),
                            ('scripts', '*.ps1'), ('native', '*.h'), ('native', '*.cpp'), ('tests', '*.py'), ('research', '*.md')]:
    files.extend((root / directory).rglob(pattern))
for relative in ['build/research-probe/research_probe.exe', 'build/runtime-session/runtime_session_v2.dll',
                 'build/scheduling-fixture/scheduling_hook.dll', 'build/fixed-observer/fixed_observer_v1.dll']:
    files.append(root / relative)
hashes = {}
for source in sorted(set(files)):
    relative = source.relative_to(root)
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    hashes[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
(destination / 'MANIFEST.json').write_text(json.dumps({'kind': 'private development candidate, not final release',
    'source_base_revision': revision, 'source_worktree_may_include_uncommitted_changes': True,
    'python': '3.13.15', 'files': hashes}, indent=2), encoding='utf-8')
archive = root / 'dist' / (name + '.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for path in destination.rglob('*'):
        if path.is_file():
            output.write(path, path.relative_to(destination))
print(json.dumps({'directory': str(destination), 'archive': str(archive),
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
