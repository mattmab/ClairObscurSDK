"""Owned original Blueprint construction for authored-timeline cast research.

Uses the Encounter Editor's native deferred construction/retention/retirement
journal. It never initializes an encounter or reconstructs meshes. The initial
backend constructs reviewed actors in the QA map or in a current gameplay world
with the versioned native capability; binding overrides are separate.
"""
import math
from .._scope import SessionScope
from .._enemy_spawn_owner import EnemySpawnOwner
from .._reader import shared_operation
from ..catalog import capture_matching, capture_selected
from ..picto_class_load import load_class
from ..values import read_values_with_references,capture_selected_values

QA_WORLD='/Game/QA/Map_BattleTesting.Map_BattleTesting'
PROFILES={name.lower():f'/Game/Characters/Heros/Cinematics/BP_Cine_{name}.BP_Cine_{name}_C'
          for name in ('Lune','Sciel','Verso','Maelle','Monoco')}
PROFILES['faceless-boy']='/Game/Characters/NPCs/Cinematics/BP_Cine_FacelessBoy.BP_Cine_FacelessBoy_C'
STORY_NPC='/Game/Characters/NPCs/Lumiere/DialogueNPCs/WalkToHarbour/BP_NPC_Dialogue_Empty_FacelessBoyFinale.BP_NPC_Dialogue_Empty_FacelessBoyFinale_C'
COLLISION_WALL='/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier.BP_InvisibleWall_NavModifier_C'
PORTAL_VISUAL='/Game/LevelTools/BP_jRPG_MapTeleportPoint_Interactible.BP_jRPG_MapTeleportPoint_Interactible_C'
STREAMING_SOURCE='/Game/Gameplay/GameplayElement/Content/StreamingSource/BP_WP_StreamingSourceComponent.BP_WP_StreamingSourceComponent_C'
OPERA_PROFILES={
    'gustave':'/Game/Characters/Heros/Cinematics/BP_Cine_Noah.BP_Cine_Noah_C',
    'sophie':'/Game/Characters/Heros/Sophie/BP_JRPG_NPC_Dialog_NPC_Sophie_NoInteraction.BP_JRPG_NPC_Dialog_NPC_Sophie_NoInteraction_C',
    'clea-spirit':'/Game/Characters/NPCs/Spirits/SpiritClea/BP_jRPG_NPC_Dialog_SpiritClea.BP_jRPG_NPC_Dialog_SpiritClea_C',
    'renoir-spirit':'/Game/Characters/NPCs/Spirits/SpiritRenoir/BP_jRPG_NPC_Dialog_RenoirSpirit.BP_jRPG_NPC_Dialog_RenoirSpirit_C',
}
PROFILES.update(OPERA_PROFILES)
BASE_PROFILES=('lune','sciel','verso')
EXTENDED_PROFILES=BASE_PROFILES+('maelle','monoco')


def available_profiles(transport):
    """Only advertise new native allowlist entries after a capability handshake."""
    capability=getattr(transport,'timeline_extended_characters_protocol',0)
    profiles=EXTENDED_PROFILES if type(capability) is int and capability==1 else BASE_PROFILES
    story=getattr(transport,'story_blueprint_characters_protocol',0)
    profiles=profiles+('faceless-boy',) if type(story) is int and story==1 else profiles
    opera=getattr(transport,'opera_story_characters_protocol',0)
    return profiles+tuple(OPERA_PROFILES) if type(opera) is int and opera==1 else profiles


def transform(value):
    if type(value) not in (tuple,list) or len(value)!=12 or any(
            type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in value):
        raise ValueError('Finite bounded Blueprint transform required')
    if not .999<=sum(v*v for v in value[:4])<=1.001 or value[7]!=0 or value[11]!=0 or tuple(value[8:11])!=(1,1,1):
        raise ValueError('Normalized unit-scale Blueprint transform required')
    return tuple(value)


def _construction_context(scope,prepared,expected,catalog,values,*,pawn=False):
    """Validate a fresh combined LocalPlayer/controller/World observation.

    This is a pre/post construction check, not a replacement for the native
    owner's current-world admission at dispatch. Only the LocalPlayer selector
    is retained; the controller link and every requested property are fresh.
    """
    anchor=prepared.anchor
    scope._check();anchor.scope._check()
    if anchor._held.active is not True:raise RuntimeError('Construction LocalPlayer lease is inactive')
    local=catalog.resolve(anchor._held.object)
    if (local.index,local.serial,local.address)!=anchor.identity or local.class_name!='LocalPlayer' or local.object_flags&0x40000030:
        raise RuntimeError('Construction LocalPlayer changed')
    token=getattr(scope,'_world_binding_token',None)
    if token is None or token[0]!=expected['world']:raise RuntimeError('Construction World differs from scope admission')
    def field(obj,name):
        row=values[obj.index];keys=[key for key in row.types if key[1]==name]
        if len(keys)!=1:raise RuntimeError('Construction field missing or ambiguous: '+name)
        key=keys[0]
        if (key[0] not in catalog.ancestors(obj.class_index) or row.types[key]!='ObjectProperty'
                or key in row.errors or key in row.truncated or key not in row.values):
            raise RuntimeError('Construction field is incomplete: '+name)
        return row.values[key]
    pc=field(local,'PlayerController')
    if (pc is None or (scope.pid,pc.index,pc.serial,pc.address)!=expected['controller']
            or pc.object_flags&0x40000030 or catalog.find_class('PlayerController').index not in catalog.ancestors(pc.class_index)):
        raise RuntimeError('Controller changed during Blueprint construction')
    worlds=[o for o in catalog.outer_chain(pc) if o.class_name=='World']
    if (len(worlds)!=1 or (scope.pid,worlds[0].index,worlds[0].serial,worlds[0].address)!=expected['world']
            or catalog.path_name(worlds[0])!=expected['world_path']):
        raise RuntimeError('World changed during Blueprint construction')
    world=worlds[0]
    if world.object_flags&0x40000030:raise RuntimeError('Construction World is retiring')
    current_pawn=None
    if pawn:
        current_pawn=field(pc,'Pawn')
        if current_pawn is None or current_pawn.object_flags&0x40000030:
            raise RuntimeError('Current exploration pawn required')
        pawn_worlds=[o for o in catalog.outer_chain(current_pawn) if o.class_name=='World']
        if len(pawn_worlds)!=1 or pawn_worlds[0]!=world:
            raise RuntimeError('Construction pawn belongs to another World')
    return pc,current_pawn,world


class BlueprintActor:
    def __init__(self,parent):
        parent._check()
        capability=getattr(parent._session._transport,'timeline_blueprint_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Timeline Blueprint actor backend required')
        self.scope=SessionScope(parent);self.owner=None;self.state='new';self.profile=None;self.prepared_actor=None
        try:
            pool=getattr(parent._session._transport,'timeline_actor_pool_protocol',0)
            if type(pool) is not int or pool not in (0,1):raise RuntimeError('Invalid timeline actor pool capability')
            if pool==1:
                from .._timeline_actor_channel import TimelineActorOwner
                self.owner=TimelineActorOwner(self.scope)
            else:self.owner=EnemySpawnOwner(self.scope)
        except BaseException:
            self.scope.close();raise

    @property
    def identity(self):return self.owner.actor_identity

    def prepare(self,profile,pose):return self._prepare(profile,pose)

    def prepare_camera(self,pose):
        if getattr(self.scope._session._transport,'sequence_flight_playback_protocol',0)!=1:
            raise ValueError('Owned viewport camera runtime required')
        return self._prepare('camera',pose,_camera=True)

    def prepare_story_npc(self,pose):
        capability=getattr(self.scope._session._transport,'story_npc_blueprint_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Original story NPC construction requires the newer native runtime')
        return self._prepare('story-npc',pose,_story_npc=True)

    def prepare_collision_wall(self,pose):
        capability=getattr(self.scope._session._transport,'story_collision_wall_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Owned story collision wall runtime required')
        return self._prepare('collision-wall',pose,_wall=True)

    def prepare_portal_visual(self,pose):
        capability=getattr(self.scope._session._transport,'story_collision_wall_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Owned story world element runtime required')
        return self._prepare('portal-visual',pose,_portal=True)

    def prepare_streaming_source(self,pose):
        if getattr(self.scope._session._transport,'story_local_transfer_protocol',0)!=1:raise RuntimeError('Streaming source requires runtime 296')
        return self._prepare('streaming-source',pose,_streaming=True)

    def _prepare(self,profile,pose,*,_camera=False,_story_npc=False,_wall=False,_portal=False,_streaming=False):
        if self.state!='new':raise RuntimeError('Blueprint construction is never replayed')
        if not (_camera or _story_npc or _wall or _portal or _streaming) and (type(profile) is not str or profile not in PROFILES):raise ValueError('Choose a reviewed cinematic Blueprint')
        if not (_camera or _story_npc or _wall or _portal or _streaming) and profile not in available_profiles(self.scope._session._transport):
            raise RuntimeError('This cinematic character requires the newer native character runtime')
        pose=transform(pose);self.scope._check();self.state='preparing';self.profile=profile
        self.class_path='/Script/Engine.CameraActor' if _camera else STORY_NPC if _story_npc else COLLISION_WALL if _wall else PORTAL_VISUAL if _portal else STREAMING_SOURCE if _streaming else PROFILES[profile]
        try:
            with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                from .controller_anchor import for_scope
                parent=self.scope._parent()
                if parent is None:raise RuntimeError('Blueprint actor parent scope is unavailable')
                prepared=getattr(self.scope._session,'_story_construction_resources',None)
                anchor=for_scope(parent) if prepared is None else None
                observe_context=(lambda:anchor.context()) if prepared is None else (lambda:prepared.context(self.scope))
                context=observe_context()
                portable=getattr(self.scope._session._transport,'timeline_current_world_protocol',0)
                if context['world_path']!=QA_WORLD and not (type(portable) is int and portable==1):
                    raise ValueError('Blueprint timeline construction requires the QA map or current-world capability')
                media=getattr(self.scope._session,'_file_audio_metadata',None)
                cls=((media.catalog(self.scope,('/Script/Engine.CameraActor',)) if media is not None else
                     capture_matching(self.scope.pid,names=('CameraActor',))).find_path('/Script/Engine.CameraActor')
                     if _camera else prepared.resources.load(self.class_path,cls=True) if prepared is not None else load_class(self.scope,self.class_path).return_value)
                if cls is None:raise RuntimeError('Cinematic Blueprint class was not loaded')
                names=('Default__GameplayStatics','BeginDeferredActorSpawnFromClass','FinishSpawningActor','K2_DestroyActor',
                       'K2_GetPawn','SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame','SetMovementMode')
                identities=(context['world'][1:],context['controller'][1:],(cls.index,cls.serial,cls.address))
                if prepared is not None:
                    # CDO/current controller/Pawn and LocalPlayer's current
                    # controller link share the same pre-dispatch observation.
                    catalog,values=prepared.observe(self.scope,names,(prepared.anchor.identity,*identities),
                        fields=('PlayerController','Pawn'))
                    pc,current_pawn,world=_construction_context(self.scope,prepared,context,catalog,values,pawn=True)
                    cls=catalog.resolve(cls)
                else:
                    catalog=capture_matching(self.scope.pid,names=names).with_observations(capture_selected(self.scope.pid,identities))
                    pc=catalog.by_index[context['controller'][1]];world=catalog.by_index[context['world'][1]]
                    values,catalog=read_values_with_references(catalog,pc,fields=('Pawn',))
                    rows=[value for key,value in values.values.items() if key[1]=='Pawn']
                    if values.errors or values.truncated or len(rows)!=1 or rows[0] is None:raise RuntimeError('Current exploration pawn required')
                    current_pawn=rows[0]
                ids=[pc,current_pawn,world,catalog.find_path('/Script/Engine.Default__GameplayStatics'),cls]
                ids.extend(catalog.find_path('/Script/Engine.'+path) for path in (
                    'GameplayStatics:BeginDeferredActorSpawnFromClass','GameplayStatics:FinishSpawningActor','Actor:K2_DestroyActor',
                    'Controller:K2_GetPawn','Actor:SetActorEnableCollision','Actor:SetActorTickEnabled','Actor:SetActorHiddenInGame',
                    'CharacterMovementComponent:SetMovementMode'))
                if prepared is None and observe_context()!=context:raise RuntimeError('World changed before Blueprint construction')
                self.owner.spawn_timeline_prepared(ids,pose)
                if prepared is not None:
                    current,values=capture_selected_values(self.scope.pid,
                        (prepared.anchor.identity,context['controller'][1:],context['world'][1:],self.identity),
                        fields=('PlayerController',),references=True)
                    _construction_context(self.scope,prepared,context,current,values)
                else:current=capture_selected(self.scope.pid,(self.identity,))
                actor=current.by_index[self.identity[0]]
                if actor.class_index!=cls.index or actor.class_name!=cls.name:raise RuntimeError('Constructed actor class differs from its Blueprint')
                if prepared is not None:
                    worlds=[o for o in current.outer_chain(actor) if o.class_name=='World']
                    if len(worlds)!=1 or (self.scope.pid,worlds[0].index,worlds[0].serial,worlds[0].address)!=context['world']:
                        raise RuntimeError('Constructed actor belongs to another World')
                elif observe_context()!=context:raise RuntimeError('World changed during Blueprint construction')
                # This copied result is for immediate owner-to-adapter handoff;
                # subsequent configuration still revalidates in the native owner.
                self.prepared_actor=actor
            self.state='prepared';return self.identity
        except BaseException:
            self.state='failed';raise

    def reveal(self):
        if self.state!='prepared':raise RuntimeError('Prepared Blueprint actor required; reveal is never replayed')
        self.state='revealing'
        try:self.owner.reveal_timeline()
        except BaseException:
            self.state='failed';raise
        self.state='visible';return self.identity

    def move(self,location,yaw,*,placement=False):
        """Move only our retained Blueprint instance; never reconstruct it."""
        if type(placement) is not bool:raise ValueError('Placement mode must be boolean')
        if self.state not in ('prepared','visible'):raise RuntimeError('Prepared or visible owned Blueprint actor required')
        previous_state=self.state
        if (type(location) not in (tuple,list) or len(location)!=3 or
                any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in location) or
                type(yaw) not in (int,float) or not math.isfinite(yaw)):
            raise ValueError('Finite bounded Blueprint placement required')
        self.scope._check()
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            names=('K2_TeleportTo','SetActorEnableCollision','SetMobility','EComponentMobility','Vector','Rotator','Actor')
            prepared=getattr(self.scope._session,'_story_construction_resources',None)
            catalog=(prepared.catalog(self.scope,names) if prepared is not None
                else capture_matching(self.scope.pid,names=names))
            catalog=catalog.with_observations(capture_selected(self.scope.pid,(self.identity,)))
            actor=catalog.by_index[self.identity[0]]
            if actor.class_name!=getattr(self,'class_path',PROFILES.get(self.profile,'')).rsplit('.',1)[-1]:
                raise RuntimeError('Owned Blueprint identity changed before placement')
            collision=None
            if placement:
                values,catalog=read_values_with_references(catalog,actor,fields=('bActorEnableCollision','RootComponent'))
                rows=[value for key,value in values.values.items() if key[1]=='bActorEnableCollision']
                if values.errors or len(rows)!=1 or type(rows[0]) is not bool:raise RuntimeError('Actor collision state is unavailable')
                collision=rows[0]
                roots=[value for key,value in values.values.items() if key[1]=='RootComponent']
                if len(roots)!=1 or roots[0] is None:raise RuntimeError('Actor placement root is unavailable')
                component=roots[0]
                values,catalog=read_values_with_references(catalog,component,fields=('Mobility',))
                rows=[value for key,value in values.values.items() if key[1]=='Mobility']
                if values.errors or len(rows)!=1 or rows[0] not in (0,1,2):raise RuntimeError('Actor mobility is unavailable')
                mobility=rows[0]
            planner=(prepared.movement_planner(self.scope,catalog) if prepared is not None
                else self.scope.invocation_planner(catalog=catalog,selected_results=True))
            call=planner.prepare(actor,catalog.find_path('/Script/Engine.Actor:K2_TeleportTo'),
                DestLocation=dict(zip(('X','Y','Z'),location)),DestRotation=dict(Pitch=0.,Yaw=yaw,Roll=0.))
            change_collision=collision is True
            change_mobility=collision is not None and mobility!=2
            if change_collision:
                collision_fn=catalog.find_path('/Script/Engine.Actor:SetActorEnableCollision')
                disable=planner.prepare(actor,collision_fn,bNewActorEnableCollision=False)
                restore=planner.prepare(actor,collision_fn,bNewActorEnableCollision=collision)
            if change_mobility:
                mobility_fn=catalog.find_path('/Script/Engine.SceneComponent:SetMobility')
                movable=planner.prepare(component,mobility_fn,NewMobility=2)
                restore_mobility=planner.prepare(component,mobility_fn,NewMobility=mobility)
            self.state='moving'
            try:
                if change_collision:
                    with disable.invoke():pass
                try:
                    if change_mobility:
                        with movable.invoke():pass
                    with call.invoke() as result:
                        if result.return_value is not True:raise RuntimeError('Owned Blueprint placement was rejected')
                finally:
                    try:
                        if change_mobility:
                            with restore_mobility.invoke():pass
                    finally:
                        if change_collision:
                            with restore.invoke():pass
            except BaseException:
                self.state='failed';raise
            finally:planner.close()
            self.state=previous_state

    def close(self):
        if self.state=='closed':return True
        if not self.owner.close():return False
        self.scope.close();self.state='closed';return True

    def retire_world(self):
        """Retire only this native-owned actor and its collector leases."""
        if self.state=='closed':return True
        if not self.owner.close():return False
        from .._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope):return False
        self.state='closed';return True
