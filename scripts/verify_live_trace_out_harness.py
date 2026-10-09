"""Live viewport out parameters and original Harness getter trace contract."""
import json
from pathlib import Path
from expedition33.sdk import Session
from expedition33.catalog import capture
from expedition33.introspection import Harness


def main():
    evidence = {'passed': False, 'steps': []}
    path = Path(__file__).resolve().parents[1] / 'evidence/trace-out-harness-live.json'
    def record(stage, **values):
        item = dict(stage=stage, **values); evidence['steps'].append(item)
        path.write_text(json.dumps(evidence, indent=2)); print(json.dumps(item), flush=True)
    try:
        with Session(traces=True) as session:
            catalog = capture()
            pc = catalog.find_class('PlayerController')
            targets = [obj for obj in catalog.objects if pc.index in catalog.ancestors(obj.class_index)
                       and not obj.object_flags & (0x10 | 0x40000000)]
            assert len(targets) == 1, [(obj.index, obj.name) for obj in targets]
            target = targets[0]
            function, = [obj for obj in catalog.objects if obj.outer_index == pc.index and obj.name == 'GetViewportSize']
            record('viewport_target', pid=session.pid, target=catalog.path_name(target), index=target.index)
            with session.trace(function, target, target=target, duration_ms=60000, limit=1000) as trace:
                result = session.invoke(target, function)
                events = trace.read()
                observed = [dict(event.arguments) for event in events]
                record('viewport_trace', outputs=dict(result.outputs), events=observed,
                       rejected=trace.status().rejected)
                assert dict(result.outputs) in observed and set(result.outputs) == {'SizeX', 'SizeY'}
                assert all(event.index == target.index and event.return_value is None for event in events)
            actor = catalog.find_class('Actor')
            specimen, = [obj for obj in catalog.objects if obj.class_index == actor.index and obj.name == 'Default__Actor']
            getter, = [obj for obj in catalog.objects if obj.outer_index == actor.index and obj.name == 'IsActorBeingDestroyed']
            harness = Harness(session)
            try:
                target_ref = {'$object': catalog.path_name(specimen)}
                started = harness.request(dict(op='trace_start', name='live-getter',
                    function=catalog.path_name(getter), target=target_ref, seconds=120, limit=5))
                schema = harness.request(dict(op='schema', struct=catalog.path_name(getter)))
                provenance = schema['retained_trace_schemas']
                assert provenance['function_indices'] == [getter.index]
                assert provenance['observation'] == 'before_trace_installation'
                assert provenance['live_schema_revalidated'] is False
                record('hooked_schema', schema=schema)
                returned = harness.request(dict(op='invoke', target=target_ref,
                    member='IsActorBeingDestroyed', allow_mutation=True))
                traced = harness.request(dict(op='trace_read', name='live-getter'))
                record('harness_trace', started=started, result=returned, trace=traced)
                assert returned is False and traced['count'] == 1
                assert traced['events'][0]['return'] is False
                assert traced['events'][0]['target']['$object'] == target_ref['$object']
                stopped = harness.request(dict(op='trace_stop', name='live-getter', forget=True))
                assert not stopped['active'] and stopped['count'] == 1
                record('harness_forgotten', count=stopped['count'])
            finally:
                harness.close()
        record('session_closed')
        evidence['passed'] = True
    except BaseException as error:
        evidence['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        path.write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
