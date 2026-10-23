"""Read-only verification of live demo Niagara components after cleanup."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references
from inspect_runtime_cinematic import object_row
c=capture();rows=[]
with ReadBatch(c.pid):
    for o in c.select('NiagaraComponent'):
        if o.object_flags&0x40000030:continue
        v,observed=read_values_with_references(c,o,fields=('Asset','bIsActive','bAutoDestroy','bAllowAnyoneToDestroyMe'))
        values={k[1]:object_row(observed,x) if hasattr(x,'class_index') else x for k,x in v.values.items()}
        if not any(s in str(values.get('Asset')) for s in ('NS_Impact_Electric1','FX_FlowerPetalsBurst','FX_MaelleSword','FX_LuneTrail')):continue
        rows.append(dict(object=object_row(c,o),outer=object_row(c,c.by_index[o.outer_index]),flags=o.object_flags,values=values,errors={k[1]:str(x) for k,x in v.errors.items()}))
out=ROOT/'evidence/runtime-cinematic-effect-components-20261017.json'
out.write_text(json.dumps(dict(pid=c.pid,read_only=True,components=rows),indent=2)+'\n')
print(json.dumps(dict(output=str(out),components=len(rows))))
