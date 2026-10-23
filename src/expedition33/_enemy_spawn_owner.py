"""Scope-owned enemy protocol backend; discovery and recipes remain separate.

This internal service owns the native transaction lifecycle. It does not claim
ordinary-map support or turn an unverified assembly into a spawnable recipe.
"""
import secrets
import struct
import threading
from ._enemy_spawn_wire import build_request,exchange,EnemyCleanupDeferred


class EnemySpawnOwner:
    def __init__(self,scope,*,_transport=None):
        scope._check()
        if not isinstance(getattr(scope,'_enemy_spawn_owners',None),list):
            raise RuntimeError('SDK scope does not support enemy ownership')
        transport=scope._session._transport if _transport is None else _transport
        capability=getattr(transport,'enemy_spawn_protocol',0)
        if type(capability) is not int or capability not in (1,2,3):
            raise RuntimeError('Owned enemy capability unavailable')
        if getattr(transport,'_enemy_spawn_owner',None) is not None:
            raise RuntimeError('This SDK session already has an enemy owner')
        self._scope=scope;self._transport=transport;self._thread=threading.get_ident()
        self._owner=secrets.randbits(64) or 1
        self._attempted=False;self._closed=False;self._prepared=False;self._grounded=False
        self._trigger_anchor=False
        self._extra_spots_attempted=False
        self._combat_placement_attempts=set()
        self._component_pose_attempts=set()
        self.phase='ready';self.actor_identity=None;self.arena_identity=None;self.last_response=None
        self.last_operation=None;self.last_error=None
        transport._enemy_spawn_owner=self
        scope._enemy_spawn_owners.append(self)

    @property
    def has_native_work(self):
        return self._attempted

    def _command(self,operation,identities=(),pose=(),policy=0,*,total_count=None,authored_route=None):
        if threading.get_ident()!=self._thread:raise RuntimeError('Enemy owner requires its owning Python thread')
        if self._closed:raise RuntimeError('Enemy owner is closed')
        if self.phase=='cleanup_unknown':raise RuntimeError('Native controller cleanup required; cleanup is not replayed')
        if self._trigger_anchor:
            if operation not in (120,111,118):
                raise RuntimeError('Original trigger anchor permits only hidden staging, arena binding and retirement')
            if operation==118:
                capability=getattr(self._transport,'enemy_trigger_parameter_research_protocol',0)
                if type(capability) is not int or capability!=1:
                    raise RuntimeError('Original trigger parameter research unavailable')
                if not self._prepared or self._grounded or self.actor_identity is None:
                    raise RuntimeError('Owned held trigger required for arena binding')
            if operation==120:
                capability=getattr(self._transport,'enemy_trigger_anchor_research_protocol',0)
                if type(capability) is not int or capability!=1:
                    raise RuntimeError('Original trigger anchor staging research unavailable')
        if operation!=111:self._scope._check()
        request=build_request(self._owner,operation,identities,pose,policy,**({'total_count':total_count} if total_count is not None else {}),**({'authored_route':authored_route} if authored_route is not None else {}))
        capability=self._transport.enemy_spawn_protocol
        if operation==133 and (type(getattr(self._transport,'enemy_authored_encounter_research_protocol',0)) is not int or self._transport.enemy_authored_encounter_research_protocol not in (2,3,4,5,6,7) or (authored_route==2 and self._transport.enemy_authored_encounter_research_protocol<3) or (authored_route>=3 and self._transport.enemy_authored_encounter_research_protocol<4) or (authored_route>=7 and self._transport.enemy_authored_encounter_research_protocol<5) or (authored_route>=8 and self._transport.enemy_authored_encounter_research_protocol<6) or (authored_route>=12 and self._transport.enemy_authored_encounter_research_protocol<7)):
            raise RuntimeError('Authored instance encounter research unavailable')
        if operation==132 and (type(getattr(self._transport,'enemy_geometry_placement_research_protocol',0)) is not int or self._transport.enemy_geometry_placement_research_protocol!=1):
            raise RuntimeError('Original helper geometry placement research unavailable')
        if operation==131 and (type(getattr(self._transport,'enemy_helper_lookup_research_protocol',0)) is not int or self._transport.enemy_helper_lookup_research_protocol!=1):
            raise RuntimeError('Original helper lookup research unavailable')
        if operation==114 and capability<2 or operation==115 and capability<3:
            raise RuntimeError('This owned enemy operation is unavailable')
        if operation==116 and getattr(self._transport,'enemy_pose_protocol',0)!=1:raise RuntimeError('Pawn pose capability unavailable')
        if operation==117 and (type(getattr(self._transport,'enemy_arena_protocol',0)) is not int or getattr(self._transport,'enemy_arena_protocol',0)!=1):raise RuntimeError('Arena observation capability unavailable')
        if operation==118 and (type(getattr(self._transport,'enemy_arena_binding_protocol',0)) is not int or getattr(self._transport,'enemy_arena_binding_protocol',0)!=1):raise RuntimeError('Arena binding capability unavailable')
        if operation==119 and (type(getattr(self._transport,'enemy_clearance_protocol',0)) is not int or getattr(self._transport,'enemy_clearance_protocol',0)!=1):raise RuntimeError('Enemy clearance capability unavailable')
        if operation in (120,121) and (type(getattr(self._transport,'enemy_grounded_spawn_protocol',0)) is not int or getattr(self._transport,'enemy_grounded_spawn_protocol',0)!=2):raise RuntimeError('Grounded enemy spawning capability unavailable')
        if operation==122 and (type(getattr(self._transport,'enemy_extra_spots_protocol',0)) is not int or self._transport.enemy_extra_spots_protocol!=1):raise RuntimeError('Extra battle position capability unavailable')
        if operation==122 and self._extra_spots_attempted:raise RuntimeError('Extra positions were already attempted; no replay')
        if operation==123:
            if type(getattr(self._transport,'enemy_combat_placement_protocol',0)) is not int or self._transport.enemy_combat_placement_protocol!=1:
                raise RuntimeError('Combat placement capability unavailable')
            identity=identities[1]
            placement_key=(identity.index,identity.serial,identity.address)
            if placement_key in self._combat_placement_attempts:raise RuntimeError('Combat position was already attempted; no replay')
        allowed={110:('ready',),112:('spawned',),113:('initialized',),114:('spawned',),115:('spawned',),116:('ready',),117:('ready',),118:('spawned',),119:('ready',),120:('ready',),121:('spawned',),122:('initialized','active'),123:('active',),131:('spawned',),132:('spawned',),133:('ready',)}
        if operation!=111 and self.phase not in allowed[operation]:
            raise RuntimeError('Enemy lifecycle does not allow this operation; no replay')
        if operation==111 and not self._attempted:return None
        if operation==118 and self.arena_identity is not None:raise RuntimeError('Owned enemy arena is already bound; no replay')
        if operation==121 and (not self._prepared or self._grounded):raise RuntimeError('Enemy is not prepared or already placed; no replay')
        if operation==112 and self._prepared and (not self._grounded or self.arena_identity is None):raise RuntimeError('Prepared enemy requires placement and arena binding before initialization')
        previous_phase=self.phase
        self.last_operation=operation;self.phase='dispatching';self.last_error=None
        if operation==122:self._extra_spots_attempted=True
        if operation==123:self._combat_placement_attempts.add(placement_key)
        if operation in (110,120,133):self._attempted=True
        try:response=exchange(self._transport,request)
        except EnemyCleanupDeferred:
            self.phase=previous_phase;self.last_error='EnemyCleanupDeferred';raise
        except BaseException as error:
            self.phase=previous_phase if operation in (116,117,119,131) else ('cleanup_unknown' if operation==111 else 'unknown')
            self.last_error=type(error).__name__;raise
        # Preserve native acknowledgement before any caller readback can fail.
        self.last_response=response
        if operation in (110,112,120,133):self.actor_identity=struct.unpack_from('<iiQ',response,4096)
        if operation in (120,133):self._prepared=True;self._grounded=False
        if operation==121 or operation in (115,132) and self._prepared:self._grounded=True
        if operation==118:
            acknowledged_actor=struct.unpack_from('<iiQ',response,4096)
            if acknowledged_actor!=self.actor_identity:
                self.phase='unknown';self.last_error='ArenaBindingActorMismatch'
                raise RuntimeError('Arena binding acknowledged a different actor; not retried')
            self.arena_identity=struct.unpack_from('<iiQ',response,4112)
        if operation==111:
            self._combat_placement_attempts.clear()
            self._component_pose_attempts.clear()
            self._trigger_anchor=False
            self._attempted=False;self.actor_identity=None;self.arena_identity=None;self._prepared=False;self._grounded=False;self._extra_spots_attempted=False;self.phase='ready'
        else:self.phase=previous_phase if operation in (122,123,131) else {110:'spawned',112:'initialized',113:'active',114:'spawned',115:'spawned',116:'ready',117:'ready',118:'spawned',119:'ready',120:'spawned',121:'spawned',132:'spawned',133:'spawned'}[operation]
        return response

    def prepare_extra_spots(self,prerequisites,total_count):return self._command(122,prerequisites,total_count=total_count)
    def place_combatant(self,prerequisites,destination):return self._command(123,prerequisites,destination)

    def spawn_prepared(self,prerequisites,pose):return self._command(120,prerequisites,pose)
    def spawn_trigger_prepared(self,prerequisites,pose):
        """Stage one original trigger anchor; no entry, pose correction or reveal."""
        capability=getattr(self._transport,'enemy_trigger_anchor_research_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Original trigger anchor staging research unavailable')
        if threading.get_ident()!=self._thread:raise RuntimeError('Enemy owner requires its owning Python thread')
        if self._closed:raise RuntimeError('Enemy owner is closed')
        if self.phase!='ready' or self._attempted:
            raise RuntimeError('Enemy lifecycle does not allow trigger staging; no replay')
        self._scope._check()
        # Preserve this restricted mode even if packet preparation or dispatch
        # fails; only acknowledged native removal clears it.
        self._trigger_anchor=True
        return self._command(120,prerequisites,pose)
    def set_visual_component_pose_once(self,component,setter,getter,pose):
        """Correct one directly owned hidden helper component, preserving scale."""
        if self._trigger_anchor:
            raise RuntimeError('Original trigger anchor permits only hidden staging, arena binding and retirement')
        from ._owned_component_pose import set_helper_pose
        return set_helper_pose(self,component,setter,getter,pose)
    def spawn_visual_prepared(self,prerequisites,pose):
        capability=getattr(self._transport,'enemy_visual_staging_research_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Original visual helper staging research unavailable')
        return self._command(120,prerequisites,pose)
    def place_prepared(self,prerequisites):return self._command(121,prerequisites)
    def inspect_clearance(self,prerequisites,probe):return self._command(119,prerequisites,probe)
    def bind_arena(self,prerequisites):return self._command(118,prerequisites)
    def bind_trigger_arena(self,prerequisites):
        """Bind an owned arena value for this held trigger; grants no entry."""
        if not self._trigger_anchor:raise RuntimeError('Original trigger owner required')
        return self._command(118,prerequisites)
    def bind_visual_arena(self,prerequisites):
        capability=getattr(self._transport,'enemy_visual_arena_research_protocol',0)
        if type(capability) is not int or capability!=2:
            raise RuntimeError('Original helper arena research unavailable')
        if not self._prepared:
            raise RuntimeError('Original helper needs owned prepared staging before arena binding')
        return self._command(118,prerequisites)
    def inspect_arena_assembly(self,prerequisites):return self._command(117,prerequisites)
    def pawn_pose(self,prerequisites):return self._command(116,prerequisites)
    def spawn(self,prerequisites,pose):return self._command(110,prerequisites,pose)
    def initialize(self,component,function,*,policy=0):return self._command(112,(component,function),policy=policy)
    def spawn_authored_prepared(self,prerequisites,pose,*,route):return self._command(133,prerequisites,pose,authored_route=route)
    def activate(self,function):return self._command(113,(function,))
    def configure_visual_tick(self,body):return self._command(114,(body,))
    def lookup_original_helper(self,function):
        response=self._command(131,(function,))
        selected=struct.unpack_from('<iiQ',response,4096)
        if selected!=self.actor_identity:
            raise RuntimeError('Original helper lookup acknowledged a different actor')
        return selected
    def place_visual(self,prerequisites):return self._command(115,prerequisites)
    def place_visual_geometry(self,prerequisites):return self._command(132,prerequisites)
    def remove(self):return self._command(111)

    def close(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Enemy cleanup requires its owning Python thread')
        if self._closed:return True
        try:self.remove() # Allowed after scope revocation, like other native owners.
        except EnemyCleanupDeferred:return False
        self._closed=True;self.phase='closed'
        if getattr(self._transport,'_enemy_spawn_owner',None) is self:self._transport._enemy_spawn_owner=None
        if self in self._scope._enemy_spawn_owners:self._scope._enemy_spawn_owners.remove(self)
        return True
