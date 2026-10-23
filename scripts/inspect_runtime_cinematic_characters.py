"""Read only Lune/Maelle visual assembly and the native leader-pose contract."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct
from inspect_runtime_cinematic import object_row, inspect_schema


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();c=capture()
    if c.pid!=args.pid:raise RuntimeError('Game PID changed')
    rows=[]
    with ReadBatch(c.pid):
        for component in c.select('SkeletalMeshComponent'):
            path=c.path_name(component)
            if component.object_flags&0x30 or not any(s in path for s in ('BP_GameMenu_Lune_C_','BP_GameMenu_Maelle_C_')):
                continue
            values,observed=read_values_with_references(c,component,fields=('SkinnedAsset','LeaderPoseComponent','RelativeLocation','RelativeRotation','RelativeScale3D'))
            def copied(value):
                if isinstance(value,StoredStruct):return {key if isinstance(key,str) else key[1]:copied(item) for key,item in value.fields.items()}
                if hasattr(value,'class_index'):return object_row(observed,value)
                return value
            rows.append(dict(component=object_row(c,component),values={key[1]:copied(value)
                for key,value in values.values.items()},errors={key[1]:str(value) for key,value in values.errors.items()}))
        fn=next(o for o in c.objects if o.class_name=='Function' and o.name=='SetLeaderPoseComponent'
            and c.by_index[o.outer_index].name=='SkinnedMeshComponent')
        leader=inspect_schema(c,fn)
        hair=[object_row(c,o) for o in c.objects if o.class_name=='SkeletalMesh'
            and 'Hair' in c.path_name(o) and any(n in c.path_name(o) for n in ('Lune','Maelle'))]
    args.output.write_text(json.dumps(dict(pid=c.pid,read_only=True,dispatched=False,characters=rows,leader_pose=leader,hair_assets=hair),indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),components=len(rows),leader_codec=leader.get('python_codec'))))


if __name__=='__main__':main()
