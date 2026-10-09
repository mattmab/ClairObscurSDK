"""Read-only arithmetic specimen for native input locals and return tracing."""
import json
from pathlib import Path
from expedition33.sdk import Session
from expedition33.catalog import capture
from expedition33.reflection import describe


def main():
    evidence = {'passed': False, 'steps': []}
    path = Path(__file__).resolve().parents[1] / 'evidence/trace-locals-live.json'
    def record(stage, **values):
        evidence['steps'].append(dict(stage=stage, **values))
        path.write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence['steps'][-1]), flush=True)
    try:
        with Session(traces=True) as session:
            catalog = capture()
            cls = catalog.find_class('KismetMathLibrary')
            target, = [o for o in catalog.objects if o.class_index == cls.index
                       and o.name == 'Default__KismetMathLibrary']
            function, = [o for o in catalog.objects if o.outer_index == cls.index and o.name == 'Add_IntInt']
            descriptor = describe(catalog, (function,))[function.index]
            original = descriptor.function['entry_rva']
            record('specimen', pid=session.pid, function=catalog.path_name(function),
                   target=catalog.path_name(target), original_entry=original)
            with session.trace(function, target, target=target, duration_ms=60000, limit=10) as trace:
                for a, b in ((17, 25), (-9, 4)):
                    result = session.invoke(target, function, A=a, B=b)
                    events = trace.read()
                    record('observation', inputs={'A': a, 'B': b}, result=result.return_value,
                           events=[dict(arguments=dict(e.arguments), result=e.return_value,
                                        index=e.index, serial=e.serial) for e in events])
                    assert result.return_value == a + b and len(events) == 1
                    event = events[0]
                    assert dict(event.arguments) == {'A': a, 'B': b}
                    assert event.return_value == a + b
                    assert (event.index, event.serial) == (target.index, target.serial)
                status = trace.status()
                assert status.rejected == 0 and status.dropped == 0
                trace.stop()
                assert describe(catalog, (function,))[function.index].function['entry_rva'] == original
                record('restored', observed=status.observed, rejected=status.rejected, cleanup=trace.cleanup)
        record('session_closed')
        evidence['passed'] = True
    except BaseException as error:
        evidence['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        path.write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
