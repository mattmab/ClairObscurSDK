"""Read-only survey of cinematic discovery and save history."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch

catalog = capture()
words = ('cinematic', 'cutscene', 'savegame', 'savemanager', 'sequenceplayer')
objects = [o for o in catalog.objects if any(w in o.name.lower() for w in words)]
rows = []
with ReadBatch(catalog.pid):
    for o in objects:
        row = dict(path=catalog.path_name(o), name=o.name, cls=o.class_name)
        if o.class_name in ('Class', 'BlueprintGeneratedClass', 'Function'):
            try:
                d = describe(catalog, (o,))[o.index]
                row['properties'] = [dict(p) for p in d.properties]
                row['function'] = dict(d.function) if d.function else None
            except Exception as e:
                row['error'] = str(e)
        rows.append(row)
out = ROOT / 'evidence/cinematics-survey.json'
out.write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(out)
for row in rows:
    print(row['cls'], row['path'])
