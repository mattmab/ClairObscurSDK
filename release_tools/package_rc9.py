"""Create RC9 from a hash-verified RC6 plus the tested World Builder adapter.

Inputs are explicit: never sweep a live SDK directory or personal settings.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_thumbnails import identity

PYTHON_OVERLAY = ['src/expedition33/' + name + '.py' for name in
                  ('procedural_mesh', 'assets', 'widgets', '_session', 'multi_controls','lease_policy','_lease_wire')]
PYTHON_OVERLAY += ['scripts/run_release_sdk.py']
NATIVE = ['research-probe-worldbuilder-v52/research_probe.exe',
          'runtime-session-worldbuilder-v52/runtime_session_worldbuilder_v52.dll',
          'thumbnail-worker-v2/thumbnail_worker.dll']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def archive(root, target):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                out.write(p, p.relative_to(root).as_posix())
    with zipfile.ZipFile(target) as check:
        if check.testzip() is not None:
            raise RuntimeError('Corrupt output archive')


def build(rc6, game, project, destination):
    destination.mkdir(parents=True, exist_ok=False)
    baseline = json.loads((rc6 / 'SDK/release-manifest.json').read_text())
    if baseline['version'] != '0.1.0-rc6':
        raise ValueError('Expected stock RC6 baseline')
    for name, expected in baseline['sdk_files'].items():
        if digest(rc6 / 'SDK' / name) != expected:
            raise ValueError('Changed RC6 input: ' + name)
    bootstrap = Path('Sandfall/Binaries/Win64/version.dll')
    if digest(rc6 / bootstrap) != baseline['bootstrap_sha256']:
        raise ValueError('Changed RC6 bootstrap')
    stage = destination / 'game-root'
    sdk = stage / 'SDK'
    for name in baseline['sdk_files']:
        copy(rc6 / 'SDK' / name, sdk / name)
    for row in baseline['mods']:
        source = rc6 / 'SDK_Mods' / row['archive']
        if digest(source) != row['sha256']:
            raise ValueError('Changed RC6 bundled mod')
        copy(source, stage / 'SDK_Mods' / row['archive'])
    copy(rc6 / bootstrap, stage / bootstrap)
    patch = []
    for name in PYTHON_OVERLAY:
        source = game / 'SDK' / name
        patch += list(difflib.unified_diff((rc6 / 'SDK' / name).read_text().splitlines(True),
                                          source.read_text().splitlines(True),
                                          fromfile='a/' + name, tofile='b/' + name))
        copy(source, sdk / name)
    for name in NATIVE:
        source = project / 'build/release' / name
        if digest(source) != digest(game / 'SDK/build' / name):
            raise ValueError('Built/installed adapter mismatch: ' + name)
        copy(source, sdk / 'build' / name)
    for alias in ('research-probe', 'readonly-worker', 'research-probe-picto-v4'):
        copy(project / 'build/release' / NATIVE[0], sdk / 'build' / alias / 'research_probe.exe')
    notes = project / 'release_tools/README.md'
    copy(notes, sdk / 'WORLD_BUILDER_RC9.md')
    files = {p.relative_to(sdk).as_posix(): digest(p) for p in sorted(sdk.rglob('*')) if p.is_file()}
    release = dict(baseline, version='0.1.0-rc9', sdk_files=files,
                   native_candidate='worldbuilder-v52', thumbnail_worker='v2')
    (sdk / 'release-manifest.json').write_text(json.dumps(release, indent=2) + '\n')
    archive(stage, destination / 'Expedition33-SDK-0.1.0-rc9.zip')

    sys.path.insert(0, str(sdk / 'src'))
    from expedition33.mod_archive import build_bytes
    mod, candidate = build_bytes(project / 'mods/E33WorldBuilder')
    mod_stage = destination / 'world-builder'
    mod_stage.mkdir()
    (mod_stage / 'E33WorldBuilder.sdkmod').write_bytes(mod)
    copy(notes, mod_stage / 'README.md')
    copy(sdk / 'LICENSE', mod_stage / 'LICENSE')
    archive(mod_stage, destination / 'E33WorldBuilder-0.29.0-rc9.zip')

    cache = game / 'SDK/settings/E33WorldBuilder/cache/neutral-v1'
    catalog = json.loads((cache / 'catalog.json').read_text())
    thumbs = destination / 'thumbnails'
    thumbs.mkdir()
    images = {}
    for asset in catalog['meshes']:
        key = hashlib.sha256((catalog['build'] + ':neutral-v1b:' + asset).encode()).hexdigest()
        source = cache / (key + '.png')
        if not source.exists():
            continue
        data = source.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (320, 240):
            raise ValueError('Invalid thumbnail: ' + asset)
        image_hash = hashlib.sha256(data).hexdigest()
        copy(source, thumbs / 'images' / (image_hash + '.png'))
        images[asset] = image_hash
    (thumbs / 'thumbnails.json').write_text(json.dumps(dict(version=1, game=identity(game),
        images=images, catalog_count=len(catalog['meshes']),
        missing=[a for a in catalog['meshes'] if a not in images]), indent=2))
    copy(project / 'release_tools/import_thumbnails.py', thumbs / 'import_thumbnails.py')
    copy(notes, thumbs / 'README.md')
    archive(thumbs, destination / 'E33WorldBuilder-thumbnails-rc9.zip')

    # Source needed to reproduce/review the native delta, without reference
    # implementations, local captures, logs, credentials or personal maps.
    source_root = destination / 'source'
    for folder in ('native', 'gpu', 'mods/E33WorldBuilder', 'tests', 'release_tools'):
        for p in (project / folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py', '.cpp', '.h', '.inl', '.json', '.txt', '.md') and '__pycache__' not in p.parts:
                copy(p, source_root / p.relative_to(project))
    for name in ('build.cmd', 'build_thumbnail_worker.cmd'):
        copy(project / name, source_root / name)
    for name in PYTHON_OVERLAY:
        copy(sdk / name, source_root / 'SDK-overlay' / name)
    copy(sdk / 'LICENSE', source_root / 'LICENSE')
    (source_root / 'rc6-to-rc9-python.patch').write_text(''.join(patch))
    archive(source_root, destination / 'E33WorldBuilder-rc9-source.zip')
    outputs = {p.name: dict(sha256=digest(p), bytes=p.stat().st_size)
               for p in sorted(destination.glob('*.zip'))}
    result = dict(version='0.1.0-rc9', images=len(images), catalog=len(catalog['meshes']),
                  missing=len(catalog['meshes']) - len(images), artifacts=outputs)
    (destination / 'artifacts.json').write_text(json.dumps(result, indent=2))
    (destination / 'SHA256SUMS.txt').write_text(''.join(v['sha256'] + '  ' + k + '\n' for k, v in outputs.items()))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rc6', 'game', 'project', 'destination'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.rc6.resolve(), args.game.resolve(), args.project.resolve(), args.destination.resolve()), indent=2))
