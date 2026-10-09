"""Brief visible UMG specimen on the existing persistent v11 console session.

Uses only SDK-owned objects. It never installs actions, changes input mode, or
requests focus. The button is disabled before viewport attachment. The bounded
observation delay runs in the external Python controller, never the game thread.
"""
from dataclasses import asdict
import json
from pathlib import Path
import runpy
import time

from expedition33.catalog import capture
from expedition33.invocation import prepare_call
from expedition33.values import read_values
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session, *, hold_seconds=30):
    if type(hold_seconds) is not int or not 0 <= hold_seconds <= 45:
        raise ValueError('Observation delay must be an integer from 0 through 45')
    assert session.supports_pod_values and session.supports_object_assignment
    helper = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))
    catalog, library, functions, args = helper['preflight']()
    assert catalog.pid == session.pid
    one, holders = helper['one'], helper['holders']
    def cls(name): return catalog.by_index[catalog.find_class(name).index]
    def cdo(name): return one(o for o in catalog.objects if o.name == 'Default__'+name and o.class_index == cls(name).index)
    def fn(owner, name): return one(o for o in catalog.objects if o.outer_index == cls(owner).index and o.name == name)
    spawn, add = fn('GameplayStatics', 'SpawnObject'), fn('CanvasPanel', 'AddChildToCanvas')
    enabled = fn('Widget', 'SetIsEnabled')
    prepare_call(catalog, cdo('Button'), enabled, {'bInIsEnabled': False}, pod_values=True)
    baseline = holders()
    scope = SessionScope(session)
    evidence = {'pid':session.pid, 'passed':False, 'baseline_holders':baseline,
                'input_mode_changed':False, 'focus_requested':False,
                'visual_confirmation':'requires separate screenshot observation',
                'hold_seconds':hold_seconds}
    path = ROOT/'evidence/widget-visible-live.json'
    def save(): path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    widget = tree = canvas = button = None
    attached = assigned = added = uncertain = False
    def mutate(callback, *values, **keywords):
        nonlocal uncertain
        uncertain = True
        result = callback(*values, **keywords)
        uncertain = False
        return result
    def root():
        current = capture()
        return read_values(current, current.resolve(tree)).values[cls('WidgetTree').index, 'RootWidget']
    try:
        widget = scope.invoke_retained(library, functions['Create'], **args).return_value
        current = capture()
        tree = read_values(current, current.resolve(widget)).values[cls('UserWidget').index, 'WidgetTree']
        assert tree is not None and tree.outer_index == widget.index and root() is None
        canvas = scope.invoke_retained(cdo('GameplayStatics'), spawn, ObjectClass=cls('CanvasPanel'), Outer=tree).return_value
        button = scope.invoke_retained(cdo('GameplayStatics'), spawn, ObjectClass=cls('Button'), Outer=tree).return_value
        slot = mutate(scope.invoke_retained, canvas, add, Content=button).return_value
        attached = True
        evidence['objects'] = {name:asdict(obj) for name,obj in
                               (('widget',widget),('tree',tree),('canvas',canvas),('button',button),('slot',slot))}
        mutate(scope.invoke, button, enabled, bInIsEnabled=False)
        for name, parameter, value in (
            ('SetPosition','InPosition',{'X':80.0,'Y':80.0}),
            ('SetSize','InSize',{'X':420.0,'Y':160.0}),
            ('SetAnchors','InAnchors',{'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}})):
            mutate(scope.invoke, slot, fn('CanvasPanelSlot',name), **{parameter:value})
        mutate(scope.invoke, button, fn('Button','SetBackgroundColor'),
               InBackgroundColor={'R':0.125,'G':0.25,'B':0.5,'A':1.0})
        mutate(scope.assign_object, tree, cls('WidgetTree'), 'RootWidget', canvas,
               expected=None, allow_mutation=True)
        assigned = True
        observed = root()
        assert observed.index == canvas.index and observed.serial == canvas.serial
        mutate(scope.invoke, widget, functions['AddToViewport'], ZOrder=1000)
        added = True
        assert scope.invoke(widget, functions['IsInViewport']).return_value is True
        assert dict(scope.invoke(slot, fn('CanvasPanelSlot','GetPosition')).return_value) == {'X':80.0,'Y':80.0}
        assert dict(scope.invoke(slot, fn('CanvasPanelSlot','GetSize')).return_value) == {'X':420.0,'Y':160.0}
        evidence['viewport_added'] = evidence['layout_readback'] = True
        evidence['observation_started_unix'] = time.time()
        save()
        time.sleep(hold_seconds)
    finally:
        try:
            if added and not uncertain:
                added = False
                mutate(scope.invoke, widget, functions['RemoveFromParent'])
                assert scope.invoke(widget, functions['IsInViewport']).return_value is False
                evidence['viewport_removed'] = True
            if assigned and not uncertain:
                assigned = False
                mutate(scope.assign_object, tree, cls('WidgetTree'), 'RootWidget', None,
                       expected=canvas, allow_mutation=True)
                assert root() is None
                evidence['root_restored'] = True
            if attached and not uncertain:
                attached = False
                mutate(scope.invoke, button, functions['RemoveFromParent'])
                assert scope.invoke(canvas, fn('PanelWidget','GetChildrenCount')).return_value == 0
                evidence['child_removed'] = True
        finally:
            evidence['mutation_outcome_unknown'] = uncertain
            try:
                scope.close()
            finally:
                save()
    assert holders() == baseline
    evidence['holder_baseline_restored'] = evidence['passed'] = True
    save()
    print('Visible UMG specimen lifecycle passed; exact root/child/holder cleanup. Visual result requires screenshot observation.')
    return evidence
