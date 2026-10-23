"""Read-only live character templates and animation eligibility inventory."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct,StoredArray

def main():
    p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);args=p.parse_args()
    output=ROOT/'evidence/scene-editor/palette-inspection.json';report=dict(pid=args.pid,read_only=True,animations=[],components=[],meshes=[])
    with ReadBatch(args.pid,_executable=ROOT/'build/release/research-probe-cinematic-v14/research_probe.exe'):
        c=capture()
        if c.pid!=args.pid:raise ValueError('Game process changed')
        def read(obj,fields):
            v,observed=read_values_with_references(c,obj,fields=fields)
            def copy(x):
                if hasattr(x,'class_index'):return observed.path_name(x)
                if isinstance(x,StoredStruct):return {k if isinstance(k,str) else k[1]:copy(value) for k,value in x.fields.items()}
                if isinstance(x,StoredArray):return dict(length=x.length)
                return x
            return dict(values={k[1]:copy(value) for k,value in v.values.items()},errors={k[1]:str(value) for k,value in v.errors.items()})
        for obj in c.select('AnimSequence'):
            path=c.path_name(obj)
            if obj.object_flags&0x40000030 or not path.startswith(('/Game/Characters/','/Game/Animations/')):continue
            row=dict(path=path,**read(obj,('Skeleton','Notifies','bEnableRootMotion','SequenceLength','AdditiveAnimType')))
            v=row['values'];row['eligible']=not row['errors'] and v.get('Notifies',{}).get('length')==0 and v.get('bEnableRootMotion') is False
            report['animations'].append(row)
        for obj in c.select('SkeletalMeshComponent'):
            if obj.object_flags&0x40000000:continue
            row=dict(path=c.path_name(obj),**read(obj,('SkinnedAsset','AttachParent','AttachSocketName','LeaderPoseComponent','RelativeLocation','RelativeRotation','RelativeScale3D')))
            if any(name in str(row) for name in ('Verso','Sciel','Gustave','Monoco','Noah')):report['components'].append(row)
        for obj in c.select('SkeletalMesh'):
            path=c.path_name(obj)
            if path.startswith('/Game/') and any(name in path for name in ('Verso','Sciel','Gustave','Monoco','Noah')):report['meshes'].append(dict(path=path,**read(obj,('Skeleton',))))
        from expedition33.reflection import describe
        cls=c.by_index[c.find_class('AnimSequence').index]
        report['animation_schema']=[dict(p) for p in describe(c,(cls,))[cls.index].properties]
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(output=str(output),animations=len(report['animations']),eligible=sum(r['eligible'] for r in report['animations']),components=len(report['components']),meshes=len(report['meshes']))))

if __name__=='__main__':main()
