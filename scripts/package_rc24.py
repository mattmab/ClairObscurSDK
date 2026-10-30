"""Build separated RC24 artifacts from the verified RC23 runtime and pinned mods."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from package_rc18 import admitted_source, validate_entry, audit
from package_rc23 import digest, read_input, write_zip
from package_mods import build_all

VERSION = '0.1.0-rc24'
CORE = {'SDKManagement', 'IntrospectionHarness', 'LiveObjectViewer'}
OPTIONAL = {'CatalogModels', 'Cinematics', 'ContinentFlight', 'E33WorldBuilder',
            'EnemyHealth', 'EnemySpawner', 'MapTravel', 'PictoEditor', 'SceneEditor',
            'Statistics', 'WorldBuilderMapLoader'}


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def build(frozen_zip, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output directory')
    if git('diff', '--name-only') or git('diff', '--cached', '--name-only'):
        raise ValueError('Commit the reviewed SDK inputs before release packaging')
    pending = git('ls-files', '--others', '--exclude-standard', '-z').split('\0')
    if any(name and admitted_source(name) for name in pending):
        raise ValueError('Track all reviewed public SDK inputs before release packaging')
    # The input is a previously audited release, never an installed game tree.
    audit(frozen_zip)
    with zipfile.ZipFile(frozen_zip) as archive:
        manifest = json.loads(archive.read('SDK/release-manifest.json'))
        document = copy.deepcopy(manifest)
        if 'build/runtime-session-cinematic-v251/runtime_session_cinematic_v251.dll' not in document['sdk_files']:
            raise ValueError('Qualified native runtime 251 required')
        entries = {}
        for name, expected in document['sdk_files'].items():
            data = archive.read('SDK/' + name)
            if digest(data) != expected:
                raise ValueError('Frozen runtime hash mismatch: ' + name)
            # Only public source paths already admitted by the qualified manifest
            # can replace frozen runtime inputs. Native binaries remain unchanged.
            if name.startswith(('src/', 'scripts/')) and name.endswith('.py'):
                data = read_input(ROOT, name)
            entries['SDK/' + name] = data
            document['sdk_files'][name] = digest(data)
        bootstrap = 'Sandfall/Binaries/Win64/version.dll'
        data = archive.read(bootstrap)
        if digest(data) != document['bootstrap_sha256']:
            raise ValueError('Frozen bootstrap hash mismatch')
        entries[bootstrap] = data
    pin = git('rev-parse', 'HEAD', cwd=ROOT / 'mods')
    indexed_pin = git('ls-files', '--stage', 'mods').split()[1]
    if pin != indexed_pin or git('status', '--porcelain', cwd=ROOT / 'mods'):
        raise ValueError('Mods must be clean and pinned in the SDK index')
    output.mkdir(parents=True)
    built = build_all(ROOT / 'mods', output / 'packages', include=CORE | OPTIONAL)
    document['version'] = VERSION
    document['mods'] = [row for row in built['mods'] if row['folder'] in CORE]
    document['mods_repository'] = 'https://github.com/mattmab/ClairObscureSDKMods'
    document['mods_commit'] = pin
    entries['SDK/release-manifest.json'] = (json.dumps(document, indent=2) + '\n').encode()
    for row in document['mods']:
        entries['SDK_Mods/' + row['archive']] = (output / 'packages' / row['archive']).read_bytes()
    notes = read_input(ROOT, 'docs/RELEASE_0.1.0_RC24.md')
    entries['RC24-README.md'] = notes
    artifacts = {}
    def package(name, contents, repository):
        count = write_zip(output / name, contents)
        blob = (output / name).read_bytes()
        artifacts[name] = dict(sha256=digest(blob), bytes=len(blob), audited_entries=count,
                               repository=repository)
    package('Expedition33-SDK-' + VERSION + '.zip', entries, 'sdk')
    optional_entries = {}
    for mod in sorted(OPTIONAL):
        name = 'SDK_Mods/' + mod + '.sdkmod'
        payload = (output / 'packages' / (mod + '.sdkmod')).read_bytes()
        optional_entries[name] = payload
        contents = {name: payload, 'LICENSE': read_input(ROOT / 'mods', 'LICENSE'),
                    'README.md': read_input(ROOT / 'mods', 'README.md')}
        if mod == 'EnemyHealth':
            contents['EnemyHealth-README.txt'] = read_input(ROOT / 'mods', 'EnemyHealth/README.txt')
        package(mod + ('-0.1.4' if mod == 'EnemyHealth' else '-RC24') + '.zip', contents, 'mods')
    optional_entries['README.md'] = read_input(ROOT / 'mods', 'README.md')
    optional_entries['LICENSE'] = read_input(ROOT / 'mods', 'LICENSE')
    package('ClairObscureSDKMods-RC24.zip', optional_entries, 'mods')
    tracked = git('ls-files', '-z').split('\0')
    sources = {name: read_input(ROOT, name) for name in tracked
               if name and name != 'mods' and (admitted_source(name) or name == '.gitmodules')}
    commit = git('rev-parse', 'HEAD')
    sources['RC24-SOURCE.txt'] = ('SDK commit: ' + commit + '\nMods commit: ' + pin + '\n'
        'Clone the SDK with --recurse-submodules for mod integration tests.\n'
        'Native runtime 251 is unchanged from RC23.\n').encode()
    package('ClairObscurSDK-rc24-source.zip', sources, 'sdk')
    mod_sources = {name: read_input(ROOT / 'mods', name)
                   for name in git('ls-files', '-z', cwd=ROOT / 'mods').split('\0') if name}
    package('ClairObscureSDKMods-rc24-source.zip', mod_sources, 'mods')
    for repository in ('sdk', 'mods'):
        (output / (repository + '-SHA256SUMS.txt')).write_text(''.join(
            row['sha256'] + '  ' + name + '\n' for name, row in sorted(artifacts.items())
            if row['repository'] == repository), encoding='utf8')
    (output / 'artifacts.json').write_text(json.dumps(artifacts, indent=2) + '\n', encoding='utf8')
    return dict(version=VERSION, commit=commit, mods_commit=pin, artifacts=artifacts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frozen_zip', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.frozen_zip, args.output)))
