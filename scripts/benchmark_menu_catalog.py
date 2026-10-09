"""Read-only equivalence/timing check for the menu's actual discovery selectors."""
import ast
import json
from pathlib import Path
import time

from expedition33.catalog import capture, capture_matching

ROOT = Path(__file__).resolve().parents[1]


def main():
    tree = ast.parse((ROOT / 'src/expedition33/widgets.py').read_text(encoding='utf-8'))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
             isinstance(n.func, ast.Name) and n.func.id == 'capture_matching']
    assert len(calls) == 1
    selectors = {k.arg: ast.literal_eval(k.value) for k in calls[0].keywords}
    started = time.perf_counter()
    full = capture()
    full_seconds = time.perf_counter() - started
    started = time.perf_counter()
    matched = capture_matching(full.pid, **selectors)
    matched_seconds = time.perf_counter() - started
    expected = {o.index for o in full.objects if o.name in selectors['names']}
    for cls in selectors['classes']:
        expected.update(o.index for o in full.select(cls))
    assert expected <= set(matched.by_index), 'Requested objects missing'
    assert all(full.by_index.get(i) == o for i, o in matched.by_index.items()), 'Object observations differ'
    assert all(full.classes.get(i) == c for i, c in matched.classes.items()), 'Class observations differ'
    record = dict(pid=full.pid, full_objects=len(full.objects), matched_objects=len(matched.objects),
        requested_matches=len(expected), full_seconds=full_seconds, matched_seconds=matched_seconds,
        all_requested_objects_present=True, all_observations_equal=True, engine_calls=0)
    (ROOT / 'evidence/menu-catalog-benchmark.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
