"""Read-only attack VFX, target reactions and bounded engine contracts."""
import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct,StoredArray
from inspect_runtime_cinematic import object_row,inspect_schema
parser=argparse.ArgumentParser();parser.add_argument('--pid',type=int,required=True);args=parser.parse_args()
c=capture()
if c.pid!=args.pid:raise RuntimeError('PID changed')
effects=[];animations=[];functions=[];notifies=[]
with ReadBatch(c.pid):
    for o in c.objects:
        path=c.path_name(o)
        if o.class_name in ('NiagaraSystem','ParticleSystem') and any(s in path.lower() for s in ('lune','maelle','thunder','lightning','hit','impact','slash','sword','petank')):
            effects.append(object_row(c,o))
        if o.class_name=='Function' and o.name in ('SpawnSystemAtLocation','SpawnEmitterAtLocation','Deactivate','DeactivateImmediate','SetPosition','GetSocketLocation'):
            owner=c.by_index[o.outer_index].name
            if owner in ('NiagaraFunctionLibrary','GameplayStatics','NiagaraComponent','ParticleSystemComponent','SkeletalMeshComponent','SceneComponent'):
                functions.append(inspect_schema(c,o))
        if o.class_name=='AnimSequence' and any(s in path.lower() for s in ('petank','hitreact','hit_react','hitreaction','gethit','takehit')):
            v,observed=read_values_with_references(c,o,fields=('Skeleton','SequenceLength','Notifies','bEnableRootMotion'))
            def copied(x):
                if isinstance(x,StoredStruct):return {k:copied(a) for k,a in x.fields.items()}
                if isinstance(x,StoredArray):return dict(length=x.length)
                if hasattr(x,'class_index'):return object_row(observed,x)
                return x
            animations.append(dict(object=object_row(c,o),values={k[1]:copied(x) for k,x in v.values.items()},errors={k[1]:str(x) for k,x in v.errors.items()}))
        if ('AnimNotify' in o.class_name or 'NotifyState' in o.class_name) and any(s in path for s in ('Lune_Thunder','DancingFury')):
            notifies.append(object_row(c,o))
out=ROOT/'evidence/runtime-cinematic-effects-20261017.json'
out.write_text(json.dumps(dict(pid=c.pid,read_only=True,effects=effects,animations=animations,functions=functions,notifies=notifies),indent=2)+'\n')
print(json.dumps(dict(output=str(out),effects=len(effects),animations=len(animations),functions=len(functions),notifies=len(notifies))))
