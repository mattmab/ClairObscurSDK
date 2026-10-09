"""Validate a local development candidate's bytes, exclusions and isolated launcher."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('metadata',type=Path)
    args=parser.parse_args()
    metadata=json.loads(args.metadata.read_text(encoding='utf-8-sig'))
    root=Path(metadata['directory']).resolve()
    archive=Path(metadata['archive']).resolve()
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['sha256']
    manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    expected=set(manifest['files'])|{'MANIFEST.json'}
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual==expected
    forbidden={'.git','evidence','logs','settings','__pycache__'}
    for relative,digest in manifest['files'].items():
        path=(root/relative).resolve()
        assert path.is_relative_to(root) and not forbidden.intersection(Path(relative).parts)
        assert path.suffix.lower() not in ('.pak','.utoc','.ucas','.pdb')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    for version in (13,14,15,16,17):
        assert f'build/runtime-session-v{version}/runtime_session_v{version}.dll' in expected
        assert f'build/research-probe-v{version}/research_probe.exe' in expected
    with zipfile.ZipFile(archive) as zipped:
        assert len(zipped.namelist())==len(expected) and set(zipped.namelist())==expected
        for name in expected:
            assert zipped.read(name)==(root/name).read_bytes()
    help_text=subprocess.check_output([sys.executable,'-I','-S','-B',str(root/'scripts/run_sdk.py'),'--help'],text=True)
    assert all(flag in help_text for flag in ('--menu-ownership', '--button-references', '--button-actions', '--multi-controls'))
    assert {'scripts/e33_agent.py', 'scripts/e33_introspect.py',
            'src/expedition33/introspection/agent.py'}.issubset(expected)
    agent_help=subprocess.check_output([sys.executable,'-I','-S','-B',str(root/'scripts/e33_agent.py'),'--help'],text=True)
    assert all(command in agent_help for command in ('status', 'mods', 'action', 'enable', 'disable', 'logs'))
    print(json.dumps(dict(directory=str(root),archive=str(archive),files=len(expected),
                         archive_sha256=metadata['sha256'],manifest_verified=True,zip_bytes_verified=True,
                         exclusions_verified=True,isolated_launcher_help=True,isolated_agent_help=True,
                         live_bundle_validation=False),indent=2))


if __name__=='__main__': main()
