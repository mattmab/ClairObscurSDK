"""Curated RC17 artifacts; explicit public mod and source inventories only."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_release_candidate import build as build_sdk
from package_world_builder import build as build_builder
from package_mods import build_all

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL = {'CatalogModels', 'Cinematics', 'ContinentFlight', 'E33MapOverlays',
            'E33WorldBuilder', 'PictoEditor', 'Statistics', 'MapTravel', 'SceneEditor', 'EnemySpawner'}
SOURCE_ROOTS = {'src', 'native', 'mods', 'scripts', 'tests', 'docs', 'licenses', 'tools'}
SOURCE_FIXTURES = {'evidence/v53-frame-time-schema.json','evidence/coverage-compiled-data-schema.json','evidence/scene-editor/clip-baseline-v52.json','evidence/scene-editor/mask-animation-inspection.json'}
PRIVATE_NAMES = (b'aza' + b'leabirthday', b'8d8a0e6175305903' + b'b22d67ba1a8e0c47')


def audit(path):
    count = 0
    def scan(archive, runtime_bytecode=False):
        nonlocal count
        assert archive.testzip() is None
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = entry.filename.replace('\\', '/')
            parts = name.lower().split('/')
            assert not set(parts) & {'settings', 'logs', 'backups', 'local-backups',
                                     'custom-source', '__pycache__', '.git'}, name
            assert '..' not in parts and not name.startswith('/') and ':' not in name, name
            assert not name.lower().endswith('.e33map.json'), name
            assert runtime_bytecode or not name.lower().endswith('.pyc'), name
            data = archive.read(entry)
            assert not any(token in name.lower().encode() or token in data.lower()
                           for token in PRIVATE_NAMES), name
            count += 1
            if name.endswith(('.sdkmod', '.zip')):
                with zipfile.ZipFile(io.BytesIO(data)) as nested:
                    scan(nested, name == 'SDK/runtime/python313.zip')
    with zipfile.ZipFile(path) as archive:
        scan(archive)
    return count


def build(output, *, source_only=False):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=source_only)
    if not source_only:
        sdk = build_sdk(output / 'sdk', '0.1.0-rc17')
        builder = build_builder(output / 'builder')
        for result in (sdk, builder):
            shutil.copy2(result['archive'], output / Path(result['archive']).name)
        build_all(ROOT / 'mods', output / 'optional', include=OPTIONAL)
        for folder, filename in (('MapTravel', 'MapTravel-0.2.2.zip'),
                                 ('E33MapOverlays', 'CustomMapLoader-0.2.0.zip')):
            with zipfile.ZipFile(output / filename, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(output / 'optional' / (folder + '.sdkmod'), 'SDK_Mods/' + folder + '.sdkmod')
                archive.write(ROOT / 'mods' / folder / 'README.txt', 'README.txt')
                archive.write(ROOT / 'LICENSE', 'LICENSE')
        with zipfile.ZipFile(output / 'Expedition33-OptionalMods-RC17.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for folder in sorted(OPTIONAL):
                archive.write(output / 'optional' / (folder + '.sdkmod'), 'SDK_Mods/' + folder + '.sdkmod')
            archive.write(ROOT / 'LICENSE', 'LICENSE')
        for folder in ('SceneEditor', 'EnemySpawner'):
            with zipfile.ZipFile(output / (folder+'-RC17.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(output/'optional'/(folder+'.sdkmod'), 'SDK_Mods/'+folder+'.sdkmod')
                archive.write(ROOT/'LICENSE', 'LICENSE')
                archive.writestr('README.txt', 'Install SDK 0.1.0-rc17 first. Extract beside Sandfall, then enable '+folder+' in Pause > Mods. See the RC17 release notes for experimental limits.\n')
        with zipfile.ZipFile(output / 'AssetConverter-RC17.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in ('LICENSE', 'README.txt', 'convert.py', 'eye_materials.py', 'run.py'):
                archive.write(ROOT / 'tools/asset_converter' / name, name)
        shutil.copyfile(ROOT / 'docs/RELEASE_0.1.0_RC17.md', output / 'GITHUB_RELEASE.md')
    tracked = subprocess.check_output(['git', '-c', 'safe.directory='+str(ROOT), 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    source = output / 'ClairObscurSDK-rc17-source.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(filter(None, tracked)):
            parts = Path(name).parts
            if len(parts) == 1 or parts[0] in SOURCE_ROOTS or name in SOURCE_FIXTURES:
                assert (ROOT / name).is_file(), name
                archive.write(ROOT / name, name)
        archive.writestr('RC17-SOURCE.txt', 'Source commit: ' + subprocess.check_output(
            ['git', '-c', 'safe.directory='+str(ROOT), 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() + '\n'
            'Build native: scripts/build-rc17-native.cmd from an x64 Visual Studio tools prompt.\n'
            'Prepare runtime/bootstrap using scripts/prepare_runtime.py and scripts/build-bootstrap.cmd.\n'
            'Package release: scripts/package_rc17.py NEW_DIRECTORY\n')
    result = {}
    for path in sorted(output.glob('*.zip')):
        result[path.name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 bytes=path.stat().st_size, audited_entries=audit(path))
    (output / 'SHA256SUMS.txt').write_text(''.join(
        row['sha256'] + '  ' + name + '\n' for name, row in result.items()), encoding='utf8')
    (output / 'artifacts.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    build(args.output, source_only=args.source_only)
