"""Source-qualified presentation on an SDK-owned Faceless Boy visual."""
from .assets import load_asset
from .catalog import capture_matching,capture_selected

def _body(scope,actor):
    from .values import capture_selected_values
    from .story_animation import body_from_observation
    c,rows=capture_selected_values(scope.pid,(actor,),fields=('Body',),references=True)
    row=rows[actor[0]]
    if row.errors or row.truncated:raise RuntimeError('Owned NPC Body observation incomplete')
    return c,body_from_observation(c,actor,row)

FACELESS_SCALE=(0.9,0.9000000210948613,0.9000000210948613)
FACELESS_IDLE='/Game/Animations/Idles/Idles_Lune/Idles_hands_back_Lune_UE5_FootUp.Idles_hands_back_Lune_UE5_FootUp'

def configure_faceless_boy_npc(visual):
    """Apply the source TrainBoy scale and idle to an owned visual."""
    from ._reader import shared_operation
    with shared_operation(visual.scope.pid):return _configure_faceless_boy_npc(visual)

def _configure_faceless_boy_npc(visual):
    """Match the original TrainBoy mesh scale and looping NPC idle.

    The cinematic visual defaults to 0.7 scale and has no idle. Only the
    retained owned actor's Body component is changed; original world NPCs and
    shared class defaults are never edited. Failed configuration is not replayed.
    """
    if visual.profile!='faceless-boy' or visual.state not in ('prepared','visible'):
        raise ValueError('Prepared owned Faceless Boy visual required')
    if getattr(visual,'_npc_presentation_attempted',False):raise RuntimeError('NPC presentation configuration is one-shot')
    scope=visual.scope;scope._check()
    prepared=getattr(scope._session,'_story_construction_resources',None)
    animation=prepared.resources.load(FACELESS_IDLE) if prepared is not None else load_asset(scope,FACELESS_IDLE).return_value
    if animation is None or animation.class_name!='AnimSequence':raise RuntimeError('Original Faceless Boy idle unavailable')
    if prepared is not None:
        c,body=_body(scope,visual.identity)
        c=c.with_observations(prepared.catalog(scope,('PlayAnimation','SetRelativeScale3D','Vector','AnimationAsset')))
        bodies=[body]
    else:
        c=capture_matching(scope.pid,names=('Body','PlayAnimation','SetRelativeScale3D','Vector','AnimationAsset'))
        bodies=[o for o in c.objects if o.outer_index==visual.identity[0] and o.name=='Body' and o.class_name=='SkeletalMeshComponent']
    if len(bodies)!=1:raise RuntimeError('Owned Faceless Boy Body component unavailable')
    body=bodies[0]
    idle_path='/Script/Engine.SkeletalMeshComponent:PlayAnimation'
    scale_path='/Script/Engine.SceneComponent:SetRelativeScale3D'
    warm=getattr(scope._session,'_story_performance_preflight',None)
    if warm is not None and {idle_path,scale_path}<=warm.paths:
        planner=warm.planner(scope,body,idle_path,dict(NewAnimToPlay=animation,bLooping=True))
        c=planner._catalog
    else:
        c=c.with_observations(capture_selected(scope.pid,((animation.index,animation.serial,animation.address),)))
        planner=scope.invocation_planner(catalog=c,selected_results=True)
    with planner:
        scale=planner.prepare(body,c.find_path('/Script/Engine.SceneComponent:SetRelativeScale3D'),NewScale3D=dict(zip('XYZ',FACELESS_SCALE)))
        idle=planner.prepare(body,c.find_path('/Script/Engine.SkeletalMeshComponent:PlayAnimation'),NewAnimToPlay=animation,bLooping=True)
        visual._npc_presentation_attempted=True
        with scale.invoke():pass
        with idle.invoke():pass
    return verify_faceless_boy_npc(visual)

def verify_faceless_boy_npc(visual):
    """Read actual runtime playback; PlayAnimation does not update saved AnimationData."""
    scope=visual.scope
    from .values import capture_selected_values
    c,body=_body(scope,visual.identity)
    c,rows=capture_selected_values(scope.pid,((body.index,body.serial,body.address),),
        fields=('RelativeScale3D','AnimationMode','AnimScriptInstance'),references=True)
    values=rows[body.index]
    data={k[1]:v for k,v in values.values.items()}
    if values.errors or values.truncated or data.get('AnimationMode')!=1:raise RuntimeError('NPC idle configuration was not acknowledged')
    if tuple(data['RelativeScale3D'].fields[n] for n in 'XYZ')!=FACELESS_SCALE:
        raise RuntimeError('NPC mesh scale differs from source')
    instance=data.get('AnimScriptInstance')
    if instance is None or instance.class_name!='AnimSingleNodeInstance':raise RuntimeError('NPC idle instance unavailable')
    c,rows=capture_selected_values(scope.pid,((instance.index,instance.serial,instance.address),),fields=('CurrentAsset',),references=True)
    values=rows[instance.index]
    assets=[v for k,v in values.values.items() if k[1]=='CurrentAsset']
    if values.errors or values.truncated or len(assets)!=1 or assets[0] is None or c.path_name(assets[0])!=FACELESS_IDLE:
        raise RuntimeError('NPC runtime idle differs from source')
    visual._npc_presentation_ready=True
    return dict(scale=FACELESS_SCALE,idle=FACELESS_IDLE)
