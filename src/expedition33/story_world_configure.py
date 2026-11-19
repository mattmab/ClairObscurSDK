"""Batch only the original one-shot setters for an already owned world actor."""
import struct
from . import _story_world_configure_wire as wire

def available(scope):
    transport=getattr(getattr(scope,'_session',None),'_transport',None)
    value=getattr(transport,'story_world_configure_protocol',0)
    pool=getattr(transport,'timeline_actor_pool_protocol',0)
    return type(value) is int and value==1 and type(pool) is int and pool==1

def construction_context(actor):
    """Copy construction selectors from its acknowledged owned transaction.

    These do not authorize configuration: native ownership, current pawn,
    controller/viewport/World and component links are checked again at dispatch.
    """
    owner=actor.owner;data=owner.last_response
    if owner.last_operation!=120 or owner.phase!='spawned' or actor.state!='prepared' or type(data) is not bytes or len(data)!=20984:
        raise RuntimeError('Fresh acknowledged world actor construction required')
    if struct.unpack_from('<II',data)!=(3,120) or struct.unpack_from('<I',data,8)[0] or struct.unpack_from('<Q',data,16)[0]!=owner._owner:
        raise RuntimeError('World actor construction receipt changed')
    if struct.unpack_from('<iiQ',data,4096)!=actor.identity:raise RuntimeError('World actor receipt identity changed')
    pc=wire.identity(struct.unpack_from('<iiQ',data,88));world=wire.identity(struct.unpack_from('<iiQ',data,120))
    token=getattr(actor.scope,'_world_binding_token',None)
    if token is None or token[0]!=(actor.scope.pid,*world):raise RuntimeError('World actor configuration differs from scope admission')
    return world,pc

def execute(element,kind,root,mesh,mobility,calls):
    actor=element.actor;scope=actor.scope;scope._check();calls=tuple(calls)
    if not available(scope):raise RuntimeError('Owned world configuration batch capability required')
    if getattr(element,'_configuration_attempted',False):raise RuntimeError('World configuration is never replayed')
    world,pc=construction_context(actor)
    expected=['/Script/Engine.SceneComponent:SetMobility','/Script/Engine.Actor:SetActorScale3D']
    if kind=='wall':
        if len(calls)==7:expected.append('/Script/Engine.SceneComponent:SetRelativeScale3D')
        expected.append('/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier.BP_InvisibleWall_NavModifier_C:SetInvisibleWallEnabled')
    elif kind=='portal':expected.append('/Script/Engine.Actor:SetActorTickEnabled')
    else:raise ValueError('Reviewed wall or portal required')
    expected+=['/Script/Engine.Actor:SetActorEnableCollision','/Script/Engine.Actor:SetActorHiddenInGame','/Script/Engine.SceneComponent:SetMobility']
    if len(calls)!=len(expected):raise ValueError('Complete ordered world setup required')
    requests=[]
    for call,path in zip(calls,expected):
        planner,session=call._check();plan=call._plan
        if session is not scope._session or planner._scope() is not scope or planner._catalog.path_name(plan.function)!=path:
            raise ValueError('World setup plan scope or original function changed')
        requests.append(wire.encode_plan(plan))
    ident=lambda obj:None if obj is None else (obj.index,obj.serial,obj.address)
    sent=wire.encode(actor.owner._owner,kind,world,pc,actor.identity,ident(root),ident(mesh),mobility,requests)
    element._configuration_attempted=True;element._configuration_receipts=()
    try:
        with scope._lease_context():response=scope._session._transport.command('mesh',sent)
        receipts=wire.decode(sent,requests,response['mesh_packet'])
    except wire.WorldConfigurationError as error:
        element._configuration_receipts=error.receipts;element.state='unknown' if error.unknown else 'failed';raise
    except BaseException as error:
        element.state='unknown';raise wire.WorldConfigurationError(4352,unknown=True) from error
    element._configuration_receipts=receipts
    return True
