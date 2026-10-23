"""Observe native Lune hair Blueprints/templates; never spawn gameplay actors."""
import argparse,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct
from inspect_runtime_cinematic import object_row,inspect_schema


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();c=capture()
    if c.pid!=args.pid:raise RuntimeError('Game PID changed')
    report=dict(pid=c.pid,read_only=True,dispatched=False,objects=[],functions=[],templates=[])
    hair_classes=[o for o in c.objects if o.class_name=='BlueprintGeneratedClass' and 'hair' in c.path_name(o).lower() and ('lune' in c.path_name(o).lower() or 'haircut' in c.path_name(o).lower())]
    report['objects']=[object_row(c,o) for o in hair_classes]
    with ReadBatch(c.pid):
        for o in c.objects:
            if o.class_name=='Function' and ('hair' in o.name.lower()) and c.by_index[o.outer_index].class_name=='BlueprintGeneratedClass':
                report['functions'].append(object_row(c,o))
        for o in c.select('SkeletalMeshComponent'):
            path=c.path_name(o)
            # Search by the actual mesh, including generically named runtime
            # components whose actor/component names do not mention Lune.
            v,observed=read_values_with_references(c,o,fields=('SkinnedAsset','AttachParent','AttachSocketName','LeaderPoseComponent','RelativeLocation','RelativeRotation','RelativeScale3D'))
            def copy(x):
                if isinstance(x,StoredStruct):return {k:copy(value) for k,value in x.fields.items()}
                if hasattr(x,'class_index'):return object_row(observed,x)
                return x
            values={k[1]:copy(value) for k,value in v.values.items()}
            asset=values.get('SkinnedAsset')
            if asset is None or not any(s in str(asset).lower() for s in ('hair','lune')):continue
            report['templates'].append(dict(object=object_row(c,o),object_flags=o.object_flags,values=values,errors={k[1]:str(x) for k,x in v.errors.items()}))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),classes=len(hair_classes),functions=len(report['functions']),templates=len(report['templates']))))


if __name__=='__main__':main()
