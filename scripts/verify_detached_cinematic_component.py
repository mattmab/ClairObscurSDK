"""Bounded detached component test. No initialization, registration or playback."""
import json
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.catalog import capture_matching
from expedition33.values import read_values, read_object_reference, StoredArray
from verify_music_reference_owner import hashes
ROOT=Path(__file__).resolve().parents[1]
def selected_values(values, owner_index):
    return {name:value for (owner,name),value in values.values.items() if owner==owner_index}

def run(mod):
    scope=SessionScope(mod.session)
    before=hashes()
    session=scope._session
    report={'playback_attempted':False,'initialized':False,
            'leases_before':repr(session._lease_command('lease-status'))}
    def one(values):
        rows=list(values)
        if len(rows)!=1: raise RuntimeError('Expected exactly one component probe dependency')
        return rows[0]
    try:
        catalog=capture_matching(scope.pid,names=('BP_CinematicSystem_C','Default__GameplayStatics','GameplayStatics','SpawnObject'),classes=('BP_jRPG_GI_Custom_C',))
        cls=one(o for o in catalog.objects if o.name=='BP_CinematicSystem_C' and o.class_name=='BlueprintGeneratedClass')
        gi=one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.name.startswith('Default__'))
        default=one(o for o in catalog.objects if o.name=='Default__GameplayStatics')
        owner=one(o for o in catalog.objects if o.name=='GameplayStatics' and o.class_name=='Class')
        fn=one(o for o in catalog.objects if o.name=='SpawnObject' and o.outer_index==owner.index)
        planner=scope.invocation_planner(catalog=catalog, selected_results=True)
        result=planner.prepare(default,fn,ObjectClass=cls,Outer=gi).invoke(refresh_from_result=True)
        obj=result.return_value
        if obj is None or obj.class_index!=cls.index or obj.outer_index!=gi.index:
            raise RuntimeError('Detached component ownership mismatch')
        report['identity']=[obj.index,obj.serial,obj.address]
        catalog=planner._catalog
        refs={}
        for name in ('CurrentCinematicWidget','SpawnedMediaPlayerActor','CurrentMediaPlayerWidget','LevelSequencePlayer','LevelSequencePlayerActor','CinematicTransitionWidget'):
            value,catalog=read_object_reference(catalog,obj,cls,name)
            refs[name]=value is None
        report['null_references']=refs
        values=read_values(catalog,obj)
        selected=selected_values(values, cls.index)
        report['value_errors']={str(key):str(value) for key,value in values.errors.items() if key[0]==cls.index}
        report['flags']={name:selected.get(name) for name in ('IsPlayingCinematic','CinematicPaused','HasInputLockFromPreCinematic','SequenceStarted','IsInTransition','PhotoModeRequested')}
        widgets=selected.get('SpawnedWidgets')
        report['spawned_widgets_empty']=isinstance(widgets,StoredArray) and len(widgets)==0
        report['defaults_verified']=all(refs.values()) and all(value is False for value in report['flags'].values()) and report['spawned_widgets_empty']
        if not report['defaults_verified']:raise RuntimeError('Detached component defaults not isolated')
    except Exception as error:
        report['error']=str(error)
    finally:
        scope.close()
        report['leases_after']=repr(session._lease_command('lease-status'))
        report['save_hashes_unchanged']=hashes()==before
        (ROOT/'evidence/detached-cinematic-component.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report
