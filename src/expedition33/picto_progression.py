"""Candidate-only verified level and shared mastery operations."""
import struct
HEADER=struct.Struct('<4I')
IDENTITY=struct.Struct('<iiQ')
TAIL=struct.Struct('<iiiI')
SIZE=112

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Picto packet size')
    version,op,error,outcome=HEADER.unpack_from(data)
    expected,value,observed,reserved=TAIL.unpack_from(data,96)
    if version!=1 or op not in (1,2,3) or error or outcome or observed or reserved:raise ValueError('Picto packet header')
    if not 0<=expected<=(2147483647 if op==2 else 100) or not 0<=value<=100:raise ValueError('Picto value range')
    if op==1 and not (1<=expected<=33 and 1<=value<=33):raise ValueError('Verified level range is 1-33')

def change(scope,op,target,function,source,panel,game_instance,expected,value):
    scope._check()
    if getattr(scope._session._transport,'picto_progression_protocol',0)!=1:raise RuntimeError('Picto progression candidate unavailable')
    if op==3 and getattr(scope._session._transport,'picto_cost_protocol',0)!=1:raise RuntimeError('Picto cost candidate unavailable')
    def identity(obj):return IDENTITY.pack(obj.index,obj.serial,obj.address) if obj else bytes(16)
    data=HEADER.pack(1,op,0,0)+b''.join(identity(o) for o in (target,function,source,panel,game_instance))+TAIL.pack(expected,value,0,0)
    validate_request(data)
    # One send only; never retry an ambiguous mutation.
    reply=scope._session._transport.command('picto-progression',data)
    result=bytes.fromhex(reply['picto_progression_packet'])
    if len(result)!=SIZE or result[:8]!=data[:8] or result[16:104]!=data[16:104] or result[108:]!=data[108:]:
        raise RuntimeError('Picto mutation acknowledgement mismatch; outcome unknown')
    _,_,error,outcome=HEADER.unpack_from(result)
    if error or outcome!=1:raise RuntimeError(f'Picto mutation rejected/partial: error={error}, outcome={outcome}; inspect before retrying')
    return TAIL.unpack_from(result,96)[2]
