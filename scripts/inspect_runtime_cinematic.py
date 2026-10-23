"""Read-only runtime cinematic feasibility probe; never attaches a controller.

Observes reflected interfaces and checks their schemas against the existing
Python invocation codec. Schema acceptance is NOT native dispatch validation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch
from expedition33.invocation import _parameter_schema
from expedition33 import _pod_values
from expedition33.values import read_values_with_references
from expedition33.values import StoredArray
from expedition33.cinematics.original_game_action import controller_context


INTERFACES = {
    'SkeletalMeshComponent': ('GetAnimInstance', 'PlayAnimation', 'SetAnimation',
        'SetAnimationMode', 'GetAnimationMode', 'Stop', 'IsPlaying', 'SetSkeletalMeshAsset'),
    'AnimInstance': ('Montage_Play', 'Montage_Stop', 'Montage_IsPlaying',
        'Montage_GetPosition', 'Montage_SetPosition', 'Montage_GetIsStopped'),
    'Actor': ('K2_GetActorLocation', 'K2_GetActorRotation', 'K2_TeleportTo',
        'K2_SetActorLocationAndRotation', 'K2_DestroyActor', 'SetActorTickEnabled',
        'GetComponentByClass', 'GetActorForwardVector', 'SetActorEnableCollision'),
    'SceneComponent': ('K2_GetComponentToWorld', 'K2_SetWorldTransform'),
    'GameplayStatics': ('BeginDeferredActorSpawnFromClass', 'FinishSpawningActor',
        'CreateSound2D', 'SpawnSound2D', 'GetPlayerCameraManager'),
    'Controller': ('GetViewTarget', 'SetIgnoreMoveInput', 'SetIgnoreLookInput'),
    'PlayerController': ('SetViewTargetWithBlend',),
    'PlayerCameraManager': ('GetCameraLocation', 'GetCameraRotation', 'GetFOVAngle'),
    'CameraComponent': ('SetFieldOfView',),
    'AudioComponent': ('Play', 'Stop', 'SetPaused', 'SetVolumeMultiplier'),
    'ActorComponent': ('K2_DestroyComponent', 'GetOwner'),
    'MovieSceneSequencePlayer': ('Play', 'Pause', 'Stop', 'SetPlayRate',
        'GetCurrentTime', 'SetPlaybackPosition', 'GetBoundObjects', 'SetDisableCameraCuts'),
    'LevelSequenceActor': ('SetBinding', 'AddBinding', 'ResetBindings', 'SetSequence'),
    'LevelSequencePlayer': ('CreateLevelSequencePlayer',),
}


def object_row(catalog, obj):
    return dict(path=catalog.path_name(obj), class_name=obj.class_name,
                index=obj.index, serial=obj.serial)


def inspect_schema(catalog, obj):
    """Inspect one signature without constructing a session or invoking a call."""
    row = object_row(catalog, obj)
    try:
        descriptor = describe(catalog, (obj,))[obj.index]
        row['function'] = dict(descriptor.function)
        row['allocation_extent'] = descriptor.owners[0]['size']
        row['parameters'] = [dict(p) for p in descriptor.properties if p['flags'] & 0x80]
        # Enumerate all missing struct codecs: the normal planner reports the
        # first error only (e.g. Rotator before the HitResult output).
        row['unregistered_structs'] = sorted({catalog.path_name(catalog.by_index[p['struct_index']])
            for p in row['parameters'] if p['type'] == 'StructProperty'
            and catalog.path_name(catalog.by_index[p['struct_index']]) not in _pod_values.PROFILES})
        try:
            _parameter_schema(catalog, obj, descriptor, pod_values=True,
                text_values=True, string_values=True, enum_values=True)
            row['python_codec'] = 'accepted_schema_only'
        except (ValueError, RuntimeError) as error:
            row['python_codec'] = 'rejected'
            row['codec_error'] = str(error)
    except Exception as error:
        row['inspection_error'] = str(error)
    return row


def inspect(pid):
    if type(pid) is not int or not 0 < pid <= 0xffffffff:
        raise ValueError('Expected a positive game process ID')
    catalog = capture()
    if catalog.pid != pid:
        raise RuntimeError('Game PID changed; no retry')
    report = dict(schema=1, pid=pid, read_only=True, controller_attached=False,
                  captured_at_utc=datetime.now(timezone.utc).isoformat(),
                  inspector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  dispatched=False, objects_spawned=False,
                  native_game_thread_dispatch_verified=False,
                  schema_acceptance_is_not_runtime_success=True,
                  interfaces=[], missing=[], candidates={}, component_state=[])
    try:
        context = controller_context(SimpleNamespace(pid=pid))
        report['world_path'] = context['world_path']
    except Exception as error:
        report['context_error'] = str(error)
    targets = []
    for owner, names in INTERFACES.items():
        for name in names:
            matches = [o for o in catalog.objects if o.class_name == 'Function'
                       and o.name == name and catalog.by_index[o.outer_index].name == owner
                       and catalog.path_name(catalog.by_index[o.outer_index]).startswith('/Script/')]
            if len(matches) == 1:
                targets.append(matches[0])
            else:
                report['missing'].append(dict(owner=owner, function=name, matches=len(matches)))
    with ReadBatch(pid):
        # Per-function errors are explicit; no invocation or metadata bypass.
        for obj in targets:
            report['interfaces'].append(inspect_schema(catalog, obj))
        prefix = report.get('world_path', '') + ':'
        for cls in ('SkeletalMeshComponent', 'AnimInstance', 'AnimSequence',
                    'AnimMontage', 'CameraActor', 'CineCameraActor', 'SoundWave',
                    'LevelSequence', 'LevelSequencePlayer'):
            try:
                all_objects = [o for o in catalog.select(cls) if not o.object_flags & 0x30]
                current = [o for o in all_objects if catalog.path_name(o).startswith(prefix)]
                selected = current if cls in ('SkeletalMeshComponent', 'AnimInstance',
                    'CameraActor', 'CineCameraActor', 'LevelSequencePlayer') else all_objects
                report['candidates'][cls] = dict(count=len(selected),
                    objects=[object_row(catalog, o) for o in selected[:24]], truncated=len(selected)>24)
                if cls == 'SkeletalMeshComponent':
                    # Prefer the player's components over unrelated world enemies.
                    current.sort(key=lambda o: (
                        'BP_jRPG_Character_World' not in catalog.path_name(o),
                        any(s in o.name for s in ('Hair', 'Face')), o.index))
                    for component in current[:8]:
                        state = object_row(catalog, component)
                        report['component_state'].append(state)
                        values, observed = read_values_with_references(catalog, component,
                            fields=('AnimationMode', 'AnimClass', 'AnimScriptInstance', 'SkinnedAsset'))
                        state['values'] = {key[1]: object_row(observed, value)
                            if hasattr(value, 'class_index') else value
                            if value is None or type(value) in (str, bool, int, float) else repr(value)
                            for key, value in values.values.items()}
                        state['errors'] = {key[1]: str(value) for key, value in values.errors.items()}
            except Exception as error:
                report['candidates'][cls] = dict(error=str(error))
    try:
        after = controller_context(SimpleNamespace(pid=pid))
        report['context_consistent'] = 'context_error' not in report and after == context
    except Exception as error:
        report['context_consistent'] = False
        report['final_context_error'] = str(error)
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['result'] = 'inspection_only_playback_not_implemented'
    report['petank_assets'] = [object_row(catalog, o) for o in catalog.objects
        if o.class_name in ('SkeletalMesh', 'AnimSequence', 'AnimMontage')
        and 'Petank' in catalog.path_name(o)]
    report['demo_assets'] = []
    player_class = catalog.by_index[catalog.find_class('Player').index]
    with ReadBatch(pid):
        player_descriptor = describe(catalog, (player_class,))[player_class.index]
    report['player_controller_field'] = dict(next(p for p in player_descriptor.properties if p['name']=='PlayerController'))
    idle_candidates = [o for o in catalog.objects if o.class_name == 'AnimSequence'
        and ('Idle' in o.name or 'idle' in o.name) and not o.object_flags & 0x30][:80]
    with ReadBatch(pid):
        for obj in catalog.objects:
            if obj.name not in ('SK_Petank', 'Petank_ENM_ElementalGrunt_IdleLooping3') and obj not in idle_candidates:
                continue
            if obj.class_name not in ('SkeletalMesh', 'AnimSequence'):
                continue
            row = object_row(catalog, obj)
            fields = ('Skeleton', 'Notifies', 'bEnableRootMotion') if obj.class_name == 'AnimSequence' else ('Skeleton',)
            values, observed = read_values_with_references(catalog, obj, fields=fields)
            row['values'] = {key[1]: object_row(observed, value) if hasattr(value, 'class_index')
                else dict(length=value.length, copied_count=len(value.items)) if isinstance(value, StoredArray)
                else value if value is None or type(value) in (str, bool, int, float) else repr(value)
                for key, value in values.values.items()}
            row['errors'] = {key[1]: str(error) for key, error in values.errors.items()}
            metadata = describe(catalog, (catalog.by_index[obj.class_index],))[obj.class_index]
            row['field_schema'] = [dict(p) for p in metadata.properties if p['name'] in fields]
            report['demo_assets'].append(row)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.pid)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(output=str(args.output), pid=report['pid'],
        interfaces=len(report['interfaces']), missing=len(report['missing']), dispatched=False)))


if __name__ == '__main__':
    main()
