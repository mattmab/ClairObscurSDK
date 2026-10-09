"""Package our private development SDK, excluding all game data/evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--release', action='store_true', help='Package a validated private v0.1 development release')
args = parser.parse_args()
dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()
if args.release and dirty:
    raise SystemExit('Commit the reviewed source and documentation before packaging a release')
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
name = 'expedition33-0.1.0-' + ('private-' if args.release else 'candidate-') + stamp
destination = root / 'dist' / name
destination.mkdir(parents=True, exist_ok=False)
files = [root / 'README.md', root / 'DEVELOPMENT.md', root / 'launch.cmd', root / 'pyproject.toml']
files.append(root / 'src/expedition33/introspection/LICENSE')
for directory, pattern in [('src', '*.py'), ('mods', '*.py'), ('scripts', '*.py'), ('scripts', '*.cmd'),
                            ('scripts', '*.ps1'), ('native', '*.h'), ('native', '*.cpp'), ('tests', '*.py'), ('research', '*.md')]:
    files.extend((root / directory).rglob(pattern))
for relative in ['build/research-probe/research_probe.exe', 'build/runtime-session/runtime_session_v5.dll',
                 'build/research-probe-v6/research_probe.exe', 'build/runtime-session-v6/runtime_session_v6.dll',
                 'build/research-probe-v7/research_probe.exe', 'build/runtime-session-v7/runtime_session_v7.dll',
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
(destination / 'MANIFEST.json').write_text(json.dumps({'kind': 'private v0.1 development release' if args.release else 'private development candidate, not final release',
    'version': '0.1.0', 'source_base_revision': revision, 'source_worktree_may_include_uncommitted_changes': bool(dirty),
    'python': '3.13.15', 'files': hashes}, indent=2), encoding='utf-8')
archive = root / 'dist' / (name + '.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for path in destination.rglob('*'):
        if path.is_file():
            output.write(path, path.relative_to(destination))
print(json.dumps({'directory': str(destination), 'archive': str(archive),
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
