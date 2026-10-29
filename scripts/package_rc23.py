"""Package a frozen, qualified SDK manifest and explicit public source inputs."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from package_rc18 import audit, validate_entry, source_inventory, admitted_source
from expedition33.mod_archive import inspect_bytes
from runtime_snapshot import verify_sources,verify_mod

VERSION = '0.1.0-rc23'
MODS = {'CatalogModels', 'Cinematics', 'ContinentFlight', 'E33WorldBuilder',
        'EnemySpawner', 'IntrospectionHarness', 'LiveObjectViewer', 'MapTravel',
        'PictoEditor', 'SceneEditor', 'SDKManagement', 'Statistics', 'WorldBuilderMapLoader'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_input(root, name):
    validate_entry(name, b'')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or redirected release input: ' + name)
    data = path.read_bytes()
    validate_entry(name, data)
    return data


def write_zip(path, entries):
    if len(entries) != len({name.casefold() for name in entries}):
        raise ValueError('Duplicate archive input')
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items()):
            validate_entry(name, data)
            archive.writestr(name, data)
    return audit(path)


def build(frozen_root, output):
    frozen_root = Path(frozen_root).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output directory')
    base = json.loads(read_input(frozen_root, 'SDK/release-manifest.json'))
    document = copy.deepcopy(base)
    document['version'] = VERSION
    if {row['archive'] for row in document['mods']} != {name + '.sdkmod' for name in MODS}:
        raise ValueError('Expected the exact public mod inventory')
    expected_native = 'build/runtime-session-cinematic-v251/runtime_session_cinematic_v251.dll'
    if expected_native not in document['sdk_files']:
        raise ValueError('Qualified runtime 251 is required')
    entries = {}
    for name, expected in document['sdk_files'].items():
        data = read_input(frozen_root, 'SDK/' + name)
        if digest(data) != expected:
            raise ValueError('Frozen SDK hash mismatch: ' + name)
        entries['SDK/' + name] = data
    for row in document['mods']:
        name = 'SDK_Mods/' + row['archive']
        data = read_input(frozen_root, name)
        summary = inspect_bytes(data, row['sha256']).summary()
        if summary != {key: row[key] for key in summary}:
            raise ValueError('Frozen mod summary mismatch: ' + name)
        entries[name] = data
    bootstrap = 'Sandfall/Binaries/Win64/version.dll'
    data = read_input(frozen_root, bootstrap)
    if digest(data) != document['bootstrap_sha256']:
        raise ValueError('Frozen bootstrap hash mismatch')
    entries[bootstrap] = data
    if entries['SDK/scripts/run_release_sdk.py']!=read_input(ROOT,'scripts/run_release_sdk.py'):
        raise ValueError('Qualified launcher differs from release source')
    entries['SDK/release-manifest.json'] = (json.dumps(document, indent=2) + '\n').encode()
    notes = read_input(ROOT, 'docs/RELEASE_0.1.0_RC23.md')
    entries['RC23-README.md'] = notes

    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    pending = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    if any(name and admitted_source(name) for name in pending):
        raise ValueError('Review and track public sources before packaging')
    sources = {name: read_input(ROOT, name) for name in source_inventory(tracked)}
    verify_sources(ROOT,entries,[n for n in sources if n.startswith('src/')])
    for mod in MODS:
        prefix='mods/'+mod+'/'
        verify_mod(ROOT/prefix,entries['SDK_Mods/'+mod+'.sdkmod'],[n[len(prefix):] for n in sources if n.startswith(prefix)])
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    # Preserve the exact qualified Python/mod snapshot separately from development
    # sources; no installed settings, caches or directory enumeration is used.
    for name, data in entries.items():
        if name.startswith('SDK_Mods/') or (name.startswith('SDK/') and name.endswith(('.py', '.json', '.png'))):
            sources['qualified-runtime/' + name] = data
    sources['RC23-SOURCE.txt'] = ('Source commit: ' + commit + '\n'
        'Build native: scripts/build-rc23-native.cmd from an x64 VS tools prompt.\n'
        'The qualified-runtime directory records the exact released Python and mod inputs.\n'
        'Package: scripts/package_rc23.py FROZEN_GAME_ROOT NEW_OUTPUT_DIRECTORY\n').encode()

    output.mkdir(parents=True)
    artifacts = {}
    def package(name, contents):
        count = write_zip(output / name, contents)
        blob = (output / name).read_bytes()
        artifacts[name] = dict(sha256=digest(blob), bytes=len(blob), audited_entries=count)
    package('Expedition33-SDK-' + VERSION + '.zip', entries)
    optional = {name: data for name, data in entries.items() if name.startswith('SDK_Mods/')}
    optional['LICENSE'] = read_input(ROOT, 'LICENSE')
    optional['README.md'] = notes
    package('Expedition33-OptionalMods-RC23.zip', optional)
    for mod in ('SceneEditor', 'Cinematics', 'EnemySpawner', 'E33WorldBuilder', 'MapTravel', 'WorldBuilderMapLoader'):
        name = 'SDK_Mods/' + mod + '.sdkmod'
        package(mod + '-RC23.zip', {name: entries[name], 'LICENSE': optional['LICENSE'], 'README.md': notes})
    package('AssetConverter-RC23.zip', {name: read_input(ROOT, 'tools/asset_converter/' + name)
        for name in ('LICENSE', 'README.txt', 'convert.py', 'eye_materials.py', 'run.py')})
    package('ClairObscurSDK-rc23-source.zip', sources)
    (output / 'GITHUB_RELEASE.md').write_bytes(notes)
    (output / 'SHA256SUMS.txt').write_text(''.join(row['sha256'] + '  ' + name + '\n'
        for name, row in sorted(artifacts.items())), encoding='utf8')
    (output / 'artifacts.json').write_text(json.dumps(artifacts, indent=2) + '\n', encoding='utf8')
    return dict(version=VERSION, commit=commit, artifacts=artifacts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frozen_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.frozen_root, args.output)))
