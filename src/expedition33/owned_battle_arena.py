"""Scoped inert battle arenas, reusing the SDK owned-actor transaction backend.

No enemy/scene/map mod imports, movement, encounter entry or camera activation.
Preparation requires the existing13 observed inputs and unit-scale spawn pose.
"""
import struct
import math
import threading
from ._enemy_spawn_owner import EnemySpawnOwner
from ._enemy_spawn_wire import SIZE,validate_request as validate_actor

PREPARE=151
RETIRE=152
STATUS=153
COMPONENT_POSE=154
GROUND=155
QUALIFY_HELPER=156
CHANNEL={PREPARE:120,RETIRE:111,STATUS:111}

def _rigid(pose):
    return (len(pose)==12 and all(math.isfinite(v) and abs(v)<=100000 for v in pose)
        and abs(sum(v*v for v in pose[:4])-1)<=1e-6 and pose[7]==pose[11]==0
        and all(abs(v-1)<=1e-6 for v in pose[8:11]))

def _same_pose(a,b):
    return (_rigid(a) and _rigid(b) and abs(abs(sum(x*y for x,y in zip(a[:4],b[:4])))-1)<=1e-6
        and all(abs(a[i]-b[i])<=.001 for i in range(4,7)))

def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Exact arena staging packet required')
    operation=struct.unpack_from('<I',packet,4)[0]
    if operation==GROUND:
        version,_,error,state,owner=struct.unpack_from('<4IQ',packet)
        if version!=3 or error or state or not owner:raise ValueError('Invalid arena ground header')
        for offset in range(88,232,16):
            index,serial,address=struct.unpack_from('<iiQ',packet,offset)
            if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address%8:raise ValueError('Invalid arena ground identity')
        if packet[24] not in (0,1,3,7) or any(packet[25:88]+packet[232:]):raise ValueError('Reserved arena grounding data')
        return
    if operation in (COMPONENT_POSE,QUALIFY_HELPER):
        version,_,error,state,owner=struct.unpack_from('<4IQ',packet)
        if version!=3 or error or state or not owner:raise ValueError('Invalid component pose header')
        end=152 if operation==QUALIFY_HELPER else 136
        for offset in range(88,end,16):
            index,serial,address=struct.unpack_from('<iiQ',packet,offset)
            if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address%8:
                raise ValueError('Invalid component pose identity')
        helper_pose=operation==COMPONENT_POSE and packet[24]==1
        from ._owned_component_pose import scaled
        if not (scaled if helper_pose else _rigid)(struct.unpack_from('<12d',packet,2000)):raise ValueError('Valid component pose required')
        if operation==QUALIFY_HELPER and any(abs(v)>1e-6 for v in struct.unpack_from('<2d',packet,2000)):
            raise ValueError('Source frame requires upright yaw')
        if any(packet[25 if helper_pose else 24:88]+packet[end:2000]+packet[2096:]):raise ValueError('Reserved component pose data')
        return
    if operation not in CHANNEL:raise ValueError('Unsupported arena operation')
    canonical=bytearray(packet);struct.pack_into('<I',canonical,4,CHANNEL[operation])
    validate_actor(bytes(canonical))
    if operation==PREPARE:
        for i in range(13):
            if struct.unpack_from('<Q',packet,96+16*i)[0]%8:raise ValueError('Unaligned arena prerequisite')

class _ArenaTransport:
    """Channel adapter only: canonical construction/cleanup and replies reused."""
    def __init__(self,transport):self._real=transport;self._enemy_spawn_owner=None
    def __getattr__(self,name):return getattr(self._real,name)
    def command(self,command,packet):
        if command!='mesh':raise ValueError('Arena channel accepts only its owned transaction')
        validate_actor(packet)
        operation=struct.unpack_from('<I',packet,4)[0]
        mapped={120:PREPARE,111:RETIRE}.get(operation)
        if mapped is None:raise ValueError('Arena channel cannot execute another enemy operation')
        wire=bytearray(packet);struct.pack_into('<I',wire,4,mapped);validate_request(bytes(wire))
        reply=self._real.command('mesh',bytes(wire))
        raw=bytes.fromhex(reply['mesh_packet'])
        if len(raw)!=SIZE or struct.unpack_from('<I',raw,4)[0]!=mapped:
            raise RuntimeError('Arena channel acknowledgement differs; preserve owner')
        raw=bytearray(raw);struct.pack_into('<I',raw,4,operation)
        return dict(reply,mesh_packet=bytes(raw).hex())

class OwnedBattleArena:
    def __init__(self,scope,*,companion_of=None):
        scope._check();transport=scope._session._transport
        cap=getattr(transport,'owned_battle_arena_staging_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Owned battle arena capability unavailable')
        primary=getattr(transport,'_owned_battle_arena_owner',None)
        if companion_of is None:
            if primary is not None:raise RuntimeError('Battle arena already owned')
        else:
            capacity=getattr(transport,'owned_battle_arena_capacity',1)
            if type(capacity) is not int or capacity!=2:raise RuntimeError('Companion battle arena capability unavailable')
            if not isinstance(companion_of,OwnedBattleArena) or primary is not companion_of:
                raise RuntimeError('Companion requires the current primary arena')
            if (companion_of._scope is not scope or companion_of._transport is not transport or
                companion_of._closed or companion_of.phase!='spawned' or companion_of._component_uncertain or
                companion_of._companion is not None):
                raise RuntimeError('Companion requires a prepared primary arena in this scope')
        self._scope=scope;self._transport=transport;self._closed=False
        self._parent=companion_of;self._companion=None
        self._component_attempts=set();self._component_uncertain=False
        self._camera_focus_attempted=False;self.camera_focus=None
        self._ground_attempted=False;self.grounding=None
        self._helper_attempted=False
        self._owner=EnemySpawnOwner(scope,_transport=_ArenaTransport(transport))
        scope._register_native_owner(self)
        # Only the wrapper may retire this backend: raw enemy cleanup would
        # bypass companion-before-primary ordering after a deferred/unknown close.
        scope._enemy_spawn_owners.remove(self._owner)
        if companion_of is None:transport._owned_battle_arena_owner=self
        else:companion_of._companion=self
    @property
    def actor_identity(self):return self._owner.actor_identity
    @property
    def phase(self):return self._owner.phase
    def prepare(self,identities,pose):
        self._scope._check()
        if self._closed:raise RuntimeError('Arena owner closed')
        self._owner.spawn_visual_prepared(tuple(identities),tuple(pose))
        return self.status()
    def prepare_original(self,class_path,pose):
        """Retain/validate an original arena class and construct its inert instance.

        The caller supplies an explicit absolute unit-scale transform. This is
        preparation only: terrain placement and battle entry are separate gates.
        """
        from .picto_class_load import load_class
        from ._reader import ReadBatch
        from .catalog import capture_matching,capture_selected
        from .values import read_values_with_references
        from .cinematics.original_game_action import controller_context
        self._scope._check()
        if self._closed or self.phase!='ready':raise RuntimeError('Arena preparation cannot be replayed')
        cls=load_class(self._scope,class_path).return_value
        if cls is None:raise RuntimeError('Original arena class did not load')
        context=controller_context(self._scope._session)
        paths=('GameplayStatics:BeginDeferredActorSpawnFromClass','GameplayStatics:FinishSpawningActor',
            'Actor:K2_DestroyActor','Controller:K2_GetPawn','Actor:SetActorEnableCollision',
            'Actor:SetActorTickEnabled','Actor:SetActorHiddenInGame')
        with ReadBatch(self._scope.pid,share=True,_executable=self._transport._executable):
            c=capture_matching(self._scope.pid,names=('Default__GameplayStatics',)+tuple(p.split(':')[1] for p in paths))
            c=c.with_observations(capture_selected(self._scope.pid,(context['controller'][1:],context['world'][1:],(cls.index,cls.serial,cls.address))))
            if '/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C' not in {c.path_name(c.by_index[i]) for i in c.ancestors(cls.index)}:
                raise ValueError('Original class is not a battle arena')
            pc=c.by_index[context['controller'][1]]
            values,c=read_values_with_references(c,pc,fields=('Pawn',))
            if values.errors:raise RuntimeError('Current pawn unavailable')
            pawn=next(iter(values.values.values()))
            if pawn is None:raise RuntimeError('Exploration pawn required before arena staging')
            def exact(path):
                rows=[o for o in c.objects if c.path_name(o)=='/Script/Engine.'+path]
                if len(rows)!=1:raise RuntimeError('Exact arena construction prerequisite unavailable: '+path)
                return rows[0]
            ids=[pc,pawn,c.by_index[context['world'][1]],exact('Default__GameplayStatics'),cls]
            ids.extend(exact(path) for path in paths)
            # The existing visual-construction ABI has13 slots; its final
            # Character movement slot is unused for an Actor arena. Bind it to
            # an already observed destructor rather than load Character APIs.
            ids.append(exact('Actor:K2_DestroyActor'))
            if controller_context(self._scope._session)!=context:raise RuntimeError('Travel during arena input preparation')
        return self.prepare(ids,pose)
    def status(self):
        self._scope._check()
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,STATUS,0,0,self._owner._owner)
        validate_request(bytes(packet))
        reply=self._transport.command('mesh',bytes(packet));raw=bytes.fromhex(reply['mesh_packet'])
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:24]!=packet[16:24]:
            raise RuntimeError('Arena status acknowledgement differs; preserve owner')
        error,state=struct.unpack_from('<II',raw,8)
        expected=bytearray(packet);struct.pack_into('<II',expected,8,error,state)
        expected[4096:4112]=raw[4096:4112]
        if raw!=bytes(expected) or error or state not in (1,2):raise RuntimeError('Arena status rejected; preserve owner')
        actor=struct.unpack_from('<iiQ',raw,4096)
        if state==1 and any(actor):raise RuntimeError('Idle arena status retains an actor')
        if any(actor) and (actor[0]<0 or actor[1]<0 or not 0x10000<=actor[2]<=0x7fffffffffff or actor[2]%8):
            raise RuntimeError('Arena status actor identity invalid')
        return dict(has_native_work=state==2,actor_identity=actor if any(actor) else None,phase=self.phase)
    def set_component_pose_once(self,component,setter,getter,pose):
        """Restore one observed original local pose on this inert owned arena.

        Engine profiles and direct attachment ownership are checked natively.
        Root motion, scaling and writes to original map actors are rejected.
        Destruction of the owned arena is the rollback boundary.
        """
        self._scope._check()
        if threading.get_ident()!=self._owner._thread:raise RuntimeError('Arena requires its owning Python thread')
        cap=getattr(self._transport,'owned_component_pose_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Owned component pose capability unavailable')
        if self._closed or self.phase!='spawned' or self._component_uncertain or self._ground_attempted or self._camera_focus_attempted:
            raise RuntimeError('Arena component mutation unavailable; preserve owner for cleanup')
        key=(component.index,component.serial,component.address)
        if key in self._component_attempts:raise RuntimeError('Component pose was already attempted; no replay')
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,COMPONENT_POSE,0,0,self._owner._owner)
        for i,identity in enumerate((component,setter,getter)):
            struct.pack_into('<iiQ',packet,88+16*i,identity.index,identity.serial,identity.address)
        pose=tuple(pose);struct.pack_into('<12d',packet,2000,*pose);validate_request(bytes(packet))
        self._component_attempts.add(key);self._component_uncertain=True
        reply=self._transport.command('mesh',bytes(packet));raw=bytes.fromhex(reply['mesh_packet'])
        from ._owned_component_pose import decode_report
        report=decode_report(packet,raw,pose,_rigid,_same_pose)
        error=report['error']
        self._component_uncertain=False
        if error:
            failure=RuntimeError('Owned component pose rejected: '+str(error));failure.report=report;raise failure
        return report
    def ground_once(self,identities=None,*,forward_approach=False,diagnostics=False,require_clear_approach=True):
        """Place the inert arena using its actual seven spawn anchors.

        Uses shared surface/volume queries and owned actor-pose operations.
        Party clearance samples the observed exploration pawn capsule, and is
        not a promise about every future combat mesh or animation envelope.
        forward_approach keeps the first enemy anchor on the player's forward
        line and screens its approach corridor before any placement. This is
        bounded geometric screening, not proof of navmesh connectivity.
        A collisionless presentation may explicitly make only that route
        advisory. Ground support and party clearance remain mandatory; the
        receipt retains the route refusal rather than claiming it was clear.
        """
        self._scope._check()
        if type(require_clear_approach) is not bool:raise ValueError('Approach requirement must be bool')
        if not require_clear_approach:
            if not forward_approach or not diagnostics:raise ValueError('Advisory approach requires screening and diagnostics')
            cap=getattr(self._transport,'owned_battle_arena_advisory_route_protocol',0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Advisory approach unavailable')
        if type(diagnostics) is not bool or (diagnostics and not forward_approach):raise ValueError('Diagnostics require forward approach screening')
        if diagnostics:
            cap=getattr(self._transport,'owned_battle_arena_approach_diagnostics_protocol',0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Arena approach diagnostics unavailable')
        if threading.get_ident()!=self._owner._thread:raise RuntimeError('Arena requires its owning Python thread')
        cap=getattr(self._transport,'owned_battle_arena_grounding_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Owned battle arena grounding capability unavailable')
        if type(forward_approach) is not bool:raise ValueError('Forward approach flag must be bool')
        if forward_approach:
            cap=getattr(self._transport,'owned_battle_arena_approach_protocol',0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Owned battle arena approach screening unavailable')
        if self._closed or self.phase!='spawned' or self._component_uncertain or self._ground_attempted or self._camera_focus_attempted:
            raise RuntimeError('Arena grounding unavailable or already attempted; no replay')
        if identities is None:
            from ._reader import ReadBatch
            from .catalog import capture_matching
            paths=('Default__KismetSystemLibrary','KismetSystemLibrary:LineTraceSingle','GameplayStatics:BreakHitResult',
                'SceneComponent:K2_GetComponentToWorld','Actor:K2_GetActorLocation','Actor:K2_GetActorRotation',
                'Actor:K2_SetActorLocationAndRotation','KismetSystemLibrary:GetComponentBounds','KismetSystemLibrary:BoxTraceSingle')
            with ReadBatch(self._scope.pid,share=True,_executable=self._transport._executable):
                c=capture_matching(self._scope.pid,names=tuple(path.split(':')[-1] for path in paths))
                def exact(path):
                    rows=[o for o in c.objects if c.path_name(o)=='/Script/Engine.'+path]
                    if len(rows)!=1:raise RuntimeError('Exact arena grounding prerequisite unavailable: '+path)
                    return rows[0]
                identities=tuple(exact(path) for path in paths)
        if len(identities)!=9:raise ValueError('Nine observed arena grounding identities required')
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,GROUND,0,0,self._owner._owner)
        packet[24]=int(forward_approach)|(2 if diagnostics else 0)|(0 if require_clear_approach else 4)
        for i,identity in enumerate(identities):struct.pack_into('<iiQ',packet,88+16*i,identity.index,identity.serial,identity.address)
        validate_request(bytes(packet));self._ground_attempted=True;self._component_uncertain=True
        reply=self._transport.command('mesh',bytes(packet));raw=bytes.fromhex(reply['mesh_packet'])
        if len(raw)!=SIZE:raise RuntimeError('Arena ground acknowledgement malformed; preserve owner')
        error,state=struct.unpack_from('<II',raw,8)
        expected=bytearray(packet);struct.pack_into('<II',expected,8,error,state);expected[4096:4448]=raw[4096:4448]
        if diagnostics:expected[4448:4744]=raw[4448:4744]
        if raw!=bytes(expected) or state!=(0 if error else 1):raise RuntimeError('Arena ground acknowledgement differs; preserve owner')
        values=struct.unpack_from('<39d',raw,4096);flags=struct.unpack_from('<9I',raw,4408)
        candidates,samples,*booleans=flags
        approach_samples=struct.unpack_from('<I',raw,4444)[0]
        if (candidates>(3 if forward_approach else 57) or samples>31
            or approach_samples>(399 if forward_approach else 0) or any(v not in (0,1) for v in booleans)
            or any(booleans[i+1]>booleans[i] for i in range(6)) or (not candidates and samples)
            or any(not math.isfinite(v) or abs(v)>1.e8 for v in values)):
            raise RuntimeError('Arena ground report malformed; preserve owner')
        result=dict(error=error,before=values[:3],destination=values[3:6],after=values[6:9],heights=values[9:16],
            positions=[values[16+3*i:19+3*i] for i in range(7)],minimum=values[37],maximum=values[38],
            candidates=candidates,samples=samples,**dict(zip(('supported','clearance','attempted','acknowledged','engine_accepted','readback','verified'),map(bool,booleans))))
        result.update(forward_approach=forward_approach,approach_samples=approach_samples)
        result['require_clear_approach']=require_clear_approach
        if diagnostics:
            version,count=struct.unpack_from('<II',raw,4448)
            if version!=1 or count!=candidates or count>3 or any(raw[4456+96*count:4744]):
                raise RuntimeError('Arena diagnostics header differs; preserve owner')
            reasons=('not_run','supported','input','surface_rejected','no_surface','slope','step','start_height',
                'width_height','total_height','clearance_rejected','blocked','end_height')
            details=[]
            for i in range(count):
                offset=4456+96*i
                stage,ground_samples,route_samples,last_surface=struct.unpack_from('<4I',raw,offset)
                distance,minimum,maximum=struct.unpack_from('<3d',raw,offset+16)
                reason,step,lane,reserved=struct.unpack_from('<IIiI',raw,offset+40)
                xyz_observed_reference=struct.unpack_from('<5d',raw,offset+56)
                if (stage not in (1,2,3,4) or not 1<=ground_samples<=31 or route_samples>399 or last_surface not in (1,2,3,4)
                    or distance!=(1600.,2400.,3200.)[i] or reason>=len(reasons) or reserved or step>132 or lane not in (-1,0,1)
                    or any(not math.isfinite(v) or abs(v)>1.e8 for v in (distance,minimum,maximum,*xyz_observed_reference))
                    or (stage<3 and (route_samples or reason)) or (stage==4 and
                        (reason!=1 if require_clear_approach else reason not in (1,4,5,6,7,8,9,11,12)))):
                    raise RuntimeError('Arena candidate diagnostics malformed; preserve owner')
                details.append(dict(stage=('','support','party_clearance','corridor','accepted')[stage],
                    distance_cm=distance,ground_samples=ground_samples,approach_samples=route_samples,
                    last_surface=('','hit','no_hit','rejected','invalid')[last_surface],minimum=minimum,maximum=maximum,
                    reason=reasons[reason],step=step,lane=lane,position=xyz_observed_reference[:3],
                    observed=xyz_observed_reference[3],reference=xyz_observed_reference[4]))
            if not error and (not details or details[-1]['stage']!='accepted'):
                raise RuntimeError('Arena diagnostics contradict success; preserve owner')
            result['candidate_diagnostics']=details
            result['approach_supported']=bool(details and details[-1]['reason']=='supported')
        if not error and (not all(booleans) or not candidates or samples!=31 or values[38]-values[37]>100 or values[37]>values[38]
            or (forward_approach and require_clear_approach and (approach_samples<183 or approach_samples%3))
            or math.dist(result['destination'],result['after'])>.1):raise RuntimeError('Arena grounding evidence contradicts success; preserve owner')
        self.grounding=result;self._component_uncertain=False
        if error:
            failure=RuntimeError('Owned arena grounding rejected: '+str(error));failure.report=result;raise failure
        return result
    def refresh_camera_focus_once(self):
        """Recompute the original four camera targets after final arena placement.

        Calls the original Blueprint on this hidden owned arena, then verifies
        its camera children and world-space target positions. Does not activate
        a camera. Further arena movement is locked once invocation is attempted;
        retirement remains available after rejection or an unknown outcome.
        """
        self._scope._check()
        if threading.get_ident()!=self._owner._thread:raise RuntimeError('Arena requires its owning Python thread')
        if self._closed or self.phase!='spawned' or self._component_uncertain or self._camera_focus_attempted:
            raise RuntimeError('Camera focus refresh unavailable; no replay')
        from ._owned_arena_camera import refresh_camera_focus
        return refresh_camera_focus(self)
    def qualify_helper_once(self,helper,relative_pose,identities=None):
        """Qualify/reveal an original owned helper against this arena's receipt.

        The native owner rechecks both roots, retained identities, original
        class lookup and ground receipt, then acknowledges tick/visibility.
        This performs no helper movement, enemy initialization or battle entry.
        """
        self._scope._check()
        if threading.get_ident()!=self._owner._thread:raise RuntimeError('Arena requires its owning Python thread')
        cap=getattr(self._transport,'owned_helper_source_frame_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Owned helper source-frame capability unavailable')
        if self._closed or self.phase!='spawned' or self._component_uncertain or self._helper_attempted or not self.grounding or not self.grounding['verified']:
            raise RuntimeError('Verified owned arena ground receipt required; no replay')
        if identities is None:
            from ._reader import ReadBatch
            from .catalog import capture_matching
            paths=('SceneComponent:K2_GetComponentToWorld','Actor:K2_GetActorRotation','GameplayStatics:GetActorOfClass')
            with ReadBatch(self._scope.pid,share=True,_executable=self._transport._executable):
                c=capture_matching(self._scope.pid,names=tuple(path.split(':')[-1] for path in paths))
                def exact(path):
                    rows=[o for o in c.objects if c.path_name(o)=='/Script/Engine.'+path]
                    if len(rows)!=1:raise RuntimeError('Exact source-frame prerequisite unavailable: '+path)
                    return rows[0]
                identities=tuple(exact(path) for path in paths)
        if len(identities)!=3:raise ValueError('Three observed source-frame functions required')
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,QUALIFY_HELPER,0,0,self._owner._owner)
        for i,identity in enumerate((helper,*identities)):struct.pack_into('<iiQ',packet,88+16*i,identity.index,identity.serial,identity.address)
        relative_pose=tuple(relative_pose);struct.pack_into('<12d',packet,2000,*relative_pose);validate_request(bytes(packet))
        self._helper_attempted=True;self._component_uncertain=True
        reply=self._transport.command('mesh',bytes(packet));raw=bytes.fromhex(reply['mesh_packet'])
        if len(raw)!=SIZE:raise RuntimeError('Source frame acknowledgement malformed; preserve owners')
        error,state=struct.unpack_from('<II',raw,8)
        expected=bytearray(packet);struct.pack_into('<II',expected,8,error,state);expected[4096:4400]=raw[4096:4400]
        if raw!=bytes(expected) or state!=(0 if error else 1):raise RuntimeError('Source frame acknowledgement differs; preserve owners')
        values=struct.unpack_from('<36d',raw,4096);flags=struct.unpack_from('<4I',raw,4384)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in values) or any(v not in (0,1) for v in flags) or any(flags[i+1]>flags[i] for i in range(3)):
            raise RuntimeError('Source frame report malformed; preserve owners')
        arena,observed,target=values[:12],values[12:24],values[24:36]
        result=dict(error=error,arena=arena,helper=observed,expected=target,
            **dict(zip(('attempted','tick_acknowledged','visibility_acknowledged','verified'),map(bool,flags))))
        if not error:
            def unit(pose):
                return (abs(sum(v*v for v in pose[:4])-1)<=1e-6 and abs(pose[0])<=1e-6 and abs(pose[1])<=1e-6
                    and pose[7]==pose[11]==0 and all(abs(v-1)<=1e-6 for v in pose[8:11]))
            def same(a,b):
                return abs(abs(sum(x*y for x,y in zip(a[:4],b[:4])))-1)<=1e-6 and math.dist(a[4:7],b[4:7])<=.1
            c,s=arena[3]**2-arena[2]**2,2*arena[3]*arena[2]
            q=relative_pose
            composed=(0.,0.,arena[2]*q[3]+arena[3]*q[2],arena[3]*q[3]-arena[2]*q[2],
                arena[4]+c*q[4]-s*q[5],arena[5]+s*q[4]+c*q[5],arena[6]+q[6],0.,1.,1.,1.,0.)
            if flags!=(1,1,1,1) or not all(unit(p) for p in (arena,observed,target)) or not same(target,composed) or not same(observed,target) or math.dist(arena[4:7],self.grounding['after'])>.1:
                raise RuntimeError('Source frame evidence contradicts qualification; preserve owners')
        self._component_uncertain=False
        if error:
            failure=RuntimeError('Owned helper source frame rejected: '+str(error));failure.report=result;raise failure
        return result
    def close(self):
        if self._closed:return True
        # Keep the primary sentinel and both owners when companion retirement is
        # deferred or unknown. Scope cleanup also visits the companion first.
        if self._companion is not None and not self._companion.close():return False
        if not self._owner.close():return False
        self._closed=True
        if getattr(self._transport,'_owned_battle_arena_owner',None) is self:self._transport._owned_battle_arena_owner=None
        return True
