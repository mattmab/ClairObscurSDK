"""Exact original layer calls, sharing one game-thread handoff per bounded set."""
from . import _story_layer_batch_wire as wire
from . import _enum_wire
from .invocation import decode_result

def available(scope):
    transport=getattr(getattr(scope,'_session',None),'_transport',None)
    value=getattr(transport,'story_layer_batch_protocol',0)
    return type(value) is int and value==1

def execute(scope,world,controller,calls):
    scope._check();calls=tuple(calls)
    if not available(scope):raise RuntimeError('Native data-layer batch capability required')
    if not 1<=len(calls)<=wire.LIMIT:raise ValueError('Bounded layer calls required')
    entries=[];mode=None;target=None
    for call in calls:
        planner,session=call._check();plan=call._plan
        if session is not scope._session or planner._scope() is not scope:
            raise ValueError('Layer plan belongs to another scope/session')
        path=planner._catalog.path_name(plan.function)
        current={'/Script/Engine.DataLayerManager:GetDataLayerInstanceRuntimeState':'get',
                 '/Script/Engine.DataLayerManager:SetDataLayerInstanceRuntimeState':'set'}.get(path)
        if current is None or mode is not None and current!=mode:
            raise ValueError('Only homogeneous exact data-layer operations can be batched')
        identity=(plan.target.index,plan.target.serial,plan.target.address)
        if target is not None and identity!=target:raise ValueError('One current layer manager required')
        target=identity;mode=current
        entries.append((plan,planner._catalog,_enum_wire.encode_plan(plan)))
    requests=tuple(item[2] for item in entries);sent=wire.encode(world,controller,requests)
    try:
        with scope._lease_context():response=scope._session._transport.command('mesh',sent)
        replies=wire.decode(sent,requests,response['mesh_packet'])
    except wire.LayerBatchError:
        raise
    except BaseException as error:
        raise wire.LayerBatchError(4332,unknown=True) from error
    return tuple(decode_result(plan,reply,catalog).return_value for (plan,catalog,_),reply in zip(entries,replies))
