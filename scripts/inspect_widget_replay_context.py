"""Load the title asset without playing; inspect exact widget-track contracts."""
import json
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.assets import load_asset
from expedition33.catalog import capture
from expedition33 import _query

ROOT=Path(__file__).resolve().parents[1]

def run(mod):
    records=[]
    scope=SessionScope(mod.session)
    try:
        load_asset(scope,'/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        catalog=capture()
        names={'MovieSceneTrackInstance','MovieSceneTrackInstanceInput','MovieSceneEntitySystemLinker',
               'MovieSceneCustomTrackInstance','BP_WidgetSequencerTrackInstance_C','BP_WidgetSequencerSection_C'}
        classes={o.index for o in catalog.objects if o.name in names and o.class_name in ('Class','BlueprintGeneratedClass','ScriptStruct')}
        for obj in catalog.objects:
            if obj.index not in classes and not (obj.outer_index in classes and obj.class_name=='Function'): continue
            row=dict(path=catalog.path_name(obj),identity=[obj.index,obj.serial,obj.address])
            try:
                row['start'],row['rows']=_query(['--describe',str(scope.pid),f'{obj.index}:{obj.serial}:{obj.address:x}'])
            except Exception as error: row['error']=repr(error)
            records.append(row)
    finally:
        scope.close()
        (ROOT/'evidence/widget-replay-context.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    return {'contracts':len(records),'errors':sum('error' in r for r in records)}
