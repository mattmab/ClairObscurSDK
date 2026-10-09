"""Construct a canvas/button in an SDK-owned tree; attach/remove without display.

Call run(sdk) on the existing v9 persistent Python owner thread. No second
controller, root-property write, viewport attachment or input change occurs.
"""
from dataclasses import asdict
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33.invocation import prepare_call
from expedition33.values import read_values
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_stable_returns
    helpers = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))
    one, holders = helpers['one'], helpers['holders']
    catalog, library, functions, arguments = helpers['preflight']()
    assert catalog.pid == session.pid
    def cls(name): return catalog.by_index[catalog.find_class(name).index]
    def cdo(name): return one(o for o in catalog.objects if o.name == 'Default__'+name and o.class_index == cls(name).index)
    def fn(owner, name): return one(o for o in catalog.objects if o.outer_index == cls(owner).index and o.name == name)
    spawn, add, count = fn('GameplayStatics', 'SpawnObject'), fn('CanvasPanel', 'AddChildToCanvas'), fn('PanelWidget', 'GetChildrenCount')
    prepare_call(catalog, cdo('GameplayStatics'), spawn, {'ObjectClass': cls('CanvasPanel'), 'Outer': cdo('WidgetTree')})
    prepare_call(catalog, cdo('CanvasPanel'), add, {'Content': cdo('Button')})
    prepare_call(catalog, cdo('CanvasPanel'), count, {})
    baseline = holders()
    evidence = {'pid': catalog.pid, 'baseline_holders': baseline, 'passed': False,
                'displayed': False, 'root_written': False, 'input_changed': False}
    scope = SessionScope(session)
    button, attached = None, False
    try:
        widget_owner = scope.invoke_retained(library, functions['Create'], **arguments)
        widget = widget_owner.return_value
        current = capture()
        widget = current.resolve(widget)
        tree = read_values(current, widget).values[cls('UserWidget').index, 'WidgetTree']
        assert tree is not None and tree.class_index == cls('WidgetTree').index
        # The created UserWidget's reflected reference owns its tree. Every
        # newly created child and slot also gets its own scoped native lease.
        tree = current.resolve(tree)
        assert tree.outer_index == widget.index
        canvas_owner = scope.invoke_retained(cdo('GameplayStatics'), spawn, ObjectClass=cls('CanvasPanel'), Outer=tree)
        button_owner = scope.invoke_retained(cdo('GameplayStatics'), spawn, ObjectClass=cls('Button'), Outer=tree)
        canvas, button = canvas_owner.return_value, button_owner.return_value
        assert canvas.class_index == cls('CanvasPanel').index and button.class_index == cls('Button').index
        assert canvas.outer_index == tree.index and button.outer_index == tree.index
        assert canvas.serial > 0 and button.serial > 0
        assert scope.invoke(canvas, count).return_value == 0
        slot_owner = scope.invoke_retained(canvas, add, Content=button)
        attached = True
        slot = slot_owner.return_value
        assert slot is not None and slot.class_index == cls('CanvasPanelSlot').index and slot.serial > 0
        assert scope.invoke(canvas, count).return_value == 1
        current = capture()
        values = read_values(current, current.resolve(button))
        observed_slot = values.values[cls('Widget').index, 'Slot']
        assert observed_slot.index == slot.index and observed_slot.serial == slot.serial
        current_holders = holders()
        assert len(current_holders) == len(baseline) + 4
        assert all(current_holders.get(k) == v for k, v in baseline.items())
        evidence['created'] = {name: asdict(obj) for name, obj in
                               (('widget', widget), ('tree', tree), ('canvas', canvas), ('button', button), ('slot', slot))}
        evidence['child_count_and_slot_verified'] = True
        attached = False  # No retry if removal acknowledgement is unknown.
        scope.invoke(button, functions['RemoveFromParent'])
        assert scope.invoke(canvas, count).return_value == 0
        evidence['removed_child'] = True
    finally:
        try:
            if attached and button is not None:
                scope.invoke(button, functions['RemoveFromParent'])
        finally:
            scope.close()
            (ROOT/'evidence/widget-children-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    assert holders() == baseline
    evidence['holder_baseline_restored'] = evidence['passed'] = True
    (ROOT/'evidence/widget-children-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Canvas/Button construction, retained slot, child attachment/removal and scoped cleanup passed; nothing displayed.')
    return evidence
