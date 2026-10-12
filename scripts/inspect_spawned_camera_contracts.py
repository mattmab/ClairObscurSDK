"""Read loaded candidate spawn declarations; no loading, spawning or playback."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture, CatalogObject
from expedition33.values import read_values, StoredArray, StoredStruct
from expedition33.enums import describe_enums
from inspect_actor_cinematic_imports import PROFILES

def copied(value, catalog):
    if isinstance(value,CatalogObject):
        return dict(path=catalog.path_name(value),index=value.index,serial=value.serial,
                    address=hex(value.address),class_name=value.class_name)
    if isinstance(value,StoredStruct):
        return dict(type=value.type_object.name,fields={str(k):copied(v,catalog) for k,v in value.fields.items()},
                    errors={str(k):str(v) for k,v in value.errors.items()},truncated=value.truncated)
    if isinstance(value,StoredArray):
        return dict(length=value.length,items=[copied(v,catalog) for v in value.items])
    if value is None or type(value) in (str,int,float,bool):return value
    return dict(unsupported_type=type(value).__name__)

def run(pid):
    catalog=capture()
    if catalog.pid!=pid:raise RuntimeError('Game PID changed')
    ls=catalog.find_class('LevelSequence'); ms=catalog.find_class('MovieScene')
    rows=[]
    for _,path,_ in PROFILES:
        objects=[o for o in catalog.objects if o.class_name=='LevelSequence' and catalog.path_name(o)==path]
        row={'sequence':path,'found':len(objects)}; rows.append(row)
        if len(objects)!=1:continue
        asset=read_values(catalog,objects[0])
        scene=asset.values.get((ls.index,'MovieScene'))
        if not isinstance(scene,CatalogObject):
            row['error']='MovieScene not copied';continue
        observed=read_values(catalog,scene)
        key=(ms.index,'Spawnables')
        row['spawnables']=copied(observed.values.get(key),catalog)
        row['error']=str(observed.errors[key]) if key in observed.errors else None
    enum_objects=[o for o in catalog.objects if o.name=='ESpawnOwnership' and o.class_name=='Enum']
    enums=[]
    for obj in enum_objects:
        descriptor=describe_enums(catalog,(obj,))[obj.index]
        enums.append(dict(path=catalog.path_name(obj),members=[dict(name=m.name,value=m.value) for m in descriptor.members]))
    output=ROOT/'evidence/spawned-camera-contracts.json'
    output.write_text(json.dumps(dict(pid=pid,sequences=rows,enums=enums,
        observation_only=True,playback_attempted=False),indent=2),encoding='utf8')
    print(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pid',required=True,type=int)
    run(parser.parse_args().pid)
