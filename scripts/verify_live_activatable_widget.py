"""Owned CommonUI activation lifecycle; no viewport attachment or input mapping."""
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    helpers = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_lifecycle.py'))
    one, holders = helpers['one'], helpers['holders']
    catalog, library, functions, arguments = helpers['preflight']()
    cls = catalog.by_index[catalog.find_class('CommonActivatableWidget').index]
    def function(name):
        return one(o for o in catalog.objects if o.outer_index == cls.index and o.name == name)
    activate, deactivate = function('ActivateWidget'), function('DeactivateWidget')
    active, focus = function('IsActivated'), function('GetDesiredFocusTarget')
    baseline = holders()
    evidence = dict(pid=session.pid, passed=False, displayed=False, states=[])
    def save():
        (ROOT / 'evidence/activatable-widget-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    save()
    scope = SessionScope(session)
    widget = None
    try:
        created = scope.invoke_retained(library, functions['Create'], **dict(arguments, WidgetType=cls))
        widget = created.return_value
        current = capture()
        widget = current.resolve(widget)
        observed = read_values(current, widget)
        assert observed.values[cls.index, 'InputMapping'] is None
        assert observed.values[cls.index, 'bIsActive'] is False
        evidence['input_mapping_absent'] = True
        evidence['widget_path'] = current.path_name(widget)
        assert scope.invoke(widget, active).return_value is False
        for operation, expected in ((activate, True), (activate, True), (deactivate, False), (deactivate, False)):
            scope.invoke(widget, operation)
            actual = scope.invoke(widget, active).return_value
            assert actual is expected
            evidence['states'].append(dict(operation=operation.name, active=actual))
            save()
        with scope.invoke_retained(widget, focus) as result:
            assert result.return_value is None
        evidence['base_desired_focus_is_null'] = True
    finally:
        try:
            if widget is not None:
                # Idempotent deactivation precedes releasing the owned widget.
                scope.invoke(widget, deactivate)
        finally:
            scope.close()
            save()
    assert holders() == baseline
    evidence['holder_baseline_restored'] = evidence['passed'] = True
    save()
    print('Owned CommonActivatableWidget activation/deactivation and exact holder cleanup passed; no viewport attachment.')
    return evidence
