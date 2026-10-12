"""Narrow read-only contracts for replacing unowned title sounds."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch
c=capture()
rows=[]
with ReadBatch(c.pid):
    for obj in c.objects:
        parent=c.by_index.get(obj.outer_index)
        if obj.class_name!='Function' or parent is None: continue
        if ((parent.name=='GameplayStatics' and obj.name in ('CreateSound2D','PlaySound2D','SpawnSound2D')) or
            (parent.name=='AudioComponent' and obj.name in ('Play','IsPlaying','SetVolumeMultiplier','SetPaused'))):
            d=describe(c,(obj,))[obj.index]
            rows.append({'path':c.path_name(obj),'function':dict(d.function),
                         'properties':[dict(p) for p in d.properties]})
(ROOT/'evidence/cinematic-sound-calls.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps([{'path':r['path'],'function':r['function']} for r in rows],indent=2))
