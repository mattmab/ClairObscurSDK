"""Read-only timings for native-widget planning; never dispatches engine calls."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import catalog, reflection, enums
from expedition33.invocation import prepare_call


def main():
    timings = []
    def timed_query(original):
        def query(arguments):
            started = time.perf_counter()
            result = original(arguments)
            timings.append({'query': arguments[0], 'seconds': time.perf_counter() - started,
                            'rows': len(result[1])})
            return result
        return query
    for module in (catalog, reflection, enums):
        module._query = timed_query(module._query)
    started = time.perf_counter()
    observed = catalog.capture()
    capture_seconds = time.perf_counter() - started
    def one(rows):
        rows = tuple(rows)
        assert len(rows) == 1
        return rows[0]
    plans = []
    for target, owner, name, arguments in (
        ('Button', 'Widget', 'SetIsEnabled', {'bInIsEnabled':True}),
        ('Button', 'Button', 'SetBackgroundColor',
         {'InBackgroundColor':{'R':0.1, 'G':0.2, 'B':0.3, 'A':1.0}}),
        ('TextBlock', 'TextBlock', 'SetText', {'InText':'Planning only'})):
        cls = observed.find_class(target).index
        obj = one(o for o in observed.objects if o.class_index == cls and o.name == 'Default__' + target)
        owner_index = observed.find_class(owner).index
        fn = one(o for o in observed.objects if o.outer_index == owner_index and o.name == name)
        started = time.perf_counter()
        prepare_call(observed, obj, fn, arguments, pod_values=True, text_values=True, enum_values=True)
        plans.append({'function': owner + '.' + name, 'seconds': time.perf_counter() - started})
    result = {'pid': observed.pid, 'read_only': True, 'engine_calls_executed': 0,
              'objects': len(observed.objects), 'capture_seconds': capture_seconds,
              'plans': plans, 'queries': timings}
    (ROOT / 'evidence/widget-planning-profile.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
