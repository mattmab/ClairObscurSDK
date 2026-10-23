"""Exact original NPC profiles through shared SDK construction primitives."""
import math
from ._scope import SessionScope
from .picto_class_load import load_class
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references
from .cinematics.original_game_action import controller_context
CLASS='/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract.BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C'
ARENA_CLASS='/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C'
SOURCE='/Game/Levels/CleaFlyingHouse/GameActions/DA_GA_SQT_BossClea.DA_GA_SQT_BossClea:BP_GameAction_TriggerBattle_C_0'

ALICIA_CLASS='/Game/Characters/Enemies/HumanEnnemies/Alicia/BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract.BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract_C'
ALICIA_SOURCE='/Game/Levels/Reacher/GameActions/DA_GA_SQT_BossReacher.DA_GA_SQT_BossReacher:BP_GameAction_TriggerBattle_C_1'
CURATOR_CLASS='/Game/Characters/Heros/Camps/BP_Character_Camp_Curator.BP_Character_Camp_Curator_C'
CURATOR_SOURCE='/Game/Levels/Lumiere/GameActions/ACT03/DA_GA_SQT_BossRenoir.DA_GA_SQT_BossRenoir:BP_GameAction_TriggerBattle_C_0'
FRANCOIS_CLASS='/Game/Characters/Enemies/Esquies_Nest/Francois/BP_NPC_FrancoisTheTurtle.BP_NPC_FrancoisTheTurtle_C'
FRANCOIS_SOURCE='/Game/Levels/EsquieNest/GameActions/DA_GA_SQT_Francois.DA_GA_SQT_Francois:BP_GameAction_TriggerBattle_C_0'

def original_profile(route):
    if route=='clea-normal':return CLASS,SOURCE
    if route=='alicia-reacher':return ALICIA_CLASS,ALICIA_SOURCE
    if route=='curator-lumiere':return CURATOR_CLASS,CURATOR_SOURCE
    if route=='francois-esquienest':return FRANCOIS_CLASS,FRANCOIS_SOURCE
    raise ValueError('No original NPC encounter profile for this identity')


def grounding_queries(scope):
    from expedition33._reader import ReadBatch
    from expedition33.catalog import capture_matching,capture_selected
    from expedition33.values import read_values_with_references
    from expedition33.cinematics.original_game_action import controller_context
    context=controller_context(scope._session)
    paths=('KismetSystemLibrary:LineTraceSingle','GameplayStatics:BreakHitResult','KismetSystemLibrary:GetComponentBounds',
           'Actor:K2_GetActorLocation','Actor:K2_GetActorRotation','Actor:K2_SetActorLocationAndRotation','KismetSystemLibrary:BoxTraceSingle','Controller:K2_GetPawn')
    with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
        c=capture_matching(scope.pid,names=('Default__KismetSystemLibrary',)+tuple(path.split(':')[1] for path in paths))
        c=c.with_observations(capture_selected(scope.pid,(context['controller'][1:],)))
        values,c=read_values_with_references(c,c.by_index[context['controller'][1]],fields=('Pawn',))
        if values.errors:raise RuntimeError('Current pawn read failed')
        pawn=next(v for k,v in values.values.items() if k[1]=='Pawn')
        if pawn is None:raise RuntimeError('Exploration pawn required for placement')
        def exact(path):
            matches=[o for o in c.objects if c.path_name(o)=='/Script/Engine.'+path]
            if len(matches)!=1:raise RuntimeError('Missing/ambiguous exact placement source: '+path)
            return matches[0]
        ids=[pawn,exact('Default__KismetSystemLibrary')]+[exact(path) for path in paths]
        if controller_context(scope._session)!=context:raise RuntimeError('Travel during placement preparation')
    return ids

def prepare_original(scope,owner,*,route='clea-normal'):
    CLASS,_=original_profile(route)
    child=SessionScope(scope)
    try:
        retained=load_class(child,CLASS);cls=retained.return_value
        context=controller_context(scope._session)
        names=('Default__GameplayStatics','Default__'+CLASS.rsplit('.',1)[1],
               'IsInteractionAvailable','BeginDeferredActorSpawnFromClass','FinishSpawningActor','K2_DestroyActor',
               'SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame','SetMovementMode',
               'UnregisterInteractiveObject','UnregisterDistantInteractiveObject','BP_ConditionCheckerComponent_GEN_VARIABLE')
        with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
            c=capture_matching(scope.pid,names=names,classes=('BP_InteractionSystem_C',))
            c=c.with_observations(capture_selected(scope.pid,(context['controller'][1:],context['world'][1:])))
            def exact(path):
                matches=[o for o in c.objects if c.path_name(o)==path]
                if len(matches)!=1:raise RuntimeError('Exact original prerequisite missing/ambiguous: '+path)
                return matches[0]
            def fields(obj,names):
                nonlocal c
                values,c=read_values_with_references(c,obj,fields=names)
                if values.errors:raise RuntimeError('Original NPC prerequisite read failed: '+str(values.errors))
                return {key[1]:value for key,value in values.values.items()}
            pc=c.by_index[context['controller'][1]];world=c.by_index[context['world'][1]]
            pawn=fields(pc,('Pawn',))['Pawn']
            if pawn is None:raise RuntimeError('Normal gameplay pawn required before staging')
            root=fields(pawn,('RootComponent',))['RootComponent']
            values=fields(root,('AttachParent','RelativeLocation','RelativeRotation'))
            if values['AttachParent'] is not None:raise RuntimeError('First hidden test requires an unattached exploration pawn')
            location=values['RelativeLocation'];rotation=values['RelativeRotation']
            if location.errors or location.truncated or rotation.errors or rotation.truncated:raise RuntimeError('Complete pawn-root pose required')
            xyz=location.fields;yaw=math.radians(rotation.fields['Yaw'])
            pose=(0,0,math.sin(yaw/2),math.cos(yaw/2),xyz['X']+1600*math.cos(yaw)-500*math.sin(yaw),
                  xyz['Y']+1600*math.sin(yaw)+500*math.cos(yaw),xyz['Z']+150,0,1,1,1,0)
            systems=[o for o in c.objects if o.class_name=='BP_InteractionSystem_C' and o.outer_index==pc.index and not o.object_flags&0x30]
            if len(systems)!=1:raise RuntimeError('Current interaction system not uniquely observed')
            gi=fields(world,('OwningGameInstance',))['OwningGameInstance']
            engine=lambda path:exact('/Script/Engine.'+path)
            availability=('/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog.BP_jRPG_NPC_Dialog_C:IsInteractionAvailable'
                if route in ('curator-lumiere','francois-esquienest') else CLASS+':IsInteractionAvailable')
            ids=[pc,world,engine('Default__GameplayStatics'),cls,
                 exact(CLASS.rsplit('.',1)[0]+'.Default__'+CLASS.rsplit('.',1)[1]),exact(availability),
                 engine('GameplayStatics:BeginDeferredActorSpawnFromClass'),engine('GameplayStatics:FinishSpawningActor'),
                 engine('Actor:K2_DestroyActor'),engine('Actor:SetActorEnableCollision'),engine('Actor:SetActorTickEnabled'),
                 engine('Actor:SetActorHiddenInGame'),engine('CharacterMovementComponent:SetMovementMode'),systems[0],
                 exact('/Game/Gameplay/Exploration/BP_InteractionSystem.BP_InteractionSystem_C:UnregisterInteractiveObject'),
                 exact('/Game/Gameplay/Exploration/BP_InteractionSystem.BP_InteractionSystem_C:UnregisterDistantInteractiveObject'),gi,
                 exact('/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog.BP_jRPG_NPC_Dialog_C:BP_ConditionCheckerComponent_GEN_VARIABLE')]
            if controller_context(scope._session)!=context:raise RuntimeError('Context changed before hidden preparation')
        queries=grounding_queries(scope)
        return owner.stage(ids,pose,queries),queries
    finally:
        child.close()

def bind_original_arena(scope,owner,arena_identity,*,expected_class=ARENA_CLASS):
    from ._enemy_arenas import observe_battle_arenas
    if expected_class not in (ARENA_CLASS, '/Game/Levels/Battle_Maps/BattleMap_SpecialEnemies/BP_BattleMap_DuollistAlpha.BP_BattleMap_DuollistAlpha_C', '/Game/Characters/Enemies/YellowForest/Boss_Scavenger/BP_BattleMap_Scavenger.BP_BattleMap_Scavenger_C'):
        raise ValueError('Unsupported exact original arena class')
    observed=observe_battle_arenas(scope._session)
    matches=[a for a in observed['arenas'] if tuple(a['identity'])==tuple(arena_identity) and a['class_path']==expected_class]
    if len(matches)!=1:raise ValueError('Select one observed standard arena in the current world')
    with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
        c=capture_matching(scope.pid,names=('Default__KismetSystemLibrary','Conv_ObjectToSoftObjectReference','Conv_SoftObjectReferenceToObject'))
        c=c.with_observations(capture_selected(scope.pid,(tuple(arena_identity),)))
        def exact(path):
            found=[o for o in c.objects if c.path_name(o)=='/Script/Engine.'+path]
            if len(found)!=1:raise RuntimeError('Arena conversion source unavailable: '+path)
            return found[0]
        identities=(c.by_index[arena_identity[0]],exact('Default__KismetSystemLibrary'),
            exact('KismetSystemLibrary:Conv_ObjectToSoftObjectReference'),exact('KismetSystemLibrary:Conv_SoftObjectReferenceToObject'))
    return owner.bind_arena(identities)

def _controller_battle_manager(c,controller):
    """Use the controller's actual reference after authored manager replacement."""
    values,c=read_values_with_references(c,controller,fields=('AC_jRPG_BattleManager',))
    if values.errors:raise RuntimeError('Current battle manager reference read failed')
    matches=[v for k,v in values.values.items() if k[1]=='AC_jRPG_BattleManager']
    if len(matches)!=1 or matches[0] is None:raise RuntimeError('Current controller has no battle manager')
    manager=matches[0]
    expected='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C'
    if manager.outer_index!=controller.index or manager.object_flags&0x40018030 or c.path_name(c.by_index[manager.class_index])!=expected:
        raise RuntimeError('Current controller battle manager identity rejected')
    return manager,c


def prepare_dispatch(scope,owner,*,route='clea-normal'):
    """Retain the original source before arming approach; never enter combat here."""
    from .assets import load_asset
    from .original_trigger_sources import _owned_source,BATTLE_STRUCT
    class_path,SOURCE=original_profile(route)
    root=load_asset(scope,SOURCE.split(':',1)[0]).return_value
    status=owner.status()
    if status['native_error'] or not status['has_work']:raise RuntimeError('Exact NPC owner is not prepared')
    context=controller_context(scope._session)
    with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
        c=capture_matching(scope.pid,classes=('BP_GameAction_TriggerBattle_C','AC_jRPG_BattleManager_C'),names=('FBattleStartParams','StartBattleNEW'))
        c=c.with_observations(capture_selected(scope.pid,((root.index,root.serial,root.address),tuple(status['actor_identity']),tuple(context['controller'][1:]))))
        source=_owned_source(c,root,SOURCE)
        structures=[o for o in c.objects if c.path_name(o)==BATTLE_STRUCT]
        manager,c=_controller_battle_manager(c,c.by_index[context['controller'][1]])
        functions=[o for o in c.objects if c.path_name(o)=='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:StartBattleNEW']
        if any(len(x)!=1 for x in (structures,functions)):raise RuntimeError('Exact original battle entry context missing or ambiguous')
        anchor=c.by_index[status['actor_identity'][0]]
        if [anchor.index,anchor.serial,anchor.address]!=status['actor_identity']:raise RuntimeError('NPC identity changed')
        if c.path_name(c.by_index[anchor.class_index])!=class_path:raise RuntimeError('NPC class does not match the selected original encounter profile')
        identities=(structures[0],source,root,anchor,manager,functions[0])
    return identities


def dispatch_original(scope,owner,prepared=None):
    from ._battle_parameter_owner import ParameterResearchOwner
    child=SessionScope(scope)
    try:
        identities=prepared if prepared is not None else prepare_dispatch(child,owner)
        # The native entry still validates current world, manager, source, actor
        # serials and arena ownership before any dispatch. Cached identities
        # are observations, not authority; travel fails closed.
        parameters=ParameterResearchOwner(child)
        parameters.match(identities[:3])
        return parameters.entry_arena_cleanup(identities,mode=1,anchor_owner=owner.token,dispatch=True,arena_policy=1)
    finally:
        child.close()

def interaction_queries(scope):
    names=('SetCollisionEnabled','GetCollisionEnabled','SetCollisionResponseToChannel','GetCollisionResponseToChannel','K2_SphereOverlapComponent')
    with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
        c=capture_matching(scope.pid,names=names)
        identities=[]
        for name in names:
            found=[o for o in c.objects if c.path_name(o)=='/Script/Engine.PrimitiveComponent:'+name]
            if len(found)!=1:raise RuntimeError('Exact interaction function unavailable: '+name)
            identities.append(found[0])
    return tuple(identities)
