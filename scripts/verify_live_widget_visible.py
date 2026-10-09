"""Brief visible UMG specimen on the existing persistent v11/v12 console session.

Uses only SDK-owned objects. By default it installs no actions, changes no input
mode, requests no focus, and disables the button before viewport attachment.
An explicit CommonUI/display callback allows separate interaction specimens.
The bounded observation delay runs in the external controller, never the game thread.
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


def run(session, *, hold_seconds=30, label_text=None, activatable=False,
        button_enabled=False, on_display=None, evidence_name=None):
    if type(hold_seconds) is not int or not 0 <= hold_seconds <= 45:
        raise ValueError('Observation delay must be an integer from 0 through 45')
    if type(activatable) is not bool or type(button_enabled) is not bool:
        raise ValueError('Widget activation and enabled options must be boolean')
    if on_display is not None and not callable(on_display):
        raise ValueError('Display probe must be callable')
    if evidence_name is not None and (type(evidence_name) is not str or Path(evidence_name).name != evidence_name):
        raise ValueError('Evidence name must be a filename')
    assert session.supports_pod_values and session.supports_object_assignment
    if label_text is not None:
        from expedition33._text_wire import encode_units
        encode_units(label_text)
        assert session.supports_text_values
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
                'input_mode_changed':False, 'focus_requested':None if on_display is not None else False,
                'display_callback':on_display is not None,
                'visual_confirmation':'requires separate screenshot observation',
                'hold_seconds':hold_seconds}
    path = ROOT/'evidence'/(evidence_name or ('widget-visible-text-live.json' if label_text is not None else 'widget-visible-live.json'))
    def save(): path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    widget = tree = canvas = button = label = None
    label_attached = False
    attached = assigned = added = uncertain = activated = False
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
        if activatable:
            args = dict(args, WidgetType=cls('CommonActivatableWidget'))
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
        mutate(scope.invoke, button, enabled, bInIsEnabled=button_enabled)
        for name, parameter, value in (
            ('SetPosition','InPosition',{'X':80.0,'Y':80.0}),
            ('SetSize','InSize',{'X':420.0,'Y':160.0}),
            ('SetAnchors','InAnchors',{'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}})):
            mutate(scope.invoke, slot, fn('CanvasPanelSlot',name), **{parameter:value})
        mutate(scope.invoke, button, fn('Button','SetBackgroundColor'),
               InBackgroundColor={'R':0.125,'G':0.25,'B':0.5,'A':1.0})
        if label_text is not None:
            label = scope.invoke_retained(cdo('GameplayStatics'), spawn, ObjectClass=cls('TextBlock'), Outer=tree).return_value
            label_slot = mutate(scope.invoke_retained, canvas, add, Content=label).return_value
            label_attached = True
            evidence['objects'].update(label=asdict(label),label_slot=asdict(label_slot))
            mutate(scope.invoke, label, enabled, bInIsEnabled=False)
            with mutate(scope.invoke_retained, label, fn('TextBlock','SetText'), InText=label_text):
                pass
            for name,parameter,value in (
                ('SetPosition','InPosition',{'X':100.0,'Y':100.0}),
                ('SetSize','InSize',{'X':380.0,'Y':120.0}),
                ('SetAnchors','InAnchors',{'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}})):
                mutate(scope.invoke,label_slot,fn('CanvasPanelSlot',name),**{parameter:value})
        mutate(scope.assign_object, tree, cls('WidgetTree'), 'RootWidget', canvas,
               expected=None, allow_mutation=True)
        assigned = True
        observed = root()
        assert observed.index == canvas.index and observed.serial == canvas.serial
        mutate(scope.invoke, widget, functions['AddToViewport'], ZOrder=1000)
        added = True
        if activatable:
            mutate(scope.invoke, widget, fn('CommonActivatableWidget', 'ActivateWidget'))
            activated = True
            assert scope.invoke(widget, fn('CommonActivatableWidget', 'IsActivated')).return_value is True
            evidence['activated'] = True
        assert scope.invoke(widget, functions['IsInViewport']).return_value is True
        assert dict(scope.invoke(slot, fn('CanvasPanelSlot','GetPosition')).return_value) == {'X':80.0,'Y':80.0}
        assert dict(scope.invoke(slot, fn('CanvasPanelSlot','GetSize')).return_value) == {'X':420.0,'Y':160.0}
        if label is not None:
            with mutate(scope.invoke_retained,label,fn('TextBlock','GetText')) as result:
                assert result.return_value == label_text
            evidence['text_after_slate_creation'] = label_text
        evidence['viewport_added'] = evidence['layout_readback'] = True
        evidence['observation_started_unix'] = time.time()
        save()
        if on_display is not None:
            evidence['interaction'] = on_display(scope, widget, button, args['OwningPlayer'])
            save()
        time.sleep(hold_seconds)
    finally:
        try:
            if activated and not uncertain:
                activated = False
                mutate(scope.invoke, widget, fn('CommonActivatableWidget', 'DeactivateWidget'))
                assert scope.invoke(widget, fn('CommonActivatableWidget', 'IsActivated')).return_value is False
                evidence['deactivated'] = True
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
            if label_attached and not uncertain:
                label_attached = False
                mutate(scope.invoke,label,functions['RemoveFromParent'])
                evidence['label_removed'] = True
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
