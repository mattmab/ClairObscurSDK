"""Dedicated timeline actor slots over the existing owned-construction API."""
import struct
from . import _enemy_spawn_wire as legacy
from ._enemy_spawn_owner import EnemySpawnOwner

OPERATIONS={120:223,221:224,111:225}
REVERSE={v:k for k,v in OPERATIONS.items()}


def _operation(packet,operation):
    result=bytearray(packet);struct.pack_into('<I',result,4,operation);return bytes(result)


def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=legacy.SIZE:raise ValueError('Exact timeline actor packet required')
    operation=struct.unpack_from('<I',packet,4)[0]
    if operation not in REVERSE:raise ValueError('Unknown timeline actor operation')
    legacy.validate_request(_operation(packet,REVERSE[operation]))


class _ActorTransport:
    def __init__(self,transport):
        cap=getattr(transport,'timeline_actor_pool_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Timeline actor pool required')
        self._base=transport;self._enemy_spawn_owner=None;self._reservation_rejected=False
    def __getattr__(self,name):return getattr(self._base,name)
    def command(self,name,packet):
        legacy.validate_request(packet);operation=struct.unpack_from('<I',packet,4)[0]
        if name!='mesh' or operation not in OPERATIONS:raise ValueError('Timeline actors only construct, reveal and retire')
        wire=_operation(packet,OPERATIONS[operation]);validate_request(wire)
        reply=self._base.command(name,wire)
        try:response=bytes.fromhex(reply['mesh_packet'])
        except (KeyError,TypeError,ValueError) as error:raise RuntimeError('Malformed timeline actor acknowledgement; not retried') from error
        if len(response)!=len(wire) or response[:8]!=wire[:8] or response[16:24]!=wire[16:24]:
            raise RuntimeError('Timeline actor acknowledgement identity mismatch; not retried')
        error=struct.unpack_from('<I',response,8)[0]
        if operation==120 and error==3769:
            rejected=bytearray(wire);struct.pack_into('<I',rejected,8,error)
            if response!=bytes(rejected):raise RuntimeError('Malformed actor capacity rejection; ownership remains uncertain')
            self._reservation_rejected=True
        return dict(reply,mesh_packet=_operation(response,operation).hex())


class TimelineActorOwner(EnemySpawnOwner):
    def __init__(self,scope):
        super().__init__(scope,_transport=_ActorTransport(scope._session._transport))
    def _command(self,operation,*args,**kwargs):
        try:return super()._command(operation,*args,**kwargs)
        except legacy.EnemyOperationError as error:
            # The exact capacity-rejection acknowledgement proves no slot was
            # reserved. Duplicate tokens and unknown delivery keep ownership.
            if operation==120 and error.native_error==3769 and self._transport._reservation_rejected:
                self._attempted=False
            raise


def validate_count(edits,transport):
    cap=getattr(transport,'timeline_actor_pool_protocol',0)
    if type(cap) is not int or cap not in (0,1):raise RuntimeError('Invalid timeline actor pool capability')
    limit=32 if cap==1 else 1
    if len(edits)>limit:raise ValueError(f'This runtime supports at most {limit} Blueprint replacements per preview')
