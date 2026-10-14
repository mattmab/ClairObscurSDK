"""Assemble a curated game-root RC ZIP; never includes developer state."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_mods import build_all
from license_manifest import validate_source, verify_archive


def build(destination, version):
    reviewed_licenses = validate_source(ROOT)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    stage = destination / 'game-root'
    sdk = stage / 'SDK'
    sdk.mkdir(parents=True)
    def copy(source, relative):
        target = sdk / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, target)
    for source in sorted((ROOT / 'src/expedition33').rglob('*')):
        if source.is_file() and (source.suffix in ('.py', '.json') or source.name == 'LICENSE'):
            copy(source.relative_to(ROOT), source.relative_to(ROOT))
    for source in sorted((ROOT / 'runtime').iterdir()):
        if source.is_file() and source.suffix in ('.exe', '.dll', '.pyd', '.zip', '._pth', '.txt', '.cat'):
            copy(source.relative_to(ROOT), source.relative_to(ROOT))
    copy('scripts/run_release_sdk.py', 'scripts/run_release_sdk.py')
    copy('scripts/sdk_command.py', 'scripts/sdk_command.py')
    copy('docs/INSTALLABLE_RELEASE.md', 'README.md')
    copy('LICENSE', 'LICENSE')
    copy('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md')
    for source in sorted((ROOT / 'licenses').rglob('*')):
        if source.is_file():
            copy(source.relative_to(ROOT), source.relative_to(ROOT))
    for directory in ('research-probe', 'readonly-worker', 'research-probe-picto-v4'):
        copy('build/release/research-probe-mesh-v27/research_probe.exe', f'build/{directory}/research_probe.exe')
    copy('build/release/research-probe-mesh-v27/research_probe.exe', 'build/research-probe-mesh-v27/research_probe.exe')
    copy('build/release/runtime-session-mesh-v27/runtime_session_mesh_v27.dll', 'build/runtime-session-mesh-v27/runtime_session_mesh_v27.dll')
    # Launchers inside SDK are install-relative and never search a dev checkout.
    (sdk / 'launch-sdk.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\python.exe" -I -S -B "%~dp0scripts\\run_release_sdk.py" %*\r\n', encoding='ascii')
    (sdk / 'launch-cinematics.cmd').write_text('@echo off\r\ncall "%~dp0launch-sdk.cmd" %*\r\n', encoding='ascii')
    manifest = build_all(ROOT / 'mods', stage / 'SDK_Mods',
                         include={'SDKManagement', 'IntrospectionHarness', 'LiveObjectViewer'})
    bootstrap = stage / 'Sandfall/Binaries/Win64/version.dll'
    bootstrap.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'build/bootstrap/version.dll', bootstrap)
    files = {str(p.relative_to(sdk)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(sdk.rglob('*')) if p.is_file()}
    release = dict(version=version, sdk_files=files, mods=manifest['mods'],
                   bootstrap_sha256=hashlib.sha256(bootstrap.read_bytes()).hexdigest(),
                   supported_game_sha256='218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618')
    (sdk / 'release-manifest.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf8')
    archive = destination / f'Expedition33-SDK-{version}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                out.write(path, path.relative_to(stage).as_posix())
    license_check = verify_archive(archive, reviewed_licenses)
    result = dict(archive=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  bytes=archive.stat().st_size, mods=len(manifest['mods']))
    result['license_manifest_verification'] = license_check
    (destination / 'artifact.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='New staging directory')
    parser.add_argument('--version', default='0.1.0-rc1')
    args = parser.parse_args()
    if not args.version or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in args.version):
        parser.error('Version must be a portable filename component')
    print(json.dumps(build(args.destination, args.version)))
