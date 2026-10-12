"""No-play test of native music reference restoration, including disconnect.

begin(mod) requires the open Cinematics panel. Finish after Escape, or compare
the persisted original identity with a fresh reader after controller shutdown.
No music function, sequence playback, or save mutation is performed.
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33._scoped_assignment import NativeScopedAssignment
from expedition33.catalog import capture
from expedition33.values import read_object_reference, read_values, StoredArray, StoredMap
from expedition33 import _decode_query
from expedition33.values import _decode_values

ROOT = Path(__file__).resolve().parents[1]
SAVES = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')

def hashes():
    return {str(p.relative_to(SAVES)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SAVES.rglob('*.sav')}

def save():
    (ROOT / 'evidence/music-reference-owner-live.json').write_text(json.dumps(report, indent=2), encoding='utf8')

def begin(mod):
    global scope, owner, catalog, gi, gi_cls, original, report, audio_owner
    if mod.native.menu.panel.state != 'open': raise RuntimeError('Open Cinematics first')
    scope = SessionScope(mod.session)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'playback_attempted': False,
              'before_hashes': hashes(), 'pid': scope.pid,
              'leases_before': repr(scope._session._lease_command('lease-status'))}
    def unique(rows):
        rows = tuple(rows)
        if len(rows) != 1: raise ValueError('Ambiguous music identity')
        return rows[0]
    try:
        catalog = capture()
        cls = unique(o for o in catalog.objects if o.name == 'BP_InteractiveMusicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
        gi = unique(o for o in catalog.objects if o.class_name == 'BP_jRPG_GI_Custom_C' and not o.name.startswith('Default__'))
        gi_cls = catalog.by_index[gi.class_index]
        original, catalog = read_object_reference(catalog, gi, gi_cls, 'InteractiveMusicSystem')
        report['original'] = [original.index, original.serial, original.address]
        report['gi'] = [gi.index, gi.serial, gi.address]
        planner = scope.invocation_planner(catalog=catalog)
        default = unique(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
        cls_static = unique(o for o in catalog.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
        fn = unique(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == cls_static.index)
        result = planner.prepare(default, fn, ObjectClass=cls, Outer=gi).invoke(refresh_from_result=True)
        detached = result.return_value
        catalog = planner._catalog
        if detached is None or detached.class_index != cls.index or detached.outer_index != gi.index:
            raise ValueError('Detached music ownership mismatch')
        report['detached'] = [detached.index, detached.serial, detached.address]
        query = subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'), '--read-values',
                                str(scope.pid), f'{detached.index}:{detached.serial}:{detached.address:x}'],
                               capture_output=True, text=True, timeout=30, check=True)
        start, observations = _decode_query(query.stdout)
        values = _decode_values(catalog, detached, start, observations)
        for name in ('InteractiveMusicByContext', 'AudioComponentsToUnspawn'):
            selected = [v for k, v in values.values.items() if k[1] == name]
            if len(selected) != 1 or not isinstance(selected[0], (StoredArray, StoredMap)) or selected[0].items:
                raise ValueError(f'Detached music container not verified empty: {name}')
        audio_owner = None
        if getattr(scope._session._transport, 'music_audio_protocol', 0) == 1:
            from expedition33._music_audio_owner import NativeMusicAudioOwner
            audio_class = unique(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
            component_class = unique(o for o in catalog.objects if o.name == 'ActorComponent' and o.class_name == 'Class')
            audio_default = unique(o for o in catalog.objects if o.name == 'Default__AudioComponent')
            stop_fn = unique(o for o in catalog.objects if o.name == 'Stop' and o.outer_index == audio_class.index)
            destroy_fn = unique(o for o in catalog.objects if o.name == 'K2_DestroyComponent' and o.outer_index == component_class.index)
            stop = planner.prepare(audio_default, stop_fn)._plan
            destroy = planner.prepare(audio_default, destroy_fn, Object=audio_default)._plan
            audio_owner = NativeMusicAudioOwner(scope)
            audio_owner.prepare(original, detached, audio_class, stop, destroy)
            report['native_audio_owner'] = audio_owner.status()
        owner = NativeScopedAssignment(scope)
        owner.open(catalog, gi, gi_cls, 'InteractiveMusicSystem', original, detached)
        current, catalog = read_object_reference(catalog, gi, gi_cls, 'InteractiveMusicSystem')
        report['private_reference_confirmed'] = current.address == detached.address
        report['native_owner'] = owner.status()
        save()
        return {k: v for k, v in report.items() if k != 'before_hashes'}
    except BaseException:
        scope.close()
        raise

def finish():
    session = scope._session
    report['native_after_menu_close'] = owner.status()
    if audio_owner is not None: report['native_audio_after_menu_close'] = audio_owner.status()
    current, _ = read_object_reference(catalog, gi, gi_cls, 'InteractiveMusicSystem')
    report['original_restored_before_python_close'] = current is not None and (
        current.index,current.serial,current.address)==(original.index,original.serial,original.address)
    scope.close()
    report['leases_after'] = repr(session._lease_command('lease-status'))
    report['save_hashes_unchanged'] = hashes() == report['before_hashes']
    save()
    return {k: v for k, v in report.items() if k != 'before_hashes'}
