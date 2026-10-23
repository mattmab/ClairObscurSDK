"""Read-only native weapon assembly reference, including component templates."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct
from inspect_runtime_cinematic import object_row
c=capture();rows=[]
with ReadBatch(c.pid):
    for o in (*c.select('SkeletalMeshComponent'),*c.select('StaticMeshComponent')):
        if not any(s in c.path_name(o).lower() for s in ('maelle','weaponmesh')):continue
        asset_field='StaticMesh' if o.class_name=='StaticMeshComponent' else 'SkinnedAsset'
        v,observed=read_values_with_references(c,o,fields=(asset_field,'AttachParent','AttachSocketName','RelativeLocation','RelativeRotation','RelativeScale3D'))
        def copied(x):
            if isinstance(x,StoredStruct):return {k:copied(a) for k,a in x.fields.items()}
            if hasattr(x,'class_index'):return object_row(observed,x)
            return x
        values={k[1]:copied(x) for k,x in v.values.items()}
        if not any(s in str(values.get(asset_field)).lower() for s in ('sword','weapon')) and 'maelle' not in c.path_name(o).lower():continue
        rows.append(dict(object=object_row(c,o),flags=o.object_flags,values=values,errors={k[1]:str(x) for k,x in v.errors.items()}))
target=ROOT/'evidence/runtime-cinematic-native-grip-20261017.json'
target.write_text(json.dumps(dict(pid=c.pid,read_only=True,components=rows),indent=2)+'\n')
print(json.dumps(dict(output=str(target),components=len(rows))))
