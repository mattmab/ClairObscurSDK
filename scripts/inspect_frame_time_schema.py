"""Read only the fixed timing ABI metadata needed for owned sequence observation."""
import argparse
import json
from pathlib import Path
from expedition33.catalog import capture_matching
from expedition33.reflection import describe
from title_timing_probe import copied_json

def inspect(pid):
    names=('FrameNumber','FrameTime','FrameRate','QualifiedFrameTime','GetCurrentTime','MovieSceneSequencePlayer')
    catalog=capture_matching(pid,names=names)
    targets=[]
    for name in names[:4]:
        matches=[o for o in catalog.objects if o.name==name and o.class_name=='ScriptStruct'
                 and catalog.path_name(o)=='/Script/CoreUObject.'+name]
        if len(matches)!=1: raise RuntimeError('Expected exact timing struct: '+name)
        targets.append(matches[0])
    owner=catalog.find_class('MovieSceneSequencePlayer').index
    matches=[o for o in catalog.objects if o.name=='GetCurrentTime' and o.class_name=='Function' and o.outer_index==owner]
    if len(matches)!=1: raise RuntimeError('Expected exact time getter')
    targets.extend(matches)
    return {catalog.path_name(o):copied_json(d) for o in targets
            for d in (describe(catalog,(o,))[o.index],)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid',type=int)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.pid),indent=2),encoding='utf8')
