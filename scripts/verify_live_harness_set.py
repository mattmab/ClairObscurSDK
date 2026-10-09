"""Exercise unchanged Explorer.set over a fresh adapter, sharing the live host."""
import importlib.util
import json
from pathlib import Path
import runpy
import sys
from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_object_assignment
    # Existing host has the preceding adapter imported. Load updated adapter in
    # its own package namespace, preserving the host's wrappers/retained state.
    name = 'expedition33.introspection_set_candidate'
    assert name not in sys.modules
    path = ROOT/'src/expedition33/introspection'
    spec = importlib.util.spec_from_file_location(name, path/'__init__.py', submodule_search_locations=[str(path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    helpers = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))
    catalog, library, functions, args = helpers['preflight']()
    one, holders = helpers['one'], helpers['holders']
    def cls(label): return catalog.by_index[catalog.find_class(label).index]
    gameplay = cls('GameplayStatics')
    spawn = one(o for o in catalog.objects if o.outer_index == gameplay.index and o.name == 'SpawnObject')
    cdo = one(o for o in catalog.objects if o.class_index == gameplay.index and o.name == 'Default__GameplayStatics')
    baseline = holders()
    evidence = {'pid': session.pid, 'passed': False, 'baseline_holders': baseline,
                'new_controller': False, 'viewport_changed': False, 'input_changed': False}
    scope = SessionScope(session)
    harness = module.Harness(scope)
    assigned = False
    try:
        widget = scope.invoke_retained(library, functions['Create'], **args).return_value
        current = capture()
        tree = read_values(current, current.resolve(widget)).values[cls('UserWidget').index, 'WidgetTree']
        canvas = scope.invoke_retained(cdo, spawn, ObjectClass=cls('CanvasPanel'), Outer=tree).return_value
        current = capture()
        def ref(obj): return {'$object':current.path_name(current.resolve(obj))}
        request = {'op':'set', 'target':ref(tree), 'member':'RootWidget', 'value':ref(canvas), 'allow_mutation':True}
        before = read_values(current, current.resolve(tree)).values[cls('WidgetTree').index, 'RootWidget']
        assert before is None
        try:
            harness.request(dict(request, allow_mutation=False))
            raise AssertionError('Missing mutation consent accepted')
        except ValueError as error:
            assert 'allow_mutation' in str(error)
        evidence['opt_in_rejected'] = True
        result = harness.request(request)
        assigned = True
        evidence['set_result'] = result
        assert result['before'] is None and result['after']['$object'] == request['value']['$object']
        assigned = False  # Do not repeat a restoration with an unknown outcome.
        restored = harness.request(dict(request, value=None))
        evidence['restore_result'] = restored
        assert restored['before'] == result['after'] and restored['after'] is None
        current = capture()
        assert read_values(current, current.resolve(tree)).values[cls('WidgetTree').index, 'RootWidget'] is None
        evidence['independent_null_readback'] = True
        evidence['status'] = harness.request({'op':'status'})
    finally:
        try:
            if assigned:
                scope.assign_object(tree, cls('WidgetTree'), 'RootWidget', None, expected=canvas, allow_mutation=True)
            harness.close()
        finally:
            try:
                scope.close()
            finally:
                (ROOT/'evidence/harness-set-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    assert holders() == baseline
    evidence['holder_baseline_restored'] = evidence['passed'] = True
    (ROOT/'evidence/harness-set-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Original Harness set: consent rejection, object assignment, before/after, null restoration and holder cleanup passed.')
    return evidence
