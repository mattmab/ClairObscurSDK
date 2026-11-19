"""Process-owned construction selectors; every actor remains world scoped."""
from .catalog import capture_matching,capture_selected
from ._reader import shared_operation

PATHS=(
 '/Game/Gameplay/LevelData/DT_LevelData.DT_LevelData',
 '/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary.FL_jRPG_CustomFunctionLibrary_C:ChangeMapByName',
 '/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary.Default__FL_jRPG_CustomFunctionLibrary_C',
 '/Script/Engine.BlueprintMapLibrary:Map_Add',
 '/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom.BP_jRPG_GI_Custom_C:GetPersistentFlagValue',
 '/Game/Gameplay/Exploration/BP_ExplorationProgressionSystem.BP_ExplorationProgressionSystem_C:IsExplorationCapacityUnlocked',
 '/Game/Gameplay/Exploration/BP_ExplorationProgressionSystem.BP_ExplorationProgressionSystem_C:SetExplorationCapacityUnlocked',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:StartDialogLines',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:StartChoice',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:UpdateAllSpeakerActors',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:ActivateCameraComponentByType',
 '/Game/Gameplay/DialogueSystem/BP_Dialogue.BP_Dialogue_C:SetDialogueParameters',
 '/Script/Engine.SceneComponent:K2_SetRelativeTransform','/Script/Engine.SceneComponent:GetRelativeTransform',
 '/Script/Engine.Controller:GetViewTarget','/Script/Engine.PlayerController:SetViewTargetWithBlend',
 '/Script/Engine.Default__GameplayStatics','/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass',
 '/Script/Engine.GameplayStatics:FinishSpawningActor','/Script/Engine.GameplayStatics:SpawnObject',
 '/Script/Engine.Actor:K2_DestroyActor','/Script/Engine.Controller:K2_GetPawn',
 '/Script/Engine.Actor:SetActorEnableCollision','/Script/Engine.Actor:SetActorTickEnabled','/Script/Engine.Actor:SetActorHiddenInGame',
 '/Script/Engine.Actor:SetActorScale3D','/Script/Engine.Actor:K2_GetActorLocation',
 '/Script/Engine.Actor:K2_TeleportTo','/Script/Engine.Actor',
 '/Script/Engine.Actor:K2_GetRootComponent','/Script/Engine.PrimitiveComponent:SetMaterial',
 '/Script/Engine.WorldPartitionStreamingSourceComponent:EnableStreamingSource',
 '/Script/Engine.WorldPartitionStreamingSourceComponent:IsStreamingCompleted',
 '/Script/SandFall.SandfallBlueprintHelpers:BlockTillLevelStreamingCompleted',
 '/Script/SandFall.Default__SandfallBlueprintHelpers',
 '/Script/Engine.DataLayerManager:GetDataLayerInstanceRuntimeState',
 '/Script/Engine.DataLayerManager:SetDataLayerInstanceRuntimeState','/Script/Engine.EDataLayerRuntimeState',
 '/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog.BP_jRPG_NPC_Dialog_C:OnInteractionRequested',
 '/Script/Engine.CharacterMovementComponent:SetMovementMode',
 '/Script/Engine.Default__KismetSystemLibrary','/Script/Engine.KismetSystemLibrary:SetClassPropertyByName',
 '/Script/Engine.KismetSystemLibrary:SetObjectPropertyByName','/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName',
 '/Script/Engine.KismetSystemLibrary:SetTextPropertyByName','/Script/Engine.SceneComponent:SetMobility',
 '/Script/Engine.SceneComponent:SetRelativeScale3D','/Script/Engine.SceneComponent:K2_SetRelativeLocation',
 '/Script/Engine.SkeletalMeshComponent:PlayAnimation','/Script/CoreUObject.Vector','/Script/CoreUObject.Rotator',
 '/Script/Engine.HitResult','/Script/Engine.EComponentMobility','/Script/Engine.AnimationAsset',
 '/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier.BP_InvisibleWall_NavModifier_C:SetInvisibleWallEnabled',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:StartRichDialogueLines',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:EndDialogue',
 '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:IsPlayingSpecificInWorldDialogue',
 '/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager.AC_jRPG_InventoryManager_C:AddItemToInventory',
 '/Script/Engine.Default__KismetTextLibrary','/Script/Engine.KismetTextLibrary:StringTableIdAndKeyFromText',
 '/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage','/Script/Engine.AnimInstance:Montage_Stop','/Script/Engine.AnimInstance:Montage_IsPlaying',
 '/Script/Engine.SkeletalMeshComponent:SetAnimClass','/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',
 '/Script/Engine.ActorComponent:SetComponentTickEnabled','/Script/Engine.ActorComponent:IsComponentTickEnabled',
 '/Game/Gameplay/CharacterCustomization/Blueprints/BP_CharacterSkinComponent.BP_CharacterSkinComponent_C:GetFaceSkeletalMesh',
 '/Game/MetaHumans/Common/Face/Face_AnimBP_HumanNPC.Face_AnimBP_HumanNPC_C:SetPostProcessAnimation',
 '/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C:SetFacialExpression',
 '/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C:SetIsTalking',
 '/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C:SetIsInDialogue',
 '/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C:UpdateEnvelopeVolume')

class StoryConstruction:
    def __init__(self,session,resources,context):
        from .cinematics.blueprint_actor import STORY_NPC,COLLISION_WALL,PORTAL_VISUAL,STREAMING_SOURCE,PROFILES
        from .story_presentation import FACELESS_IDLE
        from .cinematics.controller_anchor import for_scope
        self.session=session;self.resources=resources;self.scope=resources.scope
        self.anchor=for_scope(self.scope)
        classes=(STORY_NPC,COLLISION_WALL,PORTAL_VISUAL,STREAMING_SOURCE,PROFILES['faceless-boy'],
            '/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary.FL_jRPG_CustomFunctionLibrary_C',
            '/Game/Gameplay/DialogueSystem/BP_Dialogue.BP_Dialogue_C',
            '/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter.BP_DataAsset_DialogueCharacter_C',
            '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C',
            '/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager.AC_jRPG_InventoryManager_C')
        for path in classes:resources.load(path,cls=True)
        for path in (FACELESS_IDLE,'/Game/Gameplay/LevelData/DT_LevelData.DT_LevelData',
                '/Game/Gameplay/DialogueSystem/DialogueCharacters/DA_EmptyNameCharacter.DA_EmptyNameCharacter','/Game/Gameplay/DialogueSystem/DialogueCharacters/DA_0_WorldCharacter.DA_0_WorldCharacter'):
            resources.load(path)
        names=tuple(dict.fromkeys(path.rsplit(':',1)[-1].rsplit('.',1)[-1] for path in PATHS))
        c=capture_matching(session.pid,names=names)
        self._metadata_leases=tuple(resources.hold(c.find_path(path)) for path in PATHS)
        self.metadata=tuple(lease.object for lease in self._metadata_leases)
        # Metadata only: targets, collision, root and mobility are observed at
        # each later placement. Do not rediscover these schemas on first E.
        from .reflection import describe_selected
        from .story_performance_preflight import _pod_closure
        movement=tuple(o for o in self.metadata if o.name in (
            'K2_TeleportTo','SetActorEnableCollision','SetMobility','SetActorHiddenInGame',
            'K2_GetActorLocation','K2_GetRootComponent','SetMaterial','SetActorScale3D',
            'SetRelativeScale3D','SetActorTickEnabled','SetInvisibleWallEnabled','SpawnObject',
            'EnableStreamingSource','IsStreamingCompleted','BlockTillLevelStreamingCompleted',
            'GetDataLayerInstanceRuntimeState','SetDataLayerInstanceRuntimeState'))
        snapshot=describe_selected(session.pid,tuple((o.index,o.serial,o.address) for o in movement))
        observed,descriptors=_pod_closure(session.pid,snapshot)
        with self.scope.invocation_planner(catalog=observed,selected_results=True) as planner:
            planner._metadata.read('struct',observed,tuple(d.object for d in descriptors.values()),
                lambda catalog,objects:descriptors)
            # Enum membership is process metadata, not a layer's mutable state.
            # Retain its exact schema alongside the two original functions so
            # first arrival need only discover its current world instances.
            from .enums import describe_enums
            enum=observed.find_path('/Script/Engine.EDataLayerRuntimeState')
            descriptor=planner._metadata.read('enum',observed,(enum,),describe_enums)[enum.index]
            self.layer_values={n:descriptor.value('EDataLayerRuntimeState::'+name)
                for n,name in enumerate(('Unloaded','Loaded','Activated'))}
            self.movement_observations=planner.observations()
        engines=capture_matching(session.pid,classes=('GameEngine',))
        rows=[o for o in engines.objects if o.class_name=='GameEngine' and not o.object_flags&0x30]
        if len(rows)!=1:raise RuntimeError('One process GameEngine required for story identity preparation')
        self.engine=resources.hold(rows[0]).object
        from .values import capture_selected_values
        vc,values=capture_selected_values(session.pid,((self.engine.index,self.engine.serial,self.engine.address),),fields=('GameViewport',),references=True)
        value=values[self.engine.index]
        if value.errors or value.truncated:raise RuntimeError('Process story viewport observation incomplete')
        viewports=[v for k,v in value.values.items() if k[1]=='GameViewport' and v is not None]
        if len(viewports)!=1:raise RuntimeError('One process story viewport required')
        self.viewport=resources.hold(viewports[0]).object
        gi=capture_selected(session.pid,(context.gi[1:],)).by_index[context.gi[1]]
        resources.gi=resources.hold(gi).object
        self._retain_catalog()
    def _retain_catalog(self):
        # Only leased reflection roots may survive across world preparations.
        # CDO/table/runtime observations remain fresh even when their objects
        # are also process-owned. Retain the minimal metadata closure, not the
        # original broad discovery catalog with unrelated recyclable objects.
        roots=[]
        for path,lease in zip(PATHS,self._metadata_leases):
            obj=lease.object
            if obj.class_name=='Function' or (obj.class_name=='ScriptStruct' and path.startswith('/Script/')):
                if obj.serial<=0:raise RuntimeError('Construction metadata requires an active stable lease')
                roots.append((path,lease,obj))
        if not roots:
            self._retained_catalog=None;self._retained_roots={}
            return
        observed=capture_selected(self.scope.pid,tuple((o.index,o.serial,o.address) for _,_,o in roots))
        for path,_,obj in roots:
            current=observed.resolve(obj)
            outer=observed.by_index.get(current.outer_index)
            if (observed.path_name(current)!=path or outer is None or
                    (current.class_name=='Function' and observed.find_class('Class').index not in observed.ancestors(outer.class_index)) or
                    (current.class_name=='ScriptStruct' and (outer.class_name!='Package' or outer.outer_index!=-1))):
                raise RuntimeError('Construction metadata owner or root changed')
        self._retained_catalog=observed.subset(tuple(o for _,_,o in roots))
        self._retained_roots={o.index:(path,lease) for path,lease,o in roots}
    def catalog(self,scope,names):
        """Copied function/POD metadata plus fresh nonmetadata observations.

        A retained catalog is planning data, not proof of current engine state.
        Original invocation dispatch still validates the function and schema.
        """
        retained,fresh=self._catalog_parts(scope,names)
        observed=capture_selected(scope.pid,tuple((o.index,o.serial,o.address) for o in fresh)) if fresh else None
        return self._combine_catalog(retained,fresh,observed)
    def observe(self,scope,names,identities,*,fields):
        """Combine fresh targets/properties and nonmetadata roots in one read.

        Retained functions remain planning metadata; live targets and CDOs are
        always selected again. No property values are retained by this owner.
        """
        from .values import capture_selected_values
        retained,fresh=self._catalog_parts(scope,names)
        identities=tuple(dict.fromkeys((*tuple(identities),*((o.index,o.serial,o.address) for o in fresh))))
        observed,values=capture_selected_values(scope.pid,identities,fields=fields,references=True)
        return self._combine_catalog(retained,fresh,observed),values
    def _catalog_parts(self,scope,names):
        scope._check();self.scope._check()
        if scope._session is not self.session:raise RuntimeError('Construction resources belong to another session')
        selected=tuple(o for o in self.metadata if o.name in names)
        if not selected:raise ValueError('No prepared construction selectors')
        retained=[];fresh=[]
        for obj in selected:
            entry=self._retained_roots.get(obj.index)
            if entry is None:fresh.append(obj);continue
            path,lease=entry
            if not lease.active:raise RuntimeError('Construction metadata lease expired')
            self._retained_catalog.resolve(lease.object)
            retained.append(self._retained_catalog.resolve(obj))
        return retained,fresh
    def _combine_catalog(self,retained,fresh,observed):
        result=self._retained_catalog.subset(retained) if retained else None
        if observed is not None:
            if observed.pid!=self.scope.pid:raise RuntimeError('Construction observation process changed')
            for obj in fresh:observed.resolve(obj)
            result=observed if result is None else result.with_observations(observed)
        # A mixed fresh closure may contain one of the retained owners. Identity
        # merges already reject recycling; also reject a changed ownership chain.
        for obj in retained:
            def provenance(catalog):
                return tuple((o.pid,o.index,o.serial,o.address,o.name,o.class_index,o.outer_index,o.outer_serial)
                    for o in catalog.outer_chain(obj))
            if provenance(result)!=provenance(self._retained_catalog):
                raise RuntimeError('Construction metadata owner or root changed')
        return result
    def context(self,scope):
        ctx=self.anchor.context();token=getattr(scope,'_world_binding_token',None)
        if token is None or token[0]!=ctx['world']:
            from .world_lifecycle import WorldLifecycleError
            raise WorldLifecycleError('Construction World differs from scope admission; waiting for lifecycle handoff')
        return ctx
    def movement_planner(self,scope,catalog):
        scope._check();self.scope._check()
        if scope._session is not self.session:raise RuntimeError('Construction resources belong to another session')
        planner=scope.invocation_planner(observations=self.movement_observations,selected_results=True)
        try:planner.adopt_observations(catalog)
        except BaseException:planner.close();raise
        return planner

def prepare_construction(session,resources,context):
    previous=getattr(session,'_story_construction_resources',None)
    if previous is not None:return previous
    with shared_operation(session.pid):prepared=StoryConstruction(session,resources,context)
    session._story_construction_resources=prepared
    return prepared
