"""Read-only selected catalog comparison and selector rejection against live game."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture, capture_selected
from expedition33 import RuntimeQueryError


def main():
    start = time.perf_counter(); full = capture(); full_seconds = time.perf_counter() - start
    targets = [obj for obj in full.select('PlayerController') if not obj.object_flags & 0x10]
    assert len(targets) == 1
    target = targets[0]
    identity = (target.index, target.serial, target.address)
    start = time.perf_counter(); selected = capture_selected(full.pid, [identity]); selected_seconds = time.perf_counter() - start
    assert len(selected.objects) < len(full.objects)
    assert selected.resolve(target) == target
    for obj in selected.objects:
        assert obj == full.by_index[obj.index]
    for index, cls in selected.classes.items():
        assert cls == full.classes[index]
    assert selected.path_name(target) == full.path_name(target)
    rejected = []
    for label, pid, selector in [('serial', full.pid, (target.index, target.serial ^ 1, target.address)),
            ('address', full.pid, (target.index, target.serial, target.address + 8)),
            ('pid', full.pid + 1, identity)]:
        try:
            capture_selected(pid, [selector])
        except RuntimeQueryError:
            rejected.append(label)
        else:
            raise AssertionError('Changed selector accepted: ' + label)
    result = dict(pid=full.pid, full_objects=len(full.objects), selected_objects=len(selected.objects),
        full_seconds=full_seconds, selected_seconds=selected_seconds, target=asdict(target),
        path=selected.path_name(target), rejected=rejected, exact_rows_match=True)
    (ROOT / 'evidence/selected-catalog-live.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
