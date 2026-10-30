"""Retained sequence-proxy query; returns copied IDs, never actor handles.

The native frame constructs the exact shipping MovieSceneBindingProxy from a
retained sequence and GUID. It never serializes an arbitrary pointer-bearing
struct. A result is not proof that a replacement actor is bound.
"""
import secrets,struct
from .invocation import InvocationError
from ._pod_values import BINDING_ID,GUID,encode as encode_value,decode as decode_value
from .catalog import capture_matching
from ._reader import shared_operation

SIZE=20984
HEADER=struct.Struct('<4I2Q')
IDENTITY=struct.Struct('<iiQ')


def encode(objects,tokens,guid):
    if len(objects)!=5 or len(tokens)!=5:raise ValueError('Exact portable binding inputs required')
    if any(type(token) is not int or not 0<token<2**64 for token in tokens):raise ValueError('Exact nonzero portable input lease tokens required')
    data=bytearray(SIZE);HEADER.pack_into(data,0,3,222,0,0,secrets.randbits(64) or 1,0)
    for index,obj in enumerate(objects):
        if any(type(v) is not int for v in (obj.index,obj.serial,obj.address)):raise ValueError('Exact portable input identity integers required')
        IDENTITY.pack_into(data,32+index*16,obj.index,obj.serial,obj.address)
    struct.pack_into('<5Q',data,112,*tokens);data[152:168]=encode_value(GUID,guid)
    result=bytes(data);validate_request(result);return result


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Portable binding packet size')
    version,op,error,state,request,reserved=HEADER.unpack_from(data)
    if (version,op,error,state,reserved)!=(3,222,0,0,0) or not request or any(data[168:]):
        raise ValueError('Portable binding packet header/padding')
    for at in range(32,112,16):
        index,serial,address=IDENTITY.unpack_from(data,at)
        if index<0 or serial<=0 or address<0x10000 or address%8:raise ValueError('Stable portable binding input identity required')
    if not all(struct.unpack_from('<5Q',data,112)) or not any(data[152:168]):raise ValueError('Retained sequences and nonempty GUID required')


def decode(request,response):
    validate_request(request)
    if (type(response) is not bytes or len(response)!=SIZE or response[:8]!=request[:8] or
            response[16:168]!=request[16:168] or any(response[196:])):
        raise ValueError('Portable binding acknowledgement correlation')
    error,state=struct.unpack_from('<2I',response,8);outcome=struct.unpack_from('<I',response,192)[0]
    if (error,state,outcome)==(3760,0,0) and not any(response[168:192]):
        raise InvocationError('Portable binding query rejected before dispatch',outcome='not_dispatched',native_error=error)
    if (error,state,outcome)==(3763,2,2) and not any(response[168:192]):
        raise InvocationError('Portable binding query outcome unknown',outcome='unknown',native_error=error)
    if error or (state,outcome)!=(1,1):raise ValueError('Portable binding query outcome mismatch')
    if not any(response[168:184]):return None
    if response[168:184]!=request[152:168]:raise ValueError('Portable binding query changed the GUID')
    return decode_value(BINDING_ID,response[168:192])


def _hold(scope,obj):
    from ._stable_lease import acquire_stable
    held=getattr(scope,'_portable_binding_inputs',None)
    if held is None:held=scope._portable_binding_inputs={}
    key=(obj.index,obj.serial,obj.address);lease=held.get(key)
    if lease is None or not lease.active:
        lease,_=acquire_stable(scope,obj);held[key]=lease
        held[(lease.object.index,lease.object.serial,lease.object.address)]=lease
    return lease


def resolve(scope,root,source,guid,*,destination=None):
    """Ask the shipping engine to resolve a source GUID into destination space.

    Caller must select the actual source sequence under the playback root; a
    private duplicate may contain different nested sequence objects. An absent
    result remains unavailable, with no fabricated root ID or retry fallback.
    """
    scope._check();transport=scope._session._transport
    capability=getattr(transport,'sequence_portable_binding_protocol',0)
    if type(capability) is not int or capability!=1:raise RuntimeError('Native portable binding query required')
    encoded=encode_value(GUID,guid)
    if not any(encoded):raise ValueError('Nonempty authored binding GUID required')
    with shared_operation(scope.pid,_executable=transport._executable):
        metadata=getattr(scope,'_portable_binding_metadata',None)
        if metadata is None:
            catalog=capture_matching(scope.pid,names=('MovieSceneSequenceExtensions','Default__MovieSceneSequenceExtensions','GetPortableBindingID'))
            metadata=tuple(_hold(scope,catalog.find_path(path)) for path in (
                '/Script/SequencerScripting.Default__MovieSceneSequenceExtensions',
                '/Script/SequencerScripting.MovieSceneSequenceExtensions:GetPortableBindingID'))
            scope._portable_binding_metadata=metadata
        if any(lease.active is not True for lease in metadata):raise RuntimeError('Portable binding metadata lease is inactive')
        # Only retained identities are reused. The native frame still verifies
        # current identities and the full function/proxy/result schema per call.
        leases=(*metadata,*(_hold(scope,obj) for obj in (root,root if destination is None else destination,source)))
        packet=encode(tuple(lease.object for lease in leases),tuple(lease._token for lease in leases),guid)
        try:
            with scope._lease_context():reply=transport.command('mesh',packet)
            result=decode(packet,bytes.fromhex(reply['mesh_packet']))
        except InvocationError as error:
            if error.outcome!='not_dispatched':scope._session._abort_ownership()
            raise
        except BaseException:
            scope._session._abort_ownership();raise
        if result is None:raise ValueError('Engine could not resolve this binding in the selected sequence hierarchy')
        return result
