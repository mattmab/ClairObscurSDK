"""Scoped native visual staging, independent of editor menus and camera control.

Consumes the existing bounded native scene plan/identities. It does not discover
assets, encode editor documents, select encounters or authorize combat entry.
"""
import secrets
import math
import struct
import threading

SIZE=20984
ACTIVATE=148
ARENA_PREFLIGHT=149
GROUND=150


class VisualGroundingError(RuntimeError):
    def __init__(self,result):
        self.result=result
        super().__init__('Native visual grounding rejected; preserve owner and do not retry: '+str(result))


def decode_grounding(raw):
    if type(raw) is not bytes or len(raw)!=128:raise ValueError('Exact native grounding report required')
    result,samples,support,clearance=struct.unpack_from('<4I',raw)
    values=struct.unpack_from('<11d',raw,16)
    flags=struct.unpack_from('<5I',raw,104)
    candidates=struct.unpack_from('<I',raw,124)[0]
    if result>5 or samples>9 or support>1 or clearance>1 or any(v>1 for v in flags) or candidates>27:
        raise ValueError('Native grounding report bounds')
    if any(not math.isfinite(v) or abs(v)>1.e8 for v in values):raise ValueError('Native grounding geometry bounds')
    minimum,maximum=values[:2];destination=values[2:5];after=values[8:11]
    if flags[4] and (result or samples!=9 or not candidates or not support or not clearance or not all(flags) or
        minimum>maximum or maximum-minimum>100. or math.dist(destination,after)>.1):
        raise ValueError('Native grounding verification contradicts its evidence')
    return dict(result=result,samples=samples,support=bool(support),clearance=bool(clearance),
        minimum=minimum,maximum=maximum,destination=destination,before=values[5:8],after=after,
        attempted=bool(flags[0]),acknowledged=bool(flags[1]),engine_accepted=bool(flags[2]),
        readback=bool(flags[3]),verified=bool(flags[4]),candidates=candidates)


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Visual staging packet size')
    version,operation,error,state,owner=struct.unpack_from('<4IQ',data)
    if version!=7 or operation not in (ACTIVATE,ARENA_PREFLIGHT,GROUND) or error or state or not owner:
        raise ValueError('Exact visual-staging operation required')
    if operation==ACTIVATE:
        if any(data[24:]):raise ValueError('Exact empty visual-staging activation required')
    else:
        count=10 if operation==GROUND else 5
        if any(data[24:88]) or any(data[88+16*count:]):raise ValueError('Exact visual operation prerequisites required')
        identities=[struct.unpack_from('<iiQ',data,88+16*i) for i in range(count)]
        if any(index<=0 or serial<0 or address<0x10000 or address%8 for index,serial,address in identities):
            raise ValueError('Invalid observed arena prerequisite identity')


class NativeVisualStage:
    """One-shot preparation with scope-owned cleanup and authoritative native status."""
    def __init__(self,scope):
        scope._check()
        transport=scope._session._transport
        if type(getattr(transport,'native_visual_staging_protocol',None)) is not int or transport.native_visual_staging_protocol!=1:
            raise RuntimeError('Native visual staging requires its negotiated SDK capability')
        if getattr(transport,'runtime_scene_protocol',0)!=7:raise RuntimeError('Bounded native scene protocol seven required')
        if getattr(transport,'_native_visual_stage_owner',None) is not None:raise RuntimeError('Native visual stage already owned')
        if not callable(getattr(scope,'_register_native_owner',None)):raise RuntimeError('Native scope cleanup unavailable')
        self._scope=scope;self._transport=transport;self.token=secrets.randbits(64) or 1
        self._thread=threading.get_ident();self._attempted=False;self._closed=False;self._cleanup_unknown=False
        self.uncertain=False;self.last_result=None;self._arena_attempted=False;self._arena_bound=False
        self._ground_attempted=False;self.grounding=None
        scope._register_native_owner(self);transport._native_visual_stage_owner=self

    def _check(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Visual stage requires its owning Python thread')
        self._scope._check()
        if self._closed:raise RuntimeError('Visual stage is closed')

    def _packet(self,operation,payload=b''):
        from ._runtime_scene_wire import validate_request as validate_scene
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,7,operation,0,0,self.token)
        if len(payload)>SIZE-88:raise ValueError('Visual staging payload bounds')
        packet[88:88+len(payload)]=payload
        raw=bytes(packet)
        if operation in (ACTIVATE,ARENA_PREFLIGHT,GROUND):validate_request(raw)
        else:validate_scene(raw,protocol=7)
        return raw

    def _exchange(self,packet):
        self.uncertain=True
        reply=self._transport.command('mesh',packet)
        raw=bytes.fromhex(reply['mesh_packet'])
        grounding=struct.unpack_from('<I',packet,4)[0]==GROUND
        payload_matches=(raw[88:4096]==packet[88:4096] and raw[4224:20976]==packet[4224:20976]) if grounding else raw[88:20976]==packet[88:20976]
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:24]!=packet[16:24] or not payload_matches:
            raise RuntimeError('Visual staging acknowledgement differs; preserve ownership')
        error,state=struct.unpack_from('<II',raw,8)
        leases,poses=struct.unpack_from('<II',raw,20976)
        if state not in (0,1,3,4,5,6,9) or leases>600:raise RuntimeError('Visual staging acknowledgement state bounds')
        report=decode_grounding(raw[4096:4224]) if grounding else None
        self.last_result=dict(native_error=error,state=state,private_leases=leases,camera_updates=poses,
            actor_identity=struct.unpack_from('<iiQ',raw,24),component_identity=struct.unpack_from('<iiQ',raw,40),
            elapsed=struct.unpack_from('<d',raw,56)[0],animation_dispatched=bool(struct.unpack_from('<I',raw,84)[0]&1))
        if grounding:self.last_result['grounding']=report
        self.uncertain=False
        return self.last_result

    def prepare(self,plan,identities):
        self._check()
        if self._attempted:raise RuntimeError('Visual staging preparation is never replayed')
        if type(plan) is not bytes or len(identities)!=134:raise ValueError('Exact bounded plan and134 identities required')
        packed=b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in identities)
        # Validate every outgoing packet before the first engine mutation.
        packets=(self._packet(74,plan),self._packet(70,packed),self._packet(ACTIVATE))
        self._attempted=True
        for packet in packets:
            result=self._exchange(packet)
            if result['native_error']:raise RuntimeError('Native visual staging rejected: '+str(result))
        if result['state']!=9 or result['camera_updates']:
            raise RuntimeError('Expected camera-independent staged state; preserve owner')
        return result

    def status(self):
        self._check();return self._exchange(self._packet(73))

    def bind_parameter_arena(self,identities):
        """Bind current world + arena/conversion observations; grants no dispatch."""
        self._check()
        capability=getattr(self._transport,'native_visual_encounter_preflight_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Visual encounter preflight unavailable')
        if not self._attempted or self.uncertain or self.last_result is None or self.last_result['state']!=9 or self.last_result['native_error']:
            raise RuntimeError('Acknowledged native visual stage required')
        if self._arena_attempted:raise RuntimeError('Visual arena binding is never replayed')
        if len(identities)!=5:raise ValueError('Current world plus four exact arena prerequisites required')
        packed=b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in identities)
        packet=self._packet(ARENA_PREFLIGHT,packed)
        self._arena_attempted=True
        result=self._exchange(packet)
        if result['native_error']:raise RuntimeError('Visual arena binding rejected: '+str(result))
        if result['state']!=9 or result['camera_updates']:raise RuntimeError('Visual arena acknowledgement state changed')
        self._arena_bound=True
        return result

    def preflight_original_parameters(self,asset_path,source_path):
        """Exercise the existing owned-copy/arena preflight without battle entry.

        The original source is retained only for this transaction. Native checks
        prove current ownership and byte-preserving source copying; no source
        GameAction, campaign sequence or combat invocation is exposed here.
        """
        self._check()
        if not self._arena_bound:raise RuntimeError('Verified owned visual arena required')
        from .original_trigger_sources import _validate_paths,_owned_source,BATTLE_STRUCT
        from ._scope import SessionScope
        from .assets import load_asset
        from ._reader import ReadBatch
        from .catalog import capture_matching,capture_selected
        from .cinematics.original_game_action import controller_context
        from ._npc_encounter_preparation import _controller_battle_manager
        from ._battle_parameter_owner import ParameterResearchOwner
        _validate_paths(asset_path,source_path)
        status=self.status()
        if status['native_error'] or status['state']!=9:raise RuntimeError('Current visual ownership unavailable')
        child=SessionScope(self._scope)
        try:
            root=load_asset(child,asset_path).return_value
            if root is None:raise RuntimeError('Original battle source did not load')
            context=controller_context(child._session)
            with ReadBatch(child.pid,share=True,_executable=self._transport._executable):
                c=capture_matching(child.pid,classes=('BP_GameAction_TriggerBattle_C',),names=('FBattleStartParams','StartBattleNEW'))
                c=c.with_observations(capture_selected(child.pid,((root.index,root.serial,root.address),
                    tuple(status['actor_identity']),tuple(context['controller'][1:]))))
                source=_owned_source(c,root,source_path)
                structures=[o for o in c.objects if c.path_name(o)==BATTLE_STRUCT]
                functions=[o for o in c.objects if c.path_name(o)=='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:StartBattleNEW']
                if len(structures)!=1 or len(functions)!=1:raise RuntimeError('Exact original battle entry prerequisites unavailable')
                manager,c=_controller_battle_manager(c,c.by_index[context['controller'][1]])
                actor=c.by_index[status['actor_identity'][0]]
                if (actor.index,actor.serial,actor.address)!=tuple(status['actor_identity']):raise RuntimeError('Visual identity changed')
                identities=(structures[0],source,root,actor,manager,functions[0])
                if controller_context(child._session)!=context:raise RuntimeError('Travel during visual parameter preparation')
            parameters=ParameterResearchOwner(child)
            parameters.match(identities[:3])
            parameters.entry_arena_cleanup(identities,mode=1,anchor_owner=self.token,dispatch=False,arena_policy=1)
            return dict(native_source_match=True,entry_preflight_verified=True,arena_binding_verified=True,
                source_parameter_bytes_unchanged=True,battle_dispatched=False,source_path=source_path,
                actor_identity=status['actor_identity'])
        finally:
            child.close()

    def ground(self,identities=None):
        """One placement using observed component bounds, support and clearance.

        Requires an already bound current-world arena. This is point-in-time
        geometry evidence, not navigation or whole-animation-envelope coverage.
        """
        self._check()
        capability=getattr(self._transport,'native_visual_grounding_protocol',0)
        if type(capability) is not int or capability!=2:raise RuntimeError('Native visual grounding unavailable')
        if self._ground_attempted:raise RuntimeError('Visual placement is never replayed')
        if not self._arena_bound or self.uncertain or self.last_result is None or self.last_result['state']!=9 or self.last_result['native_error']:
            raise RuntimeError('Acknowledged staged visual and bound arena required')
        if identities is None:
            from ._npc_encounter_preparation import grounding_queries
            identities=grounding_queries(self._scope)
        if len(identities)!=10:raise ValueError('Exact ten grounding prerequisites required')
        packed=b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in identities)
        packet=self._packet(GROUND,packed)
        self._ground_attempted=True
        result=self._exchange(packet);self.grounding=result.get('grounding')
        if result['native_error'] or result['state']!=9 or result['camera_updates'] or not self.grounding or not self.grounding['verified']:
            raise VisualGroundingError(result)
        return result

    def close(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Visual cleanup requires its owning Python thread')
        if self._closed:return True
        if self._cleanup_unknown:return False
        if self._attempted:
            try:result=self._exchange(self._packet(72))
            except BaseException:
                self._cleanup_unknown=True;raise
            if result['native_error'] or result['private_leases'] or result['state'] not in (0,4,5,6):
                self._cleanup_unknown=result['native_error'] not in (0,407)
                return False
        self._closed=True
        if self in self._scope._native_owners:self._scope._native_owners.remove(self)
        if getattr(self._transport,'_native_visual_stage_owner',None) is self:self._transport._native_visual_stage_owner=None
        return True
