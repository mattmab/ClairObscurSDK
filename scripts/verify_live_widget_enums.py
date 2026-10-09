"""V13 enum round trips on an SDK-owned, undisplayed Button; owner thread only."""
from dataclasses import asdict
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33.enums import describe_enums
from expedition33.invocation import prepare_call

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_enum_values
    evidence = {'pid': session.pid, 'passed': False, 'displayed': False, 'input_changed': False, 'round_trips': []}
    def save():
        (ROOT / 'evidence/widget-enum-progress.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    def probe(scope, slot, button, catalog):
        catalog = capture()
        button = catalog.resolve(button)
        owner = catalog.find_class('Widget')
        def function(name):
            matches = [o for o in catalog.objects if o.outer_index == owner.index and o.name == name]
            assert len(matches) == 1
            return matches[0]
        setter, getter = function('SetVisibility'), function('GetVisibility')
        enum = catalog.find_path('/Script/UMG.ESlateVisibility', 'Enum')
        descriptor = describe_enums(catalog, [enum])[enum.index]
        def named(short):
            matches = [m.name for m in descriptor.members if m.name.rsplit('::', 1)[-1] == short]
            assert len(matches) == 1
            return descriptor.value(matches[0])
        for short in ('Hidden', 'Visible'):
            value = named(short)
            prepare_call(catalog, button, setter, {'InVisibility': value}, enum_values=True)
            with scope.invoke_retained(button, setter, InVisibility=value):
                pass
            with scope.invoke_retained(button, getter) as result:
                actual = result.return_value
                assert actual.enum.index == enum.index and actual.name == value.name and actual.value == value.value
                evidence['round_trips'].append(asdict(actual))
                save()
        try:
            scope.invoke_retained(button, setter, InVisibility=0)
        except ValueError:
            evidence['raw_integer_rejected'] = True
        else:
            raise AssertionError('Untyped enum input was accepted')
        return dict(enum_path=catalog.path_name(enum), round_trips=list(evidence['round_trips']))
    save()
    helper = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_children.py'))
    result = helper['run'](session, slot_probe=probe, evidence_name='widget-enum-live.json')
    evidence['passed'] = True
    save()
    print('Owned-widget enum round trips and exact holder cleanup passed; no viewport/input change.')
    return result
