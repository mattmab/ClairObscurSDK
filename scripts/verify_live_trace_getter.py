"""Live v18 getter trace proof with explicit stop/forget/session cleanup."""
import json
from pathlib import Path
from expedition33.sdk import Session
from expedition33.catalog import capture
from expedition33.reflection import describe


def main():
    evidence = {'passed': False, 'steps': []}
    path = Path(__file__).resolve().parents[1] / 'evidence/trace-getter-live.json'
    def record(stage, **values):
        item = dict(stage=stage, **values)
        evidence['steps'].append(item)
        path.write_text(json.dumps(evidence, indent=2))
        print(json.dumps(item), flush=True)
    try:
        with Session(traces=True) as session:
            record('session_open', pid=session.pid)
            catalog = capture()
            actor = catalog.find_class('Actor')
            target, = [obj for obj in catalog.objects if obj.class_index == actor.index and obj.name == 'Default__Actor']
            function, = [obj for obj in catalog.objects if obj.outer_index == actor.index and obj.name == 'IsActorBeingDestroyed']
            original = describe(catalog, (function,))[function.index].function['entry_rva']
            with session.trace(function, target, target=target, duration_ms=60000, limit=10) as trace:
                record('trace_started', registration=trace.registration, original_entry=original)
                result = session.invoke(target, function)
                record('getter_called', result=result.return_value)
                events = trace.read()
                status = trace.status()
                record('trace_read', state=trace.state, observed=status.observed, rejected=status.rejected,
                       events=[dict(sequence=e.sequence, index=e.index, serial=e.serial,
                                    arguments=dict(e.arguments), result=e.return_value) for e in events])
                assert result.return_value is False and len(events) == 1
                assert events[0].return_value is False and events[0].index == target.index
                assert events[0].serial == target.serial and not events[0].arguments
                trace.stop()
                restored = describe(catalog, (function,))[function.index].function['entry_rva']
                assert restored == original
                session.invoke(target, function)
                assert trace.read() == ()
                record('trace_stopped', restored_entry=restored, cleanup=trace.cleanup)
            record('trace_forgotten', state=trace.state)
        record('session_closed')
        evidence['passed'] = True
    except BaseException as error:
        evidence['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        path.write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
