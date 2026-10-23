"""Original BP_BattleMap focus update for an inert owned arena only."""
import math
from ._reader import ReadBatch
from .catalog import capture_matching, capture_selected
from .values import read_values_with_references
from .cinematics.original_game_action import controller_context
from ._npc_encounter_preparation import _controller_battle_manager

ARENA='/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C'
CAMERA='/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_DynamicCameraPath.BP_jRPG_DynamicCameraPath_C'
PAIRS=(('OverviewCameraFocusPoint','BP_jRPG_CameraPath_Overview'),
       ('TargetingEnemyCameraFocusPoint','BP_jRPG_CameraPath_TargetingEnemy'),
       ('TargetingAllyCameraFocusPoint','BP_jRPG_CameraPath_TargetingAlly'),
       ('IntroCameraFocusPoint1','BP_jRPG_CameraPath_Intro'))


def _identity(o):return o.index,o.serial,o.address


def _read(c,obj,names):
    values,c=read_values_with_references(c,obj,fields=names)
    result={k[1]:v for k,v in values.values.items()}
    if values.errors or set(result)!=set(names):raise RuntimeError('Incomplete owned camera fields')
    return result,c


def _exact(c,path):
    rows=[o for o in c.objects if c.path_name(o)==path]
    if len(rows)!=1:raise RuntimeError('Missing/ambiguous camera prerequisite: '+path)
    return rows[0]


def _position(value):
    if hasattr(value,'fields'):
        if value.errors or value.truncated:raise RuntimeError('Incomplete camera position')
        value=value.fields
    position=tuple(value[k] for k in 'XYZ')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in position):
        raise RuntimeError('Invalid camera position')
    return position


def refresh_camera_focus(owner):
    scope=owner._scope
    context=controller_context(scope._session)
    actor_id=owner.actor_identity
    def batch():return ReadBatch(scope.pid,share=True,_executable=owner._transport._executable)
    def idle():
        if controller_context(scope._session)!=context:raise RuntimeError('Travel during camera preparation')
        with batch():
            c=capture_selected(scope.pid,(tuple(context['controller'][1:]),))
            manager,c=_controller_battle_manager(c,c.by_index[context['controller'][1]])
            v,c=_read(c,manager,('IsBattleInitialized','HasBattleStartedEndFlow','Enemies','BattleMapBP'))
            if v['IsBattleInitialized'] or v['HasBattleStartedEndFlow'] or v['Enemies'].length or v['BattleMapBP'] is not None:
                raise RuntimeError('Preserve active battle or transition')
    def joins(c,actor):
        v,c=_read(c,actor,('bHidden','bActorEnableCollision',*(n for pair in PAIRS for n in pair)))
        if not v['bHidden'] or v['bActorEnableCollision']:raise RuntimeError('Camera refresh requires an inert owned arena')
        targets={}
        for point,camera in PAIRS:
            for field,kind in ((point,'SceneComponent'),(camera,'ChildActorComponent')):
                part=v[field]
                if part is None or part.outer_index!=actor.index or part.outer_serial!=actor.serial or c.path_name(c.by_index[part.class_index])!='/Script/Engine.'+kind:
                    raise RuntimeError('Owned camera component identity differs')
            fields,c=_read(c,v[camera],('ChildActor','ChildActorClass'))
            target=fields['ChildActor']
            if target is None or fields['ChildActorClass'] is None or target.class_index!=fields['ChildActorClass'].index or c.path_name(fields['ChildActorClass'])!=CAMERA:
                raise RuntimeError('Original camera child differs')
            targets[camera]=target
        return v,targets,c
    idle()
    planner=None
    try:
        with batch():
            c=capture_selected(scope.pid,(actor_id,))
            c=c.with_observations(capture_matching(scope.pid,names=('UpdateCamerasLookAtPoints','K2_GetComponentLocation','Vector')))
            actor=c.by_index[actor_id[0]]
            if _identity(actor)!=tuple(actor_id) or ARENA not in {c.path_name(c.by_index[i]) for i in c.ancestors(actor.class_index)}:
                raise RuntimeError('Original owned arena identity differs')
            _exact(c,'/Script/CoreUObject.Vector')
            parts,targets,c=joins(c,actor)
            planner=scope.invocation_planner(catalog=c,selected_results=True)
            call=planner.prepare_blueprint(actor,_exact(c,ARENA+':UpdateCamerasLookAtPoints'))
            getter=_exact(c,'/Script/Engine.SceneComponent:K2_GetComponentLocation')
            queries=[(camera,planner.prepare(parts[point],getter)) for point,camera in PAIRS]
        report=dict(phase='prepared',function=ARENA+':UpdateCamerasLookAtPoints',expected={},verified=False)
        owner.camera_focus=report
        for camera,query in queries:
            idle()
            with query.invoke() as result:
                if result.outcome!='dispatch_returned':raise RuntimeError('Camera position getter incomplete')
                report['expected'][camera]=_position(result.return_value)
        idle()
        owner._camera_focus_attempted=True
        owner._component_uncertain=True
        report['phase']='dispatch_intent'
        with call.invoke() as result:
            if result.outcome!='dispatch_returned':raise RuntimeError('Camera update incomplete; do not replay')
            report['phase']='dispatch_returned'
        with batch():
            c=capture_selected(scope.pid,(actor_id,*(_identity(o) for o in targets.values())))
            actor=c.by_index[actor_id[0]]
            if _identity(actor)!=tuple(actor_id):raise RuntimeError('Owned arena changed after camera update')
            final_parts,final_targets,c=joins(c,actor)
            for point,camera in PAIRS:
                if any(_identity(final_parts[n])!=_identity(parts[n]) for n in (point,camera)) or _identity(final_targets[camera])!=_identity(targets[camera]):
                    raise RuntimeError('Camera component/child replaced during update')
                values,c=_read(c,final_targets[camera],('CameraFocusPoint',))
                position=_position(values['CameraFocusPoint'])
                if any(abs(a-b)>.001 for a,b in zip(position,report['expected'][camera])):
                    raise RuntimeError('Original camera focus readback differs')
        idle()
        report.update(phase='verified',verified=True)
        owner._component_uncertain=False
        return report
    finally:
        if planner is not None:planner.close()
