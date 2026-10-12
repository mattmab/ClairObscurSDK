"""Invoke the game's inspected Pause-menu safe-location action, once.

Run in the existing console session: py import recover_native_spawn; recover_native_spawn.run(sdk)
This performs native travel, not an SDK coordinate write. It may autosave.
"""
import json
from pathlib import Path

from expedition33 import _query
from expedition33.catalog import capture_matching


def run(session):
    session._check()
    catalog = capture_matching(session.pid, names=('TeleportToSafeLocation',),
                               classes=('WBP_PauseMenu_C',))
    targets = [o for o in catalog.objects if o.class_name == 'WBP_PauseMenu_C'
               and not o.object_flags & 0x10
               and catalog.path_name(o).startswith('/Engine/Transient.GameEngine_')]
    if len(targets) != 1:
        raise RuntimeError('Expected one initialized native Pause menu')
    target = targets[0]
    functions = [o for o in catalog.objects if o.name == 'TeleportToSafeLocation'
                 and o.class_name == 'Function' and o.outer_index == target.class_index]
    if len(functions) != 1:
        raise RuntimeError('Native safe-location function is unavailable or ambiguous')
    function = functions[0]
    _, rows = _query(['--describe', str(session.pid),
                     f'{function.index}:{function.serial}:{function.address:x}'])
    info = [r for r in rows if r['event'] == 'function_metadata']
    if len(info) != 1 or info[0]['params_size'] != 0:
        raise RuntimeError('Inspected zero-argument recovery signature changed')
    # Include reflected local-variable type descriptors for the ordinary planner.
    # No local memory is read, copied, or supplied as a parameter.
    names = sorted({r[k] for r in rows if r['event'] == 'property_metadata'
                    for k in ('struct_name', 'property_class_name', 'enum_name') if k in r})
    if names:
        catalog = catalog.with_observations(capture_matching(session.pid, names=names))
    report = {'pid': session.pid, 'target': catalog.path_name(target),
              'function': catalog.path_name(function), 'dispatch_returned': False,
              'placement_verified': False}
    output = Path(__file__).resolve().parents[1] / 'evidence/native-spawn-recovery-attempt.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf8')
    try:
        with session.invocation_planner(catalog=catalog, selected_results=True) as planner:
            with planner.prepare(target, function).invoke():
                report['dispatch_returned'] = True
    except Exception as error:
        report['error'] = str(error)
        report['outcome'] = getattr(error, 'outcome', 'preparation_failed')
        raise
    finally:
        output.write_text(json.dumps(report, indent=2), encoding='utf8')
    return report
