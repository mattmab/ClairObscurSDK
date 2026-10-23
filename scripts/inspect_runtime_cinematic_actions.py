"""Read-only attack-animation and attachment contracts for the staged demo."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references
from expedition33.reflection import describe
from expedition33.enums import describe_enums
from inspect_runtime_cinematic import object_row,inspect_schema


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();c=capture()
    if c.pid!=args.pid:raise RuntimeError('Game PID changed')
    rows=[];weapons=[];schemas=[]
    pairs=(('SkeletalMeshComponent','SetPosition'),('SceneComponent','K2_AttachToComponent'),
        ('SkinnedMeshComponent','GetNumBones'),('SkinnedMeshComponent','GetBoneName'),
        ('SkinnedMeshComponent','GetBoneTransform'))
    with ReadBatch(c.pid):
        for owner,name in pairs:
            fn=next(o for o in c.objects if o.class_name=='Function' and o.name==name and c.by_index[o.outer_index].name==owner)
            schemas.append(inspect_schema(c,fn))
        for obj in c.objects:
            path=c.path_name(obj)
            if obj.class_name=='AnimSequence' and any(s in path for s in ('Lune','Maelle')) and any(s in path.lower() for s in ('attack','combo','basic','slash','skill')):
                rows.append(object_row(c,obj))
            if obj.class_name=='SkeletalMeshComponent' and obj.name=='WeaponMesh_R_SK' and 'Maelle' in path and not obj.object_flags&0x30:
                values,observed=read_values_with_references(c,obj,fields=('SkinnedAsset',))
                weapons += [object_row(observed,v) for v in values.values.values() if v is not None]
        cls=c.by_index[c.find_class('AnimSequenceBase').index]
        d=describe(c,(cls,))[cls.index]
        length=dict(next(p for p in d.properties if p['name']=='SequenceLength'))
        enum=next(o for o in c.objects if o.class_name=='Enum' and o.name=='EAttachmentRule')
        attachment_rules=[dict(name=m.name,value=m.value) for m in describe_enums(c,(enum,))[enum.index].members]
    args.output.write_text(json.dumps(dict(pid=c.pid,read_only=True,dispatched=False,interfaces=schemas,
        animations=rows,weapons=weapons,sequence_length_field=length,attachment_rules=attachment_rules),indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),animations=len(rows),weapons=len(weapons))))


if __name__=='__main__':main()
