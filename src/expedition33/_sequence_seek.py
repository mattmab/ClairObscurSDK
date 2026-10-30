"""Fixed frame-only scrub request for an existing native-owned sequence."""
import math,struct

PACKET=struct.Struct('<IIiiQif8I')
MAGIC=0x53533345


def encode(function,frame,subframe=0.):
    identity=(function.index,function.serial,function.address)
    if (any(type(v) is not int for v in identity) or not 0<=identity[0]<(1<<31) or
            not 0<identity[1]<(1<<31) or not 0<identity[2]<(1<<64)):
        raise ValueError('Fresh sequence seek function identity required')
    if type(frame) is not int or not -(1<<31)<=frame<(1<<31):raise ValueError('Signed seek frame required')
    if type(subframe) not in (int,float) or not math.isfinite(subframe) or not 0<=subframe<1:
        raise ValueError('Seek subframe must be finite and within [0,1)')
    data=PACKET.pack(MAGIC,1,*identity,frame,subframe,*([0]*8))
    validate_request(data)
    return data


def validate_request(data):
    if type(data) is not bytes or len(data)!=64:raise ValueError('Sequence seek packet size')
    magic,version,index,serial,address,frame,subframe,*reserved=PACKET.unpack(data)
    if ((magic,version)!=(MAGIC,1) or index<0 or serial<=0 or not address or
            not math.isfinite(subframe) or not 0<=subframe<1 or any(reserved)):
        raise ValueError('Sequence seek packet fields')


def decode(request,response):
    validate_request(request)
    if type(response) is not bytes or len(response)!=64 or response[:32]!=request[:32] or any(response[36:]):
        raise ValueError('Sequence seek acknowledgement mismatch')
    outcome=PACKET.unpack(response)[7]
    if outcome not in (0,1,2):raise ValueError('Sequence seek outcome')
    return outcome
