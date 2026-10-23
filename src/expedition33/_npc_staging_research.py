"""Bounded original Clea staging research. No encounter or activation command."""
import math
import struct
import threading

SIZE=20984
STAGE,STATUS,CLOSE=136,137,138
PLACE,PLACEMENT_STATUS=139,140
GROUNDED_STAGE=141
REVEAL=142
ARENA_BIND,ARENA_STATUS=143,144
PROXIMITY=145
SOLID,OVERLAP=146,147


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('NPC staging packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if version!=3 or op not in (STAGE,STATUS,CLOSE,PLACE,PLACEMENT_STATUS,GROUNDED_STAGE,REVEAL,ARENA_BIND,ARENA_STATUS,PROXIMITY,SOLID,OVERLAP) or error or state or not owner:raise ValueError('NPC staging header')
    allowed=bytearray(SIZE)
    if op in (ARENA_BIND,SOLID):
        allowed[88:152]=bytes([1])*64
        for n in range(4):
            index,serial,address=struct.unpack_from('<iiQ',data,88+n*16)
            if index<0 or serial<0 or address<0x10000:raise ValueError('Exact arena value query identity required')
    if op==OVERLAP:
        allowed[88:264]=bytes([1])*176
        for n in range(11):
            index,serial,address=struct.unpack_from('<iiQ',data,88+n*16)
            if index<0 or serial<0 or address<0x10000:raise ValueError('Exact overlap identities required')
    if op in (PLACE,PROXIMITY):
        allowed[88:248]=bytes([1])*160
        for n in range(10):
            index,serial,address=struct.unpack_from('<iiQ',data,88+n*16)
            if index<0 or serial<0 or address<0x10000:raise ValueError('Exact observed NPC placement identity required')
    if op==GROUNDED_STAGE:
        allowed[376:536]=bytes([1])*160
        for n in range(10):
            index,serial,address=struct.unpack_from('<iiQ',data,376+n*16)
            if index<0 or serial<0 or address<0x10000:raise ValueError('Exact grounded construction query required')
    if op in (STAGE,GROUNDED_STAGE):
        allowed[88:376]=bytes([1])*288;allowed[2000:2096]=bytes([1])*96
        for n in range(18):
            index,serial,address=struct.unpack_from('<iiQ',data,88+n*16)
            if index<0 or serial<0 or address<0x10000:raise ValueError('Exact observed NPC source identity required')
        pose=struct.unpack_from('<12d',data,2000)
        if any(not math.isfinite(v) or abs(v)>1.e7 for v in pose):raise ValueError('NPC transform finite bounds')
        if not .999<=sum(v*v for v in pose[:4])<=1.001 or pose[7] or pose[11] or pose[8:11]!=(1,1,1):
            raise ValueError('NPC normalized unit-scale transform required')
    if any(data[i] for i in range(24,SIZE) if not allowed[i]):raise ValueError('NPC staging padding')


def exchange(transport,operation,token,identities=None,pose=None,grounding=None):
    capability=getattr(transport,'npc_original_staging_research_protocol',0)
    if type(capability) is not int or capability!=1:raise RuntimeError('Original NPC staging unavailable')
    if operation in (ARENA_BIND,ARENA_STATUS):
        capability=getattr(transport,'npc_arena_value_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('NPC arena value unavailable')
    if operation in (SOLID,OVERLAP):
        capability=getattr(transport,'npc_interaction_variants_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('NPC interaction variants unavailable')
    if operation==PROXIMITY:
        capability=getattr(transport,'npc_proximity_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('NPC proximity unavailable')
    if operation==REVEAL:
        capability=getattr(transport,'npc_original_preview_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Original NPC preview unavailable')
    if operation in (PLACE,PLACEMENT_STATUS):
        capability=getattr(transport,'npc_original_placement_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Original NPC placement unavailable')
    if operation==GROUNDED_STAGE:
        capability=getattr(transport,'npc_original_grounded_construction_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Original NPC grounded construction unavailable')
        if grounding is None or len(grounding)!=10:raise ValueError('Exact ten grounded construction queries required')
    elif grounding is not None:raise ValueError('Unexpected grounded construction queries')
    if type(token) is not int or not 0<token<2**64:raise ValueError('Exact nonzero owner token required')
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,operation,0,0,token)
    if operation in (STAGE,GROUNDED_STAGE):
        if identities is None or len(identities)!=18 or pose is None or len(pose)!=12:raise ValueError('Exact bounded NPC source/pose required')
        for n,obj in enumerate(identities):struct.pack_into('<iiQ',packet,88+n*16,obj.index,obj.serial,obj.address)
        struct.pack_into('<12d',packet,2000,*pose)
        if operation==GROUNDED_STAGE:
            for n,obj in enumerate(grounding):struct.pack_into('<iiQ',packet,376+n*16,obj.index,obj.serial,obj.address)
    elif operation in (PLACE,ARENA_BIND,PROXIMITY,SOLID,OVERLAP):
        if identities is None or len(identities)!=(4 if operation in (ARENA_BIND,SOLID) else 11 if operation==OVERLAP else 10) or pose is not None:raise ValueError('Exact bounded placement/arena sources required')
        for n,obj in enumerate(identities):struct.pack_into('<iiQ',packet,88+n*16,obj.index,obj.serial,obj.address)
    elif identities is not None or pose is not None:raise ValueError('Status/close carry no new source data')
    validate_request(bytes(packet))
    reply=transport.command('mesh',bytes(packet))
    raw=bytes.fromhex(reply['mesh_packet'])
    if len(raw)!=SIZE:raise RuntimeError('NPC staging acknowledgement size; query same owner status, never replay stage')
    compare=bytearray(raw);compare[8:16]=packet[8:16];compare[4096:4224]=packet[4096:4224]
    if operation in (PLACE,PLACEMENT_STATUS,GROUNDED_STAGE,REVEAL):compare[4240:4416]=packet[4240:4416]
    if operation==REVEAL:compare[4416:4432]=packet[4416:4432]
    if operation in (ARENA_BIND,ARENA_STATUS):compare[4432:4480]=packet[4432:4480]
    if operation==PROXIMITY:compare[4480:4536]=packet[4480:4536]
    if operation in (SOLID,OVERLAP):compare[4536:4568]=packet[4536:4568]
    if operation==OVERLAP:compare[4568:4572]=packet[4568:4572]
    if compare!=packet:raise RuntimeError('NPC staging acknowledgement changed immutable data; preserve owner')
    error,state=struct.unpack_from('<II',raw,8)
    if state!=(0 if error else 1):raise RuntimeError('NPC staging acknowledgement incomplete; preserve owner')
    owned,construction,retirement,unreviewed=struct.unpack_from('<4I',raw,4096)
    step,entry_phase=struct.unpack_from('<2I',raw,4096+120)
    if owned>1 or construction>12 or retirement>7 or unreviewed>128 or step>8 or entry_phase>3:raise RuntimeError('NPC staging status bounds')
    def identity(at):
        index,serial,address=struct.unpack_from('<iiQ',raw,4096+at)
        if not address:
            if index not in (-1,0) or serial:raise RuntimeError('Malformed empty NPC identity')
            return None
        if index<0 or serial<0 or address<0x10000:raise RuntimeError('Malformed exact NPC identity')
        return [index,serial,address]
    count=struct.unpack_from('<Q',raw,4096+64)[0]
    if count>128:raise RuntimeError('NPC retained target bound')
    result=dict(native_error=error,has_work=bool(owned),construction_phase=construction,retirement_phase=retirement,
                unreviewed_components=unreviewed,actor_identity=identity(16),guid=list(struct.unpack_from('<4I',raw,4096+32)),
                unexpected_controller=identity(48),retained_targets=count,
                body=identity(72),face=identity(88),hair=identity(104),owner_token=token,
                step=step,entry_phase=entry_phase,ownership_unknown=error in (3451,3453),encounter_enabled=False)
    if operation in (SOLID,OVERLAP):
        flags=struct.unpack_from('<8I',raw,4536)
        if any(flags[i]>1 for i in (0,1,2,7)) or flags[3]>5 or flags[5]>5 or flags[4]>2 or flags[6]>2:raise RuntimeError('Invalid collision readback')
        if flags[2] and not (flags[0] and flags[1] and flags[5]==3 and flags[6]==2 and flags[7]):raise RuntimeError('Incomplete solid collision proof')
        if operation==SOLID and not error and not flags[2]:raise RuntimeError('Solid collision acknowledgement lacks verification')
        result['collision']=dict(zip(('attempted','acknowledged','verified','before_mode','before_response','mode','response','actor_enabled'),flags))
    if operation==OVERLAP and not error:
        value=struct.unpack_from('<I',raw,4568)[0]
        if value>1 or not result['collision']['verified']:raise RuntimeError('Invalid overlap observation')
        result['overlap']=bool(value)
    if operation==PROXIMITY and not error:
        values=struct.unpack_from('<7d',raw,4480)
        if any(not math.isfinite(v) for v in values) or values[0]<0:raise RuntimeError('Invalid proximity observation')
        expected=sum((a-b)**2 for a,b in zip(values[1:4],values[4:7]))
        if not math.isclose(expected,values[0],rel_tol=1.e-8,abs_tol=.001):raise RuntimeError('Proximity distance readback differs')
        result['proximity']=dict(distance_squared=values[0],player=list(values[1:4]),actor=list(values[4:7]))
    if operation in (PLACE,PLACEMENT_STATUS,GROUNDED_STAGE,REVEAL):
        flags=struct.unpack_from('<10I',raw,4240);values=struct.unpack_from('<17d',raw,4280)
        if flags[0]>7 or flags[1]>9 or any(v>1 for v in flags[2:]) or any(not math.isfinite(v) for v in values):
            raise RuntimeError('Malformed NPC placement journal')
        placement=dict(zip(('result','samples','support','clearance','verified','attempted','acknowledged','accepted','readback'),flags[:9]))
        placement['at_construction']=bool(flags[9])
        placement.update(minimum=values[0],maximum=values[1],destination=list(values[2:5]),before=list(values[5:11]),after=list(values[11:17]))
        valid_move=all(flags[2:9]) and not flags[9]
        valid_birth=flags[2] and flags[3] and flags[8] and flags[9] and not any(flags[5:8])
        if placement['verified'] and not (placement['result']==0 and placement['samples']==9 and (valid_move or valid_birth)):
            raise RuntimeError('Contradictory verified NPC placement')
        if placement['verified'] and (not owned or construction!=12):raise RuntimeError('Verified placement requires a constructed owned NPC')
        result['placement']=placement
    if operation==REVEAL:
        flags=struct.unpack_from('<4I',raw,4416)
        if any(v>1 for v in flags) or (not error and flags!=(1,1,1,1)):
            raise RuntimeError('Invalid original NPC visibility acknowledgement')
        result['reveal']=dict(zip(('attempted','acknowledged','observed','visible'),flags))
    if operation in (ARENA_BIND,ARENA_STATUS):
        flags=struct.unpack_from('<8I',raw,4432)
        index,serial,address=struct.unpack_from('<iiQ',raw,4464)
        if any(v>1 for v in flags[:5]) or flags[5]>4 or any(flags[6:]):raise RuntimeError('Invalid NPC arena journal')
        if address:
            if index<0 or serial<0 or address<0x10000:raise RuntimeError('Invalid retained arena identity')
            arena_identity=[index,serial,address]
        else:
            if index not in (-1,0) or serial:raise RuntimeError('Malformed empty arena identity')
            arena_identity=None
        if flags[3] and not (owned and construction==12 and flags[:3]==(1,1,1) and not flags[4] and flags[5]==4 and arena_identity):
            raise RuntimeError('Contradictory verified NPC arena value')
        if operation==ARENA_BIND and not error and not flags[3]:raise RuntimeError('Arena binding success lacks verified value')
        result['arena']=dict(zip(('requested','attempted','assigned','verified','temporary_live','leases'),flags[:6]))
        result['arena']['identity']=arena_identity
    return result


def request(scope,operation,token,identities=None,pose=None,grounding=None):
    scope._check()
    with scope._lease_context():
        return exchange(scope._session._transport,operation,token,identities,pose,grounding)


class NativeStagingOwner:
    """Scope cleanup precedes ordinary lease release; native remains authoritative."""
    def __init__(self,scope,token):
        scope._check()
        transport=scope._session._transport
        if getattr(transport,'_npc_staging_owner',None) is not None:raise RuntimeError('Original NPC service already has a Python owner')
        if not callable(getattr(scope,'_register_native_owner',None)):raise RuntimeError('Generic native scope cleanup unavailable')
        if type(token) is not int or not 0<token<2**64:raise ValueError('Exact nonzero owner token required')
        if type(getattr(transport,'npc_original_staging_research_protocol',None)) is not int or transport.npc_original_staging_research_protocol!=1:
            raise RuntimeError('Original NPC staging unavailable')
        self._scope=scope;self._transport=transport;self.token=token;self._thread=threading.get_ident()
        self._attempted=False;self._placement_attempted=False;self._reveal_attempted=False;self._arena_attempted=False;self._collision_attempted=False;self._closed=False;self._cleanup_unknown=False;self.last_result=None
        scope._register_native_owner(self);transport._npc_staging_owner=self
    def stage(self,identities,pose,grounding=None):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native owner requires its Python thread')
        self._scope._check()
        if self._attempted or self._closed:raise RuntimeError('Native stage is never replayed')
        self._attempted=True
        self.last_result=request(self._scope,GROUNDED_STAGE if grounding is not None else STAGE,self.token,identities,pose,grounding)
        return self.last_result
    def status(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native owner requires its Python thread')
        self._scope._check()
        self.last_result=request(self._scope,STATUS,self.token)
        return self.last_result
    def place(self,identities):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native placement requires its Python thread')
        self._scope._check()
        if self._closed or self._placement_attempted or not self._attempted or self.last_result is None or self.last_result['native_error'] or not self.last_result['has_work']:
            raise RuntimeError('Placement requires prepared owner and is never replayed')
        self._placement_attempted=True
        self.last_result=request(self._scope,PLACE,self.token,identities)
        return self.last_result
    def placement_status(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native status requires its Python thread')
        self._scope._check()
        self.last_result=request(self._scope,PLACEMENT_STATUS,self.token)
        return self.last_result
    def reveal(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native preview requires its Python thread')
        self._scope._check()
        if self._closed or self._reveal_attempted or self.last_result is None or self.last_result['native_error'] or not self.last_result.get('placement',{}).get('verified'):
            raise RuntimeError('Preview requires verified grounding and is never replayed')
        self._reveal_attempted=True
        self.last_result=request(self._scope,REVEAL,self.token)
        return self.last_result
    def bind_arena(self,identities):
        if threading.get_ident()!=self._thread:raise RuntimeError('Arena binding requires its Python thread')
        self._scope._check()
        if self._closed or self._arena_attempted or self.last_result is None or self.last_result['native_error'] or not self.last_result['has_work']:
            raise RuntimeError('Arena binding requires a prepared owner and is never replayed')
        self._arena_attempted=True
        self.last_result=request(self._scope,ARENA_BIND,self.token,identities)
        return self.last_result
    def proximity(self,identities):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native proximity requires its Python thread')
        self._scope._check()
        if self._closed or not self._attempted:raise RuntimeError('Prepared native owner required')
        self.last_result=request(self._scope,PROXIMITY,self.token,identities)
        return self.last_result
    def enable_collision(self,identities):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native collision requires its Python thread')
        self._scope._check()
        if self._closed or self._collision_attempted:raise RuntimeError('Collision configuration is never replayed')
        self._collision_attempted=True
        self.last_result=request(self._scope,SOLID,self.token,identities);return self.last_result
    def overlap(self,identities):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native overlap requires its Python thread')
        self._scope._check()
        if self._closed or not self._collision_attempted:raise RuntimeError('Configured solid owner required')
        self.last_result=request(self._scope,OVERLAP,self.token,identities);return self.last_result
    def arena_status(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Arena status requires its Python thread')
        self._scope._check();self.last_result=request(self._scope,ARENA_STATUS,self.token);return self.last_result
    def close(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Native cleanup requires its Python thread')
        if self._closed:return True
        if self._cleanup_unknown:return False
        if self._attempted:
            # Scope.close revokes callbacks first. Use the cached transport for
            # cleanup, never bypass scope checks for a new stage or mutation.
            try:self.last_result=exchange(self._transport,CLOSE,self.token)
            except BaseException:
                self._cleanup_unknown=True;raise
            if self.last_result['native_error'] or self.last_result['has_work']:
                self._cleanup_unknown=self.last_result['native_error'] in (3437,3438,3451,3453)
                return False
        self._closed=True
        if self in self._scope._native_owners:self._scope._native_owners.remove(self)
        if getattr(self._transport,'_npc_staging_owner',None) is self:self._transport._npc_staging_owner=None
        return True
