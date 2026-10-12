"""Read-only sequence/loading contracts for the currently running game."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch

c=capture()
owners={'LevelSequencePlayer','LevelSequenceActor','MovieSceneSequencePlayer',
        'MovieSceneSequencePlaybackSettings','MovieSceneSequenceLoopCount',
        'MovieSceneSequenceTickInterval','TopLevelAssetPath',
        'SoftObjectPath','SoftClassPath','MovieScene','MovieSceneEventTrack',
        'MovieSceneSequence','LevelSequence','KismetSystemLibrary'}
functions={'LoadAsset_Blocking','LoadClassAsset_Blocking','MakeSoftObjectPath',
           'Conv_SoftObjectPathToSoftObjectRef','CreateLevelSequencePlayer',
           'Play','Pause','Stop','PlayReverse','SetPlayRate','GetPlayRate',
           'SetPlaybackPosition','SetBinding','ResetBindings','SetSequence',
           'GetSequencePlayer','GetBoundObjects','SetDisableCameraCuts'}
targets=[o for o in c.objects if (o.name in owners and o.class_name in ('Class','ScriptStruct')) or
         (o.name in functions and o.class_name=='Function' and c.by_index.get(o.outer_index) and
          c.by_index[o.outer_index].name in owners)]
rows=[]
with ReadBatch(c.pid):
    for o in targets:
        try:
            d=describe(c,(o,))[o.index]
            rows.append(dict(path=c.path_name(o),properties=[dict(p) for p in d.properties],
                             function=dict(d.function) if d.function else None))
        except Exception as error: rows.append(dict(path=c.path_name(o),error=str(error)))
out=ROOT/'evidence/sequence-support-schema.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf8')
from expedition33.enums import describe_enums
enum_objects=[o for o in c.objects if o.class_name=='Enum' and o.name=='EMovieSceneCompletionModeOverride']
if enum_objects:
    enums=describe_enums(c,enum_objects)
    (ROOT/'evidence/sequence-completion-enum.json').write_text(json.dumps({
        c.path_name(o):[dict(name=m.name,value=m.value) for m in enums[o.index].members]
        for o in enum_objects},indent=2),encoding='utf8')
live=[dict(path=c.path_name(o),index=o.index,serial=o.serial,cls=o.class_name)
      for o in c.objects if o.class_name in ('LevelSequence','LevelSequenceActor','LevelSequencePlayer')]
(ROOT/'evidence/sequence-live-objects.json').write_text(json.dumps(live,indent=2),encoding='utf8')
print(c.pid,len(rows),out)
