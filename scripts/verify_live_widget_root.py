"""Assign/restore an SDK-created tree root using the persistent v10 host."""
from dataclasses import asdict
import json
from pathlib import Path
import runpy
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33.values import read_values
from expedition33._scope import SessionScope
from expedition33.invocation import InvocationError

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_object_assignment
    helper = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))
    catalog, library, functions, args = helper['preflight']()
    one, holders = helper['one'], helper['holders']
    def cls(name): return catalog.by_index[catalog.find_class(name).index]
    tree_class, canvas_class = cls('WidgetTree'), cls('CanvasPanel')
    gameplay = cls('GameplayStatics')
    spawn = one(o for o in catalog.objects if o.outer_index == gameplay.index and o.name == 'SpawnObject')
    gameplay_cdo = one(o for o in catalog.objects if o.class_index == gameplay.index and o.name == 'Default__GameplayStatics')
    prop = one(p for p in describe(catalog, [tree_class])[tree_class.index].properties if p['name'] == 'RootWidget')
    assert prop['type'] == 'ObjectProperty' and not prop['flags'] & 0x1000
    baseline = holders()
    evidence = {'pid': session.pid, 'passed': False, 'baseline_holders': baseline,
                'focus_changed': False, 'visible_menu_tested': False}
    scope = SessionScope(session)
    assigned, added, uncertain = False, False, False
    try:
        widget = scope.invoke_retained(library, functions['Create'], **args).return_value
        current = capture()
        tree = read_values(current, current.resolve(widget)).values[cls('UserWidget').index, 'WidgetTree']
        canvas = scope.invoke_retained(gameplay_cdo, spawn, ObjectClass=canvas_class, Outer=tree).return_value
        evidence['objects'] = {name: asdict(obj) for name, obj in (('widget',widget), ('tree',tree), ('canvas',canvas))}
        def root():
            observed = capture()
            return read_values(observed, observed.resolve(tree)).values[tree_class.index, 'RootWidget']
        assert root() is None
        result = scope.assign_object(tree, tree_class, 'RootWidget', canvas, expected=None, allow_mutation=True)
        assigned = True
        assert result.outcome == 'dispatch_returned'
        observed = root()
        assert observed.index == canvas.index and observed.serial == canvas.serial
        evidence['assigned_readback'] = True
        # A stale expected value must reject without changing the installed root.
        try:
            scope.assign_object(tree, tree_class, 'RootWidget', None, expected=None, allow_mutation=True)
            raise AssertionError('Stale expected reference was accepted')
        except InvocationError as error:
            assert error.outcome == 'not_dispatched' and error.native_error == 4
        assert root().index == canvas.index
        evidence['stale_expected_rejected'] = True
        uncertain = True
        scope.invoke(widget, functions['AddToViewport'], ZOrder=0)
        uncertain = False
        added = True
        assert scope.invoke(widget, functions['IsInViewport']).return_value is True
        evidence['viewport_added'] = True
        added = False
        uncertain = True
        scope.invoke(widget, functions['RemoveFromParent'])
        uncertain = False
        assert scope.invoke(widget, functions['IsInViewport']).return_value is False
        evidence['viewport_removed'] = True
        assigned = False
        scope.assign_object(tree, tree_class, 'RootWidget', None, expected=canvas, allow_mutation=True)
        assert root() is None
        evidence['root_restored'] = True
    finally:
        try:
            if added and not uncertain:
                scope.invoke(widget, functions['RemoveFromParent'])
            if assigned and not uncertain:
                scope.assign_object(tree, tree_class, 'RootWidget', None, expected=canvas, allow_mutation=True)
        finally:
            evidence['viewport_outcome_unknown'] = uncertain
            try:
                scope.close()
            finally:
                (ROOT/'evidence/widget-root-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    assert holders() == baseline
    evidence['holder_baseline_restored'] = evidence['passed'] = True
    (ROOT/'evidence/widget-root-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Root assignment/readback, stale-value rejection, viewport lifecycle and root/holder restoration passed.')
    return evidence
