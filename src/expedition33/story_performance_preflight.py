"""Shared asset/schema observations for dialogue performance, without posing actors.

Only assets and reflected function/type identities are cached. Every later call
adopts fresh target/argument identities and retains native schema validation.
No pawn, face component, animation instance or restoration value is cached here.
"""
from .story_dialogue import identity
from .story_preflight import observe

HUMAN='/Game/MetaHumans/Common/Face/Face_AnimBP_HumanNPC.Face_AnimBP_HumanNPC_C'
NPC='/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C'
MOUTH='/Game/Animations/Facial/RandomDialogue_Animation/RandomDialogueAnim_Face_2.RandomDialogueAnim_Face_2'
PATHS=tuple('/Script/Engine.'+owner+':'+name for owner,names in (
    ('AnimInstance',('PlaySlotAnimationAsDynamicMontage','Montage_Stop','Montage_IsPlaying')),
    ('SkeletalMeshComponent',('PlayAnimation','SetPlayRate','SetPosition','SetAnimClass','SetDisablePostProcessBlueprint')),
    ('ActorComponent',('SetComponentTickEnabled','IsComponentTickEnabled','K2_DestroyComponent')),
    ('SceneComponent',('GetRelativeTransform','SetRelativeScale3D')),('Actor',('AddComponentByClass',))) for name in names)+(
    '/Game/Gameplay/CharacterCustomization/Blueprints/BP_CharacterSkinComponent.BP_CharacterSkinComponent_C:GetFaceSkeletalMesh',
    *(HUMAN+':'+name for name in ('SetPostProcessAnimation','BlueprintBeginPlay','BlueprintUpdateAnimation')),
    *(NPC+':'+name for name in ('SetFacialExpression','SetIsTalking','SetIsInDialogue','UpdateEnvelopeVolume')))


def _pod_closure(pid,snapshot):
    """Observe nested POD schemas before sharing function planning metadata.

    A function returning Transform initially supplies the Transform identity,
    but its own fields reference Quat and Vector. Copy all three bounded POD
    levels accepted by the invocation codec; never fill missing types by name.
    """
    from .reflection import describe_selected
    catalog=snapshot.catalog;descriptors=dict(snapshot.descriptors)
    frontier=tuple(descriptors.values())
    for _ in range(3):
        pending={row['struct_index']:catalog.by_index[row['struct_index']]
                 for descriptor in frontier for row in descriptor.properties
                 if row['type']=='StructProperty' and row['struct_index'] not in descriptors}
        if not pending:return catalog,descriptors
        if len(descriptors)+len(pending)>256:raise ValueError('Performance POD metadata exceeds planner bound')
        child=observe(describe_selected,pid,tuple(identity(obj) for obj in pending.values()))
        catalog=catalog.with_observations(child.catalog)
        descriptors.update(child.descriptors);frontier=tuple(child.descriptors.values())
    if any(row['type']=='StructProperty' and row['struct_index'] not in descriptors
           for descriptor in frontier for row in descriptor.properties):
        raise ValueError('Performance POD metadata exceeds supported depth')
    return catalog,descriptors


class PerformancePreflight:
    def __init__(self,scope):
        from .catalog import capture_matching
        from .reflection import describe_selected
        scope._check();self.session=scope._session;self.observations=None;self.paths=frozenset(PATHS)
        resources=self.session._story_construction_resources.resources
        resources.load(HUMAN,cls=True);resources.load(NPC,cls=True);resources.load(MOUTH)
        names=tuple(dict.fromkeys(path.rsplit(':',1)[-1] for path in PATHS))
        found=observe(capture_matching,scope.pid,names=names)
        functions=tuple(resources.hold(found.find_path(path)).object for path in PATHS)
        snapshot=observe(describe_selected,scope.pid,tuple(identity(fn) for fn in functions))
        catalog,descriptors=_pod_closure(scope.pid,snapshot)
        with scope.invocation_planner(catalog=catalog,selected_results=True) as planner:
            # Seed the same bounded, identity-checked observation cache used by
            # ordinary planning. The reader already validated this descriptor
            # closure; no extra per-function registry/schema scan is needed.
            planner._metadata.read('struct',catalog,tuple(d.object for d in descriptors.values()),
                lambda catalog,objects:descriptors)
            self.observations=planner.observations()

    def planner(self,scope,obj,path,arguments,*,defer_reads=False):
        from .catalog import capture_selected
        if scope._session is not self.session or path not in self.paths:
            raise ValueError('Performance observations belong to a different session/function')
        objects=tuple(dict.fromkeys((identity(obj),)+tuple(identity(value) for value in arguments.values() if hasattr(value,'class_index'))))
        planner=scope.invocation_planner(observations=self.observations,selected_results=True)
        try:planner.adopt_observations(observe(capture_selected,scope.pid,objects) if defer_reads else capture_selected(scope.pid,objects))
        except BaseException:planner.close();raise
        return planner


def warm(scope,body_assets=()):
    scope._check()
    construction=getattr(scope._session,'_story_construction_resources',None)
    if construction is None:return None
    for path in dict.fromkeys(body_assets):construction.resources.load(path)
    value=getattr(scope._session,'_story_performance_preflight',None)
    if value is None:
        value=PerformancePreflight(scope)
        scope._session._story_performance_preflight=value
    return value
