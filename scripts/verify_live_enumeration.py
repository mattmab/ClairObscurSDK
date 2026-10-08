"""Live integration check. Requires the supported game process; no fixture fallback."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import expedition33


started = time.perf_counter()
objects = expedition33.objects()
elapsed = time.perf_counter() - started
assert len(objects) > 65536, 'This specimen must exercise more than one registry chunk'
assert any(obj.index >= 65536 for obj in objects), 'Second chunk was not observed'
specimens = {(obj.name, obj.class_name) for obj in objects}
for expected in [('Object', 'Class'), ('Class', 'Class'), ('/Script/CoreUObject', 'Package')]:
    assert expected in specimens, f'Missing expected core specimen: {expected}'
class_object = next(obj for obj in objects if obj.name == 'Class' and obj.class_name == 'Class')
assert class_object.index == class_object.class_index, 'Class is not its own metaclass'
summary = {
    'timestamp': datetime.now(timezone.utc).isoformat(), 'source': 'live native bridge invocation',
    'pid': objects[0].pid, 'count': len(objects), 'elapsed_seconds': elapsed,
    'max_index': max(obj.index for obj in objects),
    'class_counts': Counter(obj.class_name for obj in objects).most_common(15),
    'first_objects': [vars(obj) for obj in objects[:32]],
    'chunk_boundary': [vars(obj) for obj in objects if 65530 <= obj.index <= 65542],
}
path = Path(__file__).resolve().parents[1] / 'evidence' / 'python-live-enumeration.json'
path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({key: summary[key] for key in ['pid', 'count', 'elapsed_seconds', 'max_index']}))
for obj in objects[:20]:
    print(obj.name, obj.class_name)
