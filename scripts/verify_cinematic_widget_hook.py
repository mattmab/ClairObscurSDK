"""Arm and close exact widget routing without playing any sequence."""
import json
from pathlib import Path
from expedition33.catalog import capture_matching
from expedition33.sequences import OwnedLevelSequence
from expedition33._cinematic_widget import NativeCinematicWidgets
from verify_music_reference_owner import hashes

ROOT=Path(__file__).resolve().parents[1]
def run(mod):
    report={'playback_attempted':False};sequence=None;before=hashes()
    session=mod.session._session
    report['leases_before']=repr(session._lease_command('lease-status'))
    def one(rows):
        rows=list(rows)
        if len(rows)!=1:raise RuntimeError('Expected one widget admission dependency')
        return rows[0]
    try:
        mod.pause.open()
        sequence=OwnedLevelSequence(mod.session)
        sequence.build(mod.native.menu.panel,'/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        report['leases_before_arm']=repr(session._lease_command('lease-status'))
        owner=prepare(sequence)
        report['armed']=owner.status()
        if not sequence.owner.close():raise RuntimeError('Native sequence cleanup deferred')
        report['closed']=owner.status()
        sequence.close()
    except BaseException as error:
        report['error']=repr(error)
        report['native_error']=getattr(error,'native_error',None)
    finally:
        if sequence is not None:
            try:sequence.close()
            except BaseException as error:report['cleanup_error']=repr(error)
        try:report['leases_after']=repr(session._lease_command('lease-status'))
        except BaseException as error:report['lease_status_error']=repr(error)
        report['save_hashes_unchanged']=hashes()==before
        (ROOT/'evidence/cinematic-widget-arm.json').write_text(json.dumps(report,indent=2))
    return report

def prepare(sequence):
    def one(rows):
        rows=list(rows)
        if len(rows)!=1:raise RuntimeError("Expected one widget admission dependency")
        return rows[0]
    scope=sequence.scope
    names=('BP_CinematicSystem_C','Default__GameplayStatics','GameplayStatics','SpawnObject',
        'GetCinematicsSystem','GetComponentByClass','Default__FL_jRPG_CustomFunctionLibrary_C',
        'ExecuteUbergraph_BP_WidgetSequencerTrackInstance','BP_WidgetSequencerTrackInstance_C',
        'UserWidget','Default__UserWidget','RegisterSpawnedWidget','UnregisterSpawnedWidget',
        'UpdateCinematicControlsWidget','RemoveFromParent')
    catalog=capture_matching(scope.pid,names=names,classes=('BP_jRPG_GI_Custom_C',))
    cls=one(o for o in catalog.objects if o.name=='BP_CinematicSystem_C' and o.class_name=='BlueprintGeneratedClass')
    gi=one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.name.startswith('Default__'))
    default=one(o for o in catalog.objects if o.name=='Default__GameplayStatics')
    statics=one(o for o in catalog.objects if o.name=='GameplayStatics' and o.class_name=='Class')
    spawn=one(o for o in catalog.objects if o.name=='SpawnObject' and o.outer_index==statics.index)
    planner=scope.invocation_planner(catalog=catalog,selected_results=True)
    component=planner.prepare(default,spawn,ObjectClass=cls,Outer=gi).invoke(refresh_from_result=True).return_value
    if component is None or component.class_index!=cls.index or component.outer_index!=gi.index:
        raise RuntimeError('Private cinematic component factory mismatch')
    def named(name):return one(o for o in planner._catalog.objects if o.name==name)
    resources={
        'getter':named('GetCinematicsSystem'),'native_getter':named('GetComponentByClass'),
        'library':named('Default__FL_jRPG_CustomFunctionLibrary_C'),'component':component,
        'graph':named('ExecuteUbergraph_BP_WidgetSequencerTrackInstance'),
        'track_class':named('BP_WidgetSequencerTrackInstance_C'),'widget_class':named('UserWidget'),
        'register':named('RegisterSpawnedWidget'),'unregister':named('UnregisterSpawnedWidget'),
        'controls':named('UpdateCinematicControlsWidget'),'remove':named('RemoveFromParent')}
    remove=planner.prepare(named('Default__UserWidget'),resources['remove'])._plan
    owner=NativeCinematicWidgets(scope)
    owner.prepare(resources,sequence.player,remove)
    return owner
