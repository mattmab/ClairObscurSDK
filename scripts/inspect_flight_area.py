"""Read-only inventory of current pawns and movement modes for flight research."""
from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33._reader import ReadBatch

c = capture()
rows = []
selected = {o.index for cls in ('Pawn', 'PlayerController', 'CharacterMovementComponent') for o in c.select(cls)}
with ReadBatch(c.pid):
    for obj in c.objects:
        if obj.object_flags & 0x10:
            continue
        if obj.index not in selected:
            continue
        v = read_values(c, obj)
        fields = {f'{c.by_index[k[0]].name}.{k[1]}': repr(value)
                  for k, value in v.values.items()
                  if any(s in k[1] for s in ('Pawn', 'Controller', 'MovementMode', 'Jump', 'Movement', 'Velocity'))}
        rows.append(dict(index=obj.index, serial=obj.serial, cls=obj.class_name,
                         path=c.path_name(obj), fields=fields))
out = ROOT/'evidence/flight-area-inventory.json'
out.write_text(json.dumps(dict(pid=c.pid, rows=rows), indent=2), encoding='utf-8')
print(out)
