"""Arm the existing pause test, then verify restoration after controller loss.

begin runs in the persistent console with Cinematics open. Terminate only the
reported controller PID externally, wait for its native transport to exit, and
run verify in a fresh controller. No destroyed replay object is dereferenced.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy

from expedition33._scope import SessionScope
from expedition33.catalog import capture
from expedition33.values import read_object_reference

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'evidence/audio-pause-disconnect-live.json'


def persist(report):
    OUTPUT.write_text(json.dumps(report, indent=2), encoding='utf8')


def begin(mod):
    global pause_test
    pause_test = runpy.run_path(str(ROOT / 'scripts/verify_original_audio_pause.py'))
    context = pause_test['begin'].__globals__
    # Preserve the earlier Escape evidence rather than overwriting it.
    context['save'] = lambda: None
    result = pause_test['begin'](mod)
    report = dict(result)
    report.update(controller_pid=os.getpid(), game_pid=context['scope'].pid,
                  components=[[o.index, o.serial, o.address] for o in context['components']],
                  reference=dict(context['context']['report']))
    # Refresh after arming. Strong retention need not assign a weak serial;
    # record zero honestly if this build still reports it.
    catalog = capture()
    identities = []
    for index, serial, address in report['components']:
        obj = catalog.by_index.get(index)
        if obj is None or obj.address != address or obj.serial != serial:
            context['scope'].close()
            raise RuntimeError('Cannot seal retained component identity')
        identities.append([obj.index, obj.serial, obj.address])
    report['components'] = identities
    persist(report)
    if report['before'] == report['paused']:
        context['scope'].close()
        raise RuntimeError('No observable pause transition; disconnect test not armed')
    return {k: v for k, v in report.items() if k != 'reference'}


def verify(mod):
    report = json.loads(OUTPUT.read_text(encoding='utf8'))
    if os.getpid() == report['controller_pid']:
        raise RuntimeError('Verification requires a different controller')
    scope = SessionScope(mod.session)
    try:
        if scope.pid != report['game_pid']:
            raise RuntimeError('Game relaunched; cannot prove restoration in prior session')
        catalog = capture()
        def resolve(identity):
            index, serial, address = identity
            obj = catalog.by_index.get(index)
            if obj is None or (obj.serial, obj.address) != (serial, address):
                raise RuntimeError('Original identity changed; cannot prove restoration')
            return obj
        original = resolve(report['reference']['original'])
        gi = resolve(report['reference']['gi'])
        observed, catalog = read_object_reference(catalog, gi, catalog.by_index[gi.class_index],
                                                  'InteractiveMusicSystem')
        report['original_reference_restored'] = observed is not None and all(
            getattr(observed, key) == getattr(original, key) for key in ('index', 'serial', 'address'))
        cls = next(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
        fn = next(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'GetPlayState')
        planner = scope.invocation_planner(catalog=catalog)
        states = []
        for identity in report['components']:
            obj = resolve(identity)
            with planner.prepare(obj, fn).invoke(refresh_from_result=True) as result:
                value = result.return_value
                states.append(dict(index=obj.index, name=value.name, value=value.value))
        report['after_disconnect'] = states
        report['original_states_restored'] = states == report['before']
    finally:
        scope.close()
    saves = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
    hashes = {str(p.relative_to(saves)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in saves.rglob('*.sav')}
    report['save_hashes_unchanged'] = hashes == report['reference']['before_hashes']
    report['verified_by_controller_pid'] = os.getpid()
    persist(report)
    return {k: v for k, v in report.items() if k != 'reference'}
