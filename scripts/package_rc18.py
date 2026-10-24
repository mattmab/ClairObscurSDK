"""Curated RC18 artifacts; explicit public mod and source inventories only."""
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_release_candidate import build as build_sdk, PUBLIC_ASSETS
from package_world_builder import build as build_builder
from package_mods import build_all

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL = {'CatalogModels', 'Cinematics', 'ContinentFlight', 'WorldBuilderMapLoader',
            'E33WorldBuilder', 'PictoEditor', 'Statistics', 'MapTravel', 'SceneEditor', 'EnemySpawner'}
SOURCE_ROOTS = {'src', 'native', 'gpu', 'mods', 'scripts', 'tests', 'docs', 'licenses', 'tools'}
# Historical local research utilities are retained in Git, but are not release
# build inputs. Model experiments require a particular user Downloads asset;
# the verification/recording scripts use a particular user's save directory.
SOURCE_EXCLUDES = {
    'scripts/ayane_projection.py': 'local model projection experiment',
    'scripts/inspect_ayane_rig.py': 'local model rig experiment',
    'scripts/prepare_ayane.py': 'local model preparation experiment',
    'scripts/record_cinematic_menu_state.py': 'local save-backed diagnostic capture',
    'scripts/verify_audio_pause_disconnect.py': 'local save-backed live verification',
    'scripts/verify_media_open.py': 'local save-backed live verification',
    'scripts/verify_music_disconnect.py': 'local save-backed live verification',
    'scripts/verify_music_reference_owner.py': 'local save-backed live verification',
    'scripts/verify_sequence_creation.py': 'local save-backed live verification',
    'scripts/verify_sequence_interruption.py': 'local save-backed live verification',
    'scripts/verify_sequence_load.py': 'local save-backed live verification',
}
SOURCE_FIXTURES = {'evidence/v53-frame-time-schema.json','evidence/coverage-compiled-data-schema.json','evidence/scene-editor/clip-baseline-v52.json','evidence/scene-editor/mask-animation-inspection.json'}
# One-way fingerprints protect local-only identifiers without publishing their
# plaintext (including split/concatenated spellings). Each candidate is bounded;
# scanner state is capped and no matched text is returned or logged.
PRIVATE_FINGERPRINTS = (
    ('word', 14, '0a4d7acc7cb1e2b4508607ddda07347d9e012161411fbc2abec5835c47cb4d9e'),
    ('hex', 32, '534999460239c13248bc01984d4467bf622b1475bcb846be39c83201f6f621f8'),
)


PUBLIC_SOURCE_MODS=OPTIONAL|{'SDKManagement','IntrospectionHarness','LiveObjectViewer',
    'ConsoleExample','CustomModel','ExampleMod','KeybindExample','ManagementExample','RuntimeCinematicDemo'}
ROOT_FILES={'.gitattributes','.gitignore','DEVELOPMENT.md','LICENSE','README.md','THIRD_PARTY_NOTICES.md',
    'launch-cinematics.cmd','launch-flight.cmd','launch-native-mods.cmd','launch-picto.cmd','launch-sdk.cmd','launch.cmd'}
REQUIRED_SOURCES={
    'gpu/bridge.h','scripts/build-early-lifecycle-runtime.cmd','scripts/build-readonly-worker-values.cmd','scripts/build-rc18-native.cmd','scripts/package_rc18.py',
    'scripts/run_release_sdk.py','scripts/prepare_runtime.py','scripts/build-bootstrap.cmd',
    'scripts/package_release_candidate.py','scripts/package_mods.py','scripts/package_world_builder.py',
    'docs/RELEASE_0.1.0_RC18.md','src/expedition33/_stable_lease.py',
    'src/expedition33/_metadata_stabilization.py','src/expedition33/title_menu.py',
    'src/expedition33/title_management.py','src/expedition33/process_title_ui.py',
    'src/expedition33/admission_monitor.py','src/expedition33/world_admission.py','src/expedition33/ui_admission.py',
    'src/expedition33/process_ui.py','src/expedition33/pause_preparation.py','src/expedition33/process_ui_routes.py',
    'src/expedition33/ui_shell_proof.py','src/expedition33/world_lifecycle.py',
    'src/expedition33/process_console.py','native/menu_open_pipeline.h',
    'native/stable_lease_runtime.h','native/metadata_stabilization_target.h',
    'native/metadata_stabilization_protocol.h','native/metadata_stabilization_runtime.h',
    'mods/WorldBuilderMapLoader/context_observer.py','mods/WorldBuilderMapLoader/prepared_maps.py',
    'mods/WorldBuilderMapLoader/lifecycle.json',
    'native/retired_world_gate.h','native/retired_world_getter.h','native/retired_world_release.h',
    'native/retired_world_target.h','native/retired_world_fixture.cpp',
    'native/menu_open_pipeline_fixture.cpp','native/session_specimen_filter.h',
    'native/console_color_status_protocol.h','native/runtime_console_colors.h',
    'native/console_colors/callback_cpp_guard.h','native/console_colors/native_adapter.h',
    'native/console_colors/scrollback_renderer.h','native/console_colors/semantic_colors.h',
    'native/console_colors/target_adapter.h','native/console_colors/target_fingerprints.h',
    'native/console_colors/target_owned_text_bridge.h',
    'native/lease_release_batch_protocol.h','native/lease_release_batch_runtime.h',
    'src/expedition33/_lease_release_batch.py','src/expedition33/_menu_latency.py',
    'src/expedition33/core_startup.py','src/expedition33/console_startup.py',
    'src/expedition33/frontend_rejection.py','src/expedition33/mod_lifecycle.py',
    'src/expedition33/startup_metrics.py'} | set(PUBLIC_ASSETS)
FORBIDDEN_PARTS={'settings','logs','backups','local-backups','custom-source','__pycache__','.git',
    'sdk-capability-review','qabattleexplorer','qabattleexplorer.sdkmod'}


def contains_private_identifier(data):
    folded=data.lower()
    # ASCII identifiers encoded as UTF-16LE/BE become the same bounded candidate
    # after NUL removal. Raw UTF-8/ASCII is checked independently as well.
    views=(folded,folded.replace(b'\0',b'')) if b'\0' in folded else (folded,)
    for kind,length,digest in PRIVATE_FINGERPRINTS:
        if (kind not in ('word','hex') or type(length) is not int or not 1<=length<=128
                or type(digest) is not str or re.fullmatch('[a-f0-9]{64}',digest) is None):
            raise ValueError('Invalid private fingerprint guard configuration')
        alphabet=rb'[a-z]' if kind=='word' else rb'[a-f0-9]'
        pattern=rb'(?=('+alphabet+rb'{'+str(length).encode('ascii')+rb'}))'
        seen=set()
        for view in views:
            for match in re.finditer(pattern,view):
                candidate=match.group(1)
                if candidate in seen:continue
                if hashlib.sha256(candidate).hexdigest()==digest:return True
                if len(seen)>=4096:seen.clear()
                seen.add(candidate)
    return False


def validate_entry(name,data,*,runtime_bytecode=False):
    name=name.replace('\\','/');parts=name.casefold().split('/')
    if (set(parts)&FORBIDDEN_PARTS or '..' in parts or name.startswith('/') or ':' in name or
            name.casefold().endswith('.e33map.json') or
            (name.casefold().endswith('.pyc') and not runtime_bytecode) or
            'e33mapoverlays.sdkmod' in parts):
        raise ValueError('Excluded release path: '+name)
    if (contains_private_identifier(name.casefold().encode('utf8'))
            or contains_private_identifier(data)):
        raise ValueError('Excluded local content in release input')


def audit(path):
    count=0
    def scan(archive,runtime_bytecode=False):
        nonlocal count
        if archive.testzip() is not None:raise ValueError('Corrupt archive')
        seen=set()
        for entry in archive.infolist():
            if entry.is_dir():continue
            name=entry.filename.replace('\\','/')
            if name.casefold() in seen:raise ValueError('Duplicate archive path: '+name)
            seen.add(name.casefold());data=archive.read(entry)
            validate_entry(name,data,runtime_bytecode=runtime_bytecode);count+=1
            if name.casefold().endswith(('.sdkmod','.zip')):
                with zipfile.ZipFile(io.BytesIO(data)) as nested:
                    scan(nested,name=='SDK/runtime/python313.zip')
    with zipfile.ZipFile(path) as archive:scan(archive)
    return count


def admitted_source(name):
    if name in SOURCE_EXCLUDES:return False
    if name=='mods/README.md':return True
    parts=Path(name).parts
    if parts and parts[0]=='mods':return len(parts)>2 and parts[1] in PUBLIC_SOURCE_MODS
    return (name in ROOT_FILES or name in SOURCE_FIXTURES or
            (len(parts)>1 and parts[0] in SOURCE_ROOTS))


def source_inventory(tracked):
    selected=[]
    for name in sorted(filter(None,tracked)):
        if admitted_source(name):
            validate_entry(name,b'');selected.append(name)
    missing=REQUIRED_SOURCES-set(selected)
    if missing:raise ValueError('Required public source inputs must be tracked before release: '+', '.join(sorted(missing)))
    return tuple(selected)


def build(output, *, source_only=False):
    tracked = subprocess.check_output(['git', '-c', 'safe.directory='+str(ROOT), 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    untracked=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    pending=sorted(name for name in filter(None,untracked) if admitted_source(name))
    if pending:raise ValueError('Review and track all public source inputs before packaging: '+', '.join(pending))
    sources=[]
    for name in source_inventory(tracked):
        path=ROOT/name
        if not path.is_file():raise ValueError('Source input missing: '+name)
        data=path.read_bytes();validate_entry(name,data);sources.append((name,data))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=source_only)
    if not source_only:
        sdk = build_sdk(output / 'sdk', '0.1.0-rc18')
        builder = build_builder(output / 'builder',requires_sdk='0.1.0-rc18')
        for result in (sdk, builder):
            shutil.copy2(result['archive'], output / Path(result['archive']).name)
        build_all(ROOT / 'mods', output / 'optional', include=OPTIONAL)
        for folder, filename in (('MapTravel', 'MapTravel-0.2.4.zip'),
                                 ('WorldBuilderMapLoader', 'WorldBuilderMapLoader-RC18.zip')):
            with zipfile.ZipFile(output / filename, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(output / 'optional' / (folder + '.sdkmod'), 'SDK_Mods/' + folder + '.sdkmod')
                readme=ROOT/'mods'/folder/'README.txt'
                if readme.is_file():archive.write(readme,'README.txt')
                else:archive.writestr('README.txt','Install SDK 0.1.0-rc18 first. WorldBuilderMapLoader replaces the legacy E33MapOverlays package; keep only one map loader installed. User maps/settings are preserved and are not included.\n')
                archive.write(ROOT / 'LICENSE', 'LICENSE')
        with zipfile.ZipFile(output / 'Expedition33-OptionalMods-RC18.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for folder in sorted(OPTIONAL):
                archive.write(output / 'optional' / (folder + '.sdkmod'), 'SDK_Mods/' + folder + '.sdkmod')
            archive.write(ROOT / 'LICENSE', 'LICENSE')
        for folder in ('SceneEditor', 'EnemySpawner'):
            with zipfile.ZipFile(output / (folder+'-RC18.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.write(output/'optional'/(folder+'.sdkmod'), 'SDK_Mods/'+folder+'.sdkmod')
                archive.write(ROOT/'LICENSE', 'LICENSE')
                archive.writestr('README.txt', 'Install SDK 0.1.0-rc18 first. Extract beside Sandfall, then enable '+folder+' in Pause > Mods. See the RC18 release notes for experimental limits.\n')
        with zipfile.ZipFile(output / 'AssetConverter-RC18.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in ('LICENSE', 'README.txt', 'convert.py', 'eye_materials.py', 'run.py'):
                archive.write(ROOT / 'tools/asset_converter' / name, name)
        shutil.copyfile(ROOT / 'docs/RELEASE_0.1.0_RC18.md', output / 'GITHUB_RELEASE.md')
    source = output / 'ClairObscurSDK-rc18-source.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name,data in sources:archive.writestr(name,data)
        archive.writestr('RC18-SOURCE.txt', 'Source commit: ' + subprocess.check_output(
            ['git', '-c', 'safe.directory='+str(ROOT), 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() + '\n'
            'Build native: scripts/build-rc18-native.cmd from an x64 Visual Studio tools prompt.\n'
            'Prepare runtime/bootstrap using scripts/prepare_runtime.py and scripts/build-bootstrap.cmd.\n'
            'Package release: scripts/package_rc18.py NEW_DIRECTORY\n')
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
