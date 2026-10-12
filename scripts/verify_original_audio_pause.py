"""Pause/restore original soundtrack without starting cinematic playback."""
import json
import runpy
import subprocess
from pathlib import Path
from expedition33 import _decode_query
from expedition33.values import _decode_values, StoredMap

ROOT=Path(__file__).resolve().parents[1]

def save():
    (ROOT/'evidence/original-audio-pause-live.json').write_text(json.dumps(report,indent=2),encoding='utf8')

def states():
    rows=[]
    for obj in components:
        with planner.prepare(obj,get_state).invoke(refresh_from_result=True) as result:
            value=result.return_value
            rows.append(dict(index=obj.index,name=value.name,value=value.value))
    return rows

def begin(mod):
    global helper,context,scope,owner,planner,components,get_state,report
    helper=runpy.run_path(str(ROOT/'scripts/verify_music_reference_owner.py'))
    helper['begin'](mod)
    context=helper['begin'].__globals__
    scope,owner=context['scope'],context['audio_owner']
    report={'sequence_playback_attempted':False}
    try:
        catalog,original=context['catalog'],context['original']
        proc=subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),'--read-values',str(scope.pid),
            f'{original.index}:{original.serial}:{original.address:x}'],capture_output=True,text=True,check=True,
            timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        start,rows=_decode_query(proc.stdout)
        values=_decode_values(catalog,original,start,rows)
        music=next(v for k,v in values.values.items() if k[1]=='InteractiveMusicByContext')
        if not isinstance(music,StoredMap): raise ValueError('Missing music map')
        components=tuple({v.index:v for item in music.items.values() for name,v in item.fields.items()
            if name.startswith('AudioComponent_') and v is not None}.values())
        if not components: raise ValueError('No original soundtrack component to validate')
        planner=scope.invocation_planner(catalog=catalog)
        cls=next(o for o in catalog.objects if o.name=='AudioComponent' and o.class_name=='Class')
        default=next(o for o in catalog.objects if o.name=='Default__AudioComponent')
        get_state=next(o for o in catalog.objects if o.outer_index==cls.index and o.name=='GetPlayState')
        pause=next(o for o in catalog.objects if o.outer_index==cls.index and o.name=='SetPaused')
        report['before']=states()
        owner.pause_original_audio(planner.prepare(default,pause,bPause=False)._plan)
        report['paused']=states()
        report['owner']=owner.status()
    except BaseException as error:
        report['error']=repr(error)
        scope.close()
        raise
    finally: save()
    return report

def finish():
    report['after_escape']=states()
    report['restoration']=helper['finish']()
    report['original_states_restored']=report['after_escape']==report['before']
    save()
    return report
