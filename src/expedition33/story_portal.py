"""Owned native E-to-zone handoff. Receipt handling never dispatches travel."""
import logging,secrets,struct,time,uuid
from contextlib import contextmanager
from ._scope import SessionScope
from ._reader import shared_operation
from .catalog import capture_matching
from ._stable_lease import acquire_stable
from .zone_travel import prepare_spawn_registration,validate_request as validate_zone
SIZE=20984
ID=struct.Struct('<iiQ')
LOG=logging.getLogger(__name__)

class PortalHandoffError(RuntimeError):pass

def validate(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Portal packet size')
    version,op,error,state,owner,carrier=struct.unpack_from('<4I2Q',data)
    if (version,op,error,state)!=(3,244,0,0) or not owner or not carrier:raise ValueError('Portal packet header')
    for at in (32,48,64,80):
        index,serial,address=ID.unpack_from(data,at)
        if index<0 or serial<=0 or address<0x10000 or address&7:raise ValueError('Portal identity')
    if struct.unpack_from('<I',data,96)[0]!=0xe33c5701:raise ValueError('Portal save namespace')
    mode,seq,last,elapsed=struct.unpack_from('<4I',data,112)
    if mode>2 or seq or last or elapsed or data[608]>1 or data[609]>1 or (data[609] and not data[608]):raise ValueError('Portal packet padding')
    if data[609]:
        index,serial,address=ID.unpack_from(data,640)
        if index<0 or serial<=0 or address<0x10000 or address&7 or not struct.unpack_from('<Q',data,656)[0]:raise ValueError('Portal interaction identity/lease')
        if any(data[610:640]) or any(data[664:]):raise ValueError('Portal direct interaction padding')
    elif any(data[609:]):raise ValueError('Portal packet padding')
    validate_zone(data[128:560])
    if struct.unpack_from('<I',data,132)[0]!=0 or not all(struct.unpack_from('<6Q',data,560)):raise ValueError('Portal preflight/leases')

def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=SIZE:raise PortalHandoffError('Portal reply size; retain owner')
    clean=bytearray(reply);clean[8:16]=sent[8:16];clean[116:128]=sent[116:128]
    if sent[608]:clean[616:624]=sent[616:624]
    if bytes(clean)!=sent:raise PortalHandoffError('Portal reply identity changed; retain owner')
    error,state=struct.unpack_from('<2I',reply,8)
    seq,last,elapsed=struct.unpack_from('<3I',reply,116)
    if error:raise PortalHandoffError('Native portal rejected: '+str((error,last)))
    if state not in (1,2,3,4) or seq>1:raise PortalHandoffError('Invalid portal receipt')
    result=dict(state=state,sequence=seq,native_error=last,handoff_ms=elapsed)
    if sent[608]:result['activation_ms']=struct.unpack_from('<Q',reply,616)[0]
    return result

class StoryPortal:
    def __init__(self,parent,npc,ctx,key,route):
        parent._check()
        if getattr(parent._session._transport,'story_portal_handoff_protocol',0)!=1:raise RuntimeError('Native portal handoff requires SDK runtime 294')
        self._scope=parent;self.scope=SessionScope(parent);self.owner=secrets.randbits(64) or 1
        self.started=False;self.closed=False;self.unknown=False;self.consumed=False
        self.key=key;self.visit=tuple(ctx['visit']);self.route=dict(route);self.receipt=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
        # Adopt the Python owner before constructing or sending anything.
        self.npc=npc;self.ctx=ctx;self.packet=None
    @property
    def state(self):return 'closed' if self.closed else 'unknown' if self.unknown else 'active'
    @contextmanager
    def _preparation_phase(self,name):
        started=time.perf_counter()
        try:yield
        finally:
            timings=getattr(self,'preparation_timings',None)
            if timings is None:self.preparation_timings=timings={}
            timings[name]=timings.get(name,0.)+(time.perf_counter()-started)*1000
    def _observe_registration(self):
        # This entire phase is read-only. A loading/GC race may defer it before
        # acquiring leases or attempting the one-shot native registration.
        with self._preparation_phase('zone context and route'):
            packet,catalog,system=prepare_spawn_registration(self.scope,self.route,self.route['spawn_tag'])
            zone=bytearray(packet)
            identities=tuple(ID.unpack_from(zone,16+16*i) for i in range(6))
        function=None
        if self.route.get('local_transfer') and getattr(self.scope._session._transport,'story_direct_portal_protocol',0)==1:
            with self._preparation_phase('interaction metadata'):
                construction=getattr(self.scope._session,'_story_construction_resources',None)
                discovered=(construction.catalog(self.scope,('OnInteractionRequested',)) if construction is not None
                    else capture_matching(self.scope.pid,names=('OnInteractionRequested',)))
                function=discovered.find_path('/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog.BP_jRPG_NPC_Dialog_C:OnInteractionRequested')
        return zone,identities,catalog,system,function
    def prepare(self):
        if self.packet is not None or self.started or self.unknown or self.closed:raise RuntimeError('Portal registration is one-shot')
        started=time.perf_counter();self.preparation_timings={}
        construction=self.scope._session._story_construction_resources;resources=construction.resources
        temporary=SessionScope(self.scope)
        try:
            with shared_operation(self.scope.pid):
                from .story_preflight import observe
                zone,identities,c,system_object,function=observe(self._observe_registration)
                with self._preparation_phase('resource retention'):
                    holds=[resources.hold(c.by_index[identity[0]]) for identity in identities[:5]]
                    for i,held in enumerate(holds):ID.pack_into(zone,16+16*i,held.object.index,held.object.serial,held.object.address)
                    end=next(o for o in construction.metadata if o.name=='EndDialogue');end=resources.hold(end)
                with self._preparation_phase('dialogue lease'):
                    system,_=acquire_stable(temporary,system_object)
                p=bytearray(SIZE);struct.pack_into('<4I2Q',p,0,3,244,0,0,self.owner,self.npc.actor.owner._owner)
                for at,identity in ((32,self.npc.identity),(48,self.ctx['visit']),(64,(system.object.index,system.object.serial,system.object.address)),(80,(end.object.index,end.object.serial,end.object.address))):ID.pack_into(p,at,*identity)
                if uuid.UUID(self.key).hex!=self.key:raise ValueError('Canonical story identity required')
                struct.pack_into('<4I',p,96,*(int(self.key[i:i+8],16) for i in range(0,32,8)))
                p[128:560]=zone;struct.pack_into('<6Q',p,560,*(held._token for held in holds+[end]))
                if self.route.get('local_transfer'):
                    if getattr(self.scope._session._transport,'story_local_transfer_protocol',0)!=1:raise RuntimeError('Local portal transfer requires runtime 296')
                    p[608]=1
                    if getattr(self.scope._session._transport,'story_direct_portal_protocol',0)==1:
                        with self._preparation_phase('resource retention'):function=resources.hold(function)
                        p[609]=1;ID.pack_into(p,640,function.object.index,function.object.serial,function.object.address)
                        struct.pack_into('<Q',p,656,function._token)
                self.packet=bytes(p)
                with self._preparation_phase('native registration'):self._send(0)
                self.started=True
        finally:
            with self._preparation_phase('temporary cleanup'):temporary.close()
            LOG.info('Portal preparation started=%s unknown=%s elapsed_ms=%.2f active phases=%s',
                self.started,self.unknown,(time.perf_counter()-started)*1000,self.preparation_timings)
        return self
    def _send(self,mode):
        self.scope._check()
        p=bytearray(self.packet);struct.pack_into('<I',p,112,mode);p=bytes(p);validate(p)
        try:
            with self.scope._lease_context():reply=self.scope._session._transport.command('mesh',p)
            receipt=decode(p,bytes.fromhex(reply['mesh_packet']))
        except BaseException:self.unknown=True;raise
        self.receipt=receipt;return receipt
    def status(self):
        if self.closed:raise RuntimeError('Portal owner closed')
        return self._send(1)
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self._send(2)
        self.scope.close();self.closed=True;return True
