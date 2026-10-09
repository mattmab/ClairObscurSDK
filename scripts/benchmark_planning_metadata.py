"""Read-only planning benchmark: no engine invocation or new controller."""
import json
from pathlib import Path
import time
from expedition33.catalog import capture
from expedition33.invocation import prepare_call
from expedition33._planning_metadata import MetadataObservations


def main():
    catalog = capture()
    cls = catalog.find_class('KismetMathLibrary')
    target, = [o for o in catalog.objects if o.class_index == cls.index and o.name == 'Default__KismetMathLibrary']
    function, = [o for o in catalog.objects if o.outer_index == cls.index and o.name == 'Add_IntInt']
    count = 10
    started = time.perf_counter()
    baseline = [prepare_call(catalog, target, function, {'A': i, 'B': -i}) for i in range(count)]
    ordinary = time.perf_counter() - started
    cache = MetadataObservations()
    started = time.perf_counter()
    cached = [prepare_call(catalog, target, function, {'A': i, 'B': -i}, _metadata=cache) for i in range(count)]
    reused = time.perf_counter() - started
    assert cached == baseline
    result = dict(pid=catalog.pid, calls=count, ordinary_seconds=ordinary,
                  cached_seconds=reused, plans_equal=True, engine_calls=0)
    path = Path(__file__).resolve().parents[1] / 'evidence/planning-metadata-benchmark.json'
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
