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
from ..values import read_values_with_references

QA_WORLD='/Game/QA/Map_BattleTesting.Map_BattleTesting'
PROFILES={name.lower():f'/Game/Characters/Heros/Cinematics/BP_Cine_{name}.BP_Cine_{name}_C'
          for name in ('Lune','Sciel','Verso','Maelle','Monoco')}
BASE_PROFILES=('lune','sciel','verso')


def available_profiles(transport):
    """Only advertise new native allowlist entries after a capability handshake."""
    capability=getattr(transport,'timeline_extended_characters_protocol',0)
    return tuple(PROFILES) if type(capability) is int and capability==1 else BASE_PROFILES


def transform(value):
    if type(value) not in (tuple,list) or len(value)!=12 or any(
            type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in value):
        raise ValueError('Finite bounded Blueprint transform required')
    if not .999<=sum(v*v for v in value[:4])<=1.001 or value[7]!=0 or value[11]!=0 or tuple(value[8:11])!=(1,1,1):
        raise ValueError('Normalized unit-scale Blueprint transform required')
    return tuple(value)


class BlueprintActor:
    def __init__(self,parent):
        parent._check()
        capability=getattr(parent._session._transport,'timeline_blueprint_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Timeline Blueprint actor backend required')
        self.scope=SessionScope(parent);self.owner=None;self.state='new';self.profile=None
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

    def prepare(self,profile,pose):
        if self.state!='new':raise RuntimeError('Blueprint construction is never replayed')
        if type(profile) is not str or profile not in PROFILES:raise ValueError('Choose a reviewed cinematic Blueprint')
        if profile not in available_profiles(self.scope._session._transport):
            raise RuntimeError('This cinematic character requires the newer native character runtime')
        pose=transform(pose);self.scope._check();self.state='preparing';self.profile=profile
        try:
            with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                from .controller_anchor import for_scope
                parent=self.scope._parent()
                if parent is None:raise RuntimeError('Blueprint actor parent scope is unavailable')
                anchor=for_scope(parent);context=anchor.context()
                portable=getattr(self.scope._session._transport,'timeline_current_world_protocol',0)
                if context['world_path']!=QA_WORLD and not (type(portable) is int and portable==1):
                    raise ValueError('Blueprint timeline construction requires the QA map or current-world capability')
                cls=load_class(self.scope,PROFILES[profile]).return_value
                if cls is None:raise RuntimeError('Cinematic Blueprint class was not loaded')
                names=('Default__GameplayStatics','BeginDeferredActorSpawnFromClass','FinishSpawningActor','K2_DestroyActor',
                       'K2_GetPawn','SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame','SetMovementMode')
                catalog=capture_matching(self.scope.pid,names=names).with_observations(capture_selected(self.scope.pid,
                    (context['world'][1:],context['controller'][1:],(cls.index,cls.serial,cls.address))))
                pc=catalog.by_index[context['controller'][1]];world=catalog.by_index[context['world'][1]]
                values,catalog=read_values_with_references(catalog,pc,fields=('Pawn',))
                rows=[value for key,value in values.values.items() if key[1]=='Pawn']
                if values.errors or values.truncated or len(rows)!=1 or rows[0] is None:raise RuntimeError('Current exploration pawn required')
                ids=[pc,rows[0],world,catalog.find_path('/Script/Engine.Default__GameplayStatics'),cls]
                ids.extend(catalog.find_path('/Script/Engine.'+path) for path in (
                    'GameplayStatics:BeginDeferredActorSpawnFromClass','GameplayStatics:FinishSpawningActor','Actor:K2_DestroyActor',
                    'Controller:K2_GetPawn','Actor:SetActorEnableCollision','Actor:SetActorTickEnabled','Actor:SetActorHiddenInGame',
                    'CharacterMovementComponent:SetMovementMode'))
                if anchor.context()!=context:raise RuntimeError('World changed before Blueprint construction')
                self.owner.spawn_timeline_prepared(ids,pose)
                current=capture_selected(self.scope.pid,(self.identity,))
                actor=current.by_index[self.identity[0]]
                if actor.class_name!=cls.name:raise RuntimeError('Constructed actor class differs from its Blueprint')
                if anchor.context()!=context:raise RuntimeError('World changed during Blueprint construction')
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

    def move(self,location,yaw):
        """Move only our retained Blueprint instance; never reconstruct it."""
        if self.state!='visible':raise RuntimeError('Visible owned Blueprint actor required')
        if (type(location) not in (tuple,list) or len(location)!=3 or
                any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in location) or
                type(yaw) not in (int,float) or not math.isfinite(yaw)):
            raise ValueError('Finite bounded Blueprint placement required')
        self.scope._check()
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            catalog=capture_matching(self.scope.pid,names=('K2_TeleportTo','Vector','Rotator','Actor'))
            catalog=catalog.with_observations(capture_selected(self.scope.pid,(self.identity,)))
            actor=catalog.by_index[self.identity[0]]
            if actor.class_name!=PROFILES[self.profile].rsplit('.',1)[-1]:
                raise RuntimeError('Owned Blueprint identity changed before placement')
            planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
            call=planner.prepare(actor,catalog.find_path('/Script/Engine.Actor:K2_TeleportTo'),
                DestLocation=dict(zip(('X','Y','Z'),location)),DestRotation=dict(Pitch=0.,Yaw=yaw,Roll=0.))
            self.state='moving'
            try:
                with call.invoke() as result:
                    if result.return_value is not True:raise RuntimeError('Owned Blueprint placement was rejected')
            except BaseException:
                self.state='failed';raise
            self.state='visible'

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
