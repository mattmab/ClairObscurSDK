"""Build RC25 from an explicit, hashed input list and reviewed mod packages."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from license_manifest import validate_source, verify_archive
from package_mods import build_all
from package_rc18 import audit, validate_entry

CORE = frozenset(('SDKManagement', 'IntrospectionHarness', 'LiveObjectViewer'))
PUBLIC_MODS = CORE | frozenset(('BattleRetry', 'CatalogModels', 'Cinematics',
    'ContinentFlight', 'E33WorldBuilder', 'EnemyHealth', 'EnemySpawner', 'MapTravel',
    'PictoEditor', 'SceneEditor', 'SkillDamage', 'Statistics', 'StoryPacks',
    'WorldBuilderMapLoader', 'ConsoleExample', 'ExampleMod', 'KeybindExample',
    'ManagementExample'))
VERSION = '0.1.0-rc25'

# Some previously distributed mods still resolve their reader by its legacy
# install path. All aliases ship the current reader, including map value reads.
READ_WORKER_FOLDERS = (
    'readonly-worker-values-v2',
    'readonly-worker-strings-v1',
    'readonly-worker-values-v3-skill-damage',
    'readonly-worker',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def portable(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Input paths must be portable relative paths')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Input path escapes its root')
    return name


def inputs(document, root=ROOT):
    if document.get('schema') != 1 or document.get('version') != VERSION:
        raise ValueError('Unrecognized release input inventory')
    files = document.get('files', [])
    if not files:
        raise ValueError('Release input inventory is empty')
    result, seen = [], set()
    for row in files:
        source, target = portable(row['source']), portable(row['target'])
        if target.casefold() in seen:
            raise ValueError('Duplicate release target')
        seen.add(target.casefold())
        if not (target.startswith('SDK/') or target == 'Sandfall/Binaries/Win64/version.dll'):
            raise ValueError('Unapproved release target')
        path = root / source
        if not path.resolve().is_relative_to(root.resolve()) or any(
                p.is_symlink() or p.is_junction() for p in (path, *path.parents) if p != root.parent):
            raise ValueError('Redirected input')
        data = path.read_bytes()
        if sha(data) != row['sha256']:
            raise ValueError('Release input changed: ' + source)
        validate_entry(target, data)
        result.append((target, data))
    required = ('SDK/scripts/run_release_sdk.py', 'SDK/runtime/python.exe',
        'SDK/build/research-probe-cinematic-v318/research_probe.exe',
        'SDK/build/runtime-session-cinematic-v318/runtime_session_cinematic_v318.dll',
        'Sandfall/Binaries/Win64/version.dll')
    required += tuple(f'SDK/build/{folder}/research_probe.exe' for folder in READ_WORKER_FOLDERS)
    missing = sorted(set(required) - {name for name, _ in result})
    if missing:
        raise ValueError('Missing required release inputs: ' + ', '.join(missing))
    if set(document.get('mods', {})) != PUBLIC_MODS:
        raise ValueError('Public mod inventory differs from approved set')
    return result


def unpack_standard_library(runtime, reviewed):
    """Flatten only the hash-pinned CPython stdlib and redirect its import path."""
    original = dict(reviewed['runtime']['files'])
    archive_name, pth_name = 'python313.zip', 'python313._pth'
    source = runtime / archive_name
    pth = runtime / pth_name
    pth_bytes = pth.read_bytes()
    if (sha(source.read_bytes()) != original.pop(archive_name) or
            sha(pth_bytes) != original[pth_name] or not pth_bytes.startswith(b'python313.zip\r\n')):
        raise ValueError('Unreviewed CPython standard library or import configuration')
    seen = set()
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            name = 'Lib/' + portable(info.filename)
            if name.casefold() in seen or info.orig_filename != info.filename:
                raise ValueError('Invalid standard-library member: ' + name)
            seen.add(name.casefold())
            data = archive.read(info)
            target = runtime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            original[name] = sha(data)
    replacement = b'Lib' + pth_bytes[len(b'python313.zip'):]
    pth.write_bytes(replacement)
    original[pth_name] = sha(replacement)
    source.unlink()
    return original


def zip_tree(path, stage, *, unpacked_stdlib=False):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in sorted(stage.rglob('*')):
            if item.is_file():
                archive.write(item, item.relative_to(stage).as_posix())
    return {'archive': path.name, 'sha256': sha(path.read_bytes()),
            'bytes': path.stat().st_size, 'audited_entries': audit(path, unpacked_stdlib=unpacked_stdlib)}


def build(destination, inventory, *, unpack_core=False, nexus=False):
    unpack_core = unpack_core or nexus
    document = json.loads(Path(inventory).read_text(encoding='utf8'))
    reviewed = validate_source(ROOT)
    payload = inputs(document)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    stage = destination / 'game-root'
    for name, data in payload:
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    built = build_all(ROOT / 'mods', destination / 'all-mods', include=PUBLIC_MODS)
    for row in built['mods']:
        if row['sha256'] != document['mods'][row['folder']]:
            raise ValueError('Mod changed after input review: ' + row['folder'])
    (stage / 'SDK_Mods').mkdir()
    optional = destination / 'optional-root'
    (optional / 'SDK_Mods').mkdir(parents=True)
    for row in built['mods']:
        folder = stage if row['folder'] in CORE else optional
        archive_path = destination / 'all-mods' / row['archive']
        if unpack_core and row['folder'] in CORE:
            loose_root = stage / 'SDK/bundled-mods' / row['folder']
            with zipfile.ZipFile(archive_path) as archive:
                for entry in row['files']:
                    name = portable(entry['path'])
                    path = loose_root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
            row['layout'] = 'loose'
        else:
            shutil.copy2(archive_path, folder / 'SDK_Mods' / row['archive'])
    sdk = stage / 'SDK'
    archive_name = 'Expedition33-SDK-0.1.0-rc25.zip'
    if unpack_core:
        archive_name = 'Expedition33-SDK-0.1.0-rc25-unpacked-core.zip'
        readme = sdk / 'README.md'
        with readme.open('a', encoding='utf8') as stream:
            stream.write('\n## Unpacked core mods\n\n'
                         'This ZIP installs the three core mods under `SDK/bundled-mods`. '
                         'Those copies take precedence over archived copies of the same mods '
                         'from previous installs. Optional `.sdkmod` files still go in `SDK_Mods`.\n')
    runtime_hashes = None
    if nexus:
        archive_name = 'Expedition33-SDK-0.1.0-rc25-Nexus.zip'
        runtime_hashes = unpack_standard_library(sdk / 'runtime', reviewed)
        with (sdk / 'THIRD_PARTY_NOTICES.md').open('a', encoding='utf8') as stream:
            stream.write('\nThis Nexus edition expands the official Python standard-library ZIP under '
                         '`runtime/Lib` and updates `python313._pth` to use that directory. '
                         'The runtime executables and libraries retain their upstream bytes. '
                         'The dependency manifest records the official input and the release manifest '
                         'records the installed file hashes.\n')
    release = dict(version=VERSION, native_runtime=318,
        sdk_files={p.relative_to(sdk).as_posix(): sha(p.read_bytes()) for p in sorted(sdk.rglob('*')) if p.is_file()},
        mods=[r for r in built['mods'] if r['folder'] in CORE],
        bootstrap_sha256=sha((stage / 'Sandfall/Binaries/Win64/version.dll').read_bytes()),
        supported_game_sha256='218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618')
    (sdk / 'release-manifest.json').write_text(json.dumps(release, indent=2)+'\n', encoding='utf8')
    for folder in (stage, optional):
        shutil.copy2(ROOT / 'LICENSE', folder / 'LICENSE')
    (optional / 'README.txt').write_text('Install SDK RC25 first. Extract the SDK_Mods folder into the game root. Enable optional mods in the SDK Mods menu. Existing saves and settings are not included.\n', encoding='utf8')
    artifacts = [zip_tree(destination / archive_name, stage, unpacked_stdlib=nexus),
                 zip_tree(destination / 'Expedition33-OptionalMods-RC25.zip', optional)]
    artifacts[0]['licenses'] = verify_archive(destination / artifacts[0]['archive'], reviewed,
                                             runtime_hashes=runtime_hashes)
    (destination / 'artifacts.json').write_text(json.dumps(artifacts, indent=2)+'\n', encoding='utf8')
    return artifacts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--unpack-core', action='store_true', help='Ship the three core mods as plain files')
    parser.add_argument('--nexus', action='store_true', help='Ship core mods and Python stdlib as plain files')
    args = parser.parse_args()
    print(json.dumps(build(args.destination, args.inputs, unpack_core=args.unpack_core, nexus=args.nexus), indent=2))
