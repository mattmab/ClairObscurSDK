"""Bounded base-UserWidget specimen on an existing persistent v8 session.

Run preflight from the shell; call run(sdk) from the native Python console.
Does not install a menu, change input mode, set focus, or force garbage collection.
"""
from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33.invocation import prepare_call
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def one(rows):
    rows = list(rows)
    assert len(rows) == 1, len(rows)
    return rows[0]


def preflight():
    catalog = capture()
    pc = one(o for o in catalog.select('PlayerController') if not o.object_flags & 0x10)
    cls = catalog.by_index[catalog.find_class('UserWidget').index]
    cdo = one(o for o in catalog.objects if o.name == 'Default__UserWidget' and o.class_index == cls.index)
    library = catalog.find_class('WidgetBlueprintLibrary')
    target = one(o for o in catalog.objects if o.name == 'Default__WidgetBlueprintLibrary' and o.class_index == library.index)

    def function(owner, name):
        return one(o for o in catalog.objects if o.outer_index == catalog.find_class(owner).index and o.name == name)

    functions = {'Create': function('WidgetBlueprintLibrary', 'Create'),
                 'AddToViewport': function('UserWidget', 'AddToViewport'),
                 'IsInViewport': function('Widget', 'IsInViewport'),
                 'RemoveFromParent': function('Widget', 'RemoveFromParent')}
    args = {'WorldContextObject': pc, 'WidgetType': cls, 'OwningPlayer': pc}
    plans = [prepare_call(catalog, target, functions['Create'], args)]
    for name in ('AddToViewport', 'IsInViewport', 'RemoveFromParent'):
        plans.append(prepare_call(catalog, cdo, functions[name], {'ZOrder': 0} if name == 'AddToViewport' else {}))
    summaries = [{'name': plan.function.name, 'entry_rva': hex(plan.entry_rva),
                  'parameter_size': plan.parameter_size,
                  'parameters': [asdict(p) for p in plan.parameters]} for plan in plans]
    (ROOT/'evidence/widget-lifecycle-preflight.json').write_text(json.dumps(
        {'pid': catalog.pid, 'plans': summaries, 'executed': False}, indent=2), encoding='utf-8')
    return catalog, target, functions, args


def holders():
    with redirect_stdout(io.StringIO()):
        runpy.run_path(str(ROOT/'scripts/inspect_gc_owners.py'))['main']()
    data = json.loads((ROOT/'evidence/gc-owners-live.json').read_text())
    return {h['holder_address']: (h['widget']['index'], h['widget']['serial'])
            for group in data['collections'] for h in group['strong_holders']}


def run(session):
    assert session.supports_retained_invocation
    catalog, target, functions, args = preflight()
    assert catalog.pid == session.pid
    baseline = holders()
    evidence = {'pid': catalog.pid, 'baseline_holders': baseline, 'passed': False,
                'focus_changed': False, 'gc_forced': False, 'visible_menu_tested': False}
    scope = SessionScope(session)
    owned, widget, added = None, None, False
    try:
        owned = scope.invoke_retained(target, functions['Create'], **args)
        widget = owned.return_value
        assert widget is not None and widget.class_index == args['WidgetType'].index
        assert widget.index not in catalog.by_index, 'Expected a newly allocated object'
        evidence['created'] = asdict(widget)
        after_create = holders()
        assert len(after_create) == len(baseline) + 1
        assert all(after_create.get(k) == v for k, v in baseline.items())
        assert (widget.index, widget.serial) in after_create.values()
        evidence['retained_before_return'] = True
        # The first v8 specimen exposed lazy serial assignment in AddToViewport.
        # Future runs must stop before repeating that known identity failure.
        assert widget.serial > 0, 'Stable new-object serial support is required before viewport dispatch'
        def invoke(name, **kwargs):
            return scope.invoke(widget, functions[name], **kwargs).return_value
        assert invoke('IsInViewport') is False
        scope.invoke(widget, functions['AddToViewport'], ZOrder=0)
        added = True
        assert invoke('IsInViewport') is True
        evidence['added_and_in_viewport'] = True
        # Clear intent before dispatch: an unknown outcome must not be retried.
        added = False
        scope.invoke(widget, functions['RemoveFromParent'])
        assert invoke('IsInViewport') is False
        evidence['removed_and_not_in_viewport'] = True
        assert owned.release()
        assert not owned.active
        assert holders() == baseline
        evidence['holder_baseline_restored'] = True
        evidence['passed'] = True
    finally:
        try:
            if added and widget is not None:
                scope.invoke(widget, functions['RemoveFromParent'])
        finally:
            scope.close()
            (ROOT/'evidence/widget-lifecycle-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Base UserWidget: created, retained, added, removed, released; holder baseline restored.')
    return evidence


def recover_observed_widget(session):
    """One explicit cleanup after independently observing a zero->assigned serial.

    Never retries AddToViewport or relaxes SDK identity checks. This research
    recovery is specific to the saved, independently observed specimen.
    """
    path = ROOT/'evidence/widget-lifecycle-live.json'
    evidence = json.loads(path.read_text())
    assert not evidence.get('recovery_started')
    observed = evidence['after_unknown_observation']
    catalog, _, functions, _ = preflight()
    widget = catalog.by_index[observed['index']]
    assert all(getattr(widget, key) == observed[key] for key in
               ('pid', 'index', 'serial', 'address', 'name', 'class_index', 'outer_index', 'outer_serial'))
    assert not widget.object_flags & 0x40000000
    assert widget.pid == session.pid and widget.name.startswith('UserWidget_')
    evidence['recovery_started'] = True
    path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    scope = SessionScope(session)
    try:
        scope.retain(widget)
        assert scope.invoke(widget, functions['IsInViewport']).return_value is True
        scope.invoke(widget, functions['RemoveFromParent'])
        assert scope.invoke(widget, functions['IsInViewport']).return_value is False
        evidence['recovery_removed_from_viewport'] = True
    finally:
        scope.close()
        path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    assert holders() == {k: tuple(v) for k, v in evidence['baseline_holders'].items()}
    evidence['recovery_holder_baseline_restored'] = True
    path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Observed test widget removed; SDK holder baseline restored. No add retry.')


if __name__ == '__main__':
    preflight()
    print('Widget lifecycle preflight passed; no engine function executed.')
