"""One-shot owned wall/portal configuration with ordered scalar receipts."""
import struct
from . import _invocation_wire as callwire, _retained_wire, _blueprint_wire
from ._ui_batch import pack_sparse,unpack_sparse

SIZE,HEADER,LIMIT,OP=20984,128,7,266
ID=struct.Struct('<iiQ')

def identity(value):
    value=tuple(value)
    if len(value)!=3 or any(type(n) is not int for n in value) or value[0]<0 or value[1]<0 or not 0x10000<=value[2]<=0x7fffffffffff or value[2]&7:
        raise ValueError('Exact world configuration identity required')
    return value

def encode(owner,kind,world,controller,actor,root,mesh,mobility,requests):
    requests=tuple(requests)
    if type(owner) is not int or not 0<owner<2**64 or kind not in ('wall','portal'):
        raise ValueError('Exact owned wall/portal required')
    if type(mobility) is not int or mobility not in (0,1,2):raise ValueError('Observed original mobility required')
    if len(requests) not in ((6,7) if kind=='wall' else (6,)):raise ValueError('Complete world configuration sequence required')
    output=bytearray(SIZE);struct.pack_into('<4IQ4I',output,0,3,OP,0,0,owner,1 if kind=='wall' else 2,len(requests),0,0)
    for offset,value in zip((40,56,72,88),(world,controller,actor,root)):ID.pack_into(output,offset,*identity(value))
    if kind=='wall':ID.pack_into(output,104,*identity(mesh))
    elif mesh is not None:raise ValueError('Portal cannot configure a wall mesh')
    struct.pack_into('<I',output,120,mobility);at=HEADER
    for request in requests:
        if type(request) is not bytes or len(request)!=_retained_wire.SIZE:raise ValueError('Retained setup call required')
        packed=pack_sparse(request)
        if at+4+len(packed)>SIZE-LIMIT*64:raise ValueError('World configuration exceeds bounded envelope')
        struct.pack_into('<I',output,at,len(packed));at+=4;output[at:at+len(packed)]=packed;at+=len(packed)
    struct.pack_into('<I',output,32,at);result=bytes(output);validate_request(result);return result

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('World configuration packet size')
    version,op,error,done,owner,kind,count,used,reserved=struct.unpack_from('<4IQ4I',data)
    if (version,op,error,done)!=(3,OP,0,0) or not owner or kind not in (1,2) or count not in ((6,7) if kind==1 else (6,)) or reserved:
        raise ValueError('World configuration request header')
    for at in (40,56,72,88):identity(ID.unpack_from(data,at))
    if kind==1:identity(ID.unpack_from(data,104))
    elif any(data[104:120]):raise ValueError('Portal mesh identity forbidden')
    if struct.unpack_from('<I',data,120)[0]>2 or any(data[124:128]) or not HEADER<=used<=SIZE-LIMIT*64 or any(data[used:]):
        raise ValueError('World configuration bounds or padding')
    at=HEADER
    for _ in range(count):
        if used-at<4:raise ValueError('Truncated world call')
        length=struct.unpack_from('<I',data,at)[0];at+=4
        if not length or length>used-at:raise ValueError('World call extent')
        raw=unpack_sparse(data[at:at+length],_retained_wire.SIZE);at+=length
        h=callwire.HEADER.unpack_from(raw)
        if h[0] not in (1,2,8) or h[3]!=65535 or h[6]!=1 or h[7:]!=(0,0,0):
            raise ValueError('Only original scalar input-only setup calls allowed')
        if struct.unpack_from('<II',raw,callwire.SIZE)!=(1,0) or any(raw[_retained_wire.LEASES_AT:]):
            raise ValueError('World setup call cannot carry object ownership')
    if at!=used:raise ValueError('World configuration trailing calls')

class WorldConfigurationError(RuntimeError):
    def __init__(self,error,receipts=(),*,unknown=False):
        self.native_error=error;self.receipts=tuple(receipts);self.unknown=unknown
        self.outcome='unknown' if unknown else 'partial' if receipts else 'not_dispatched'
        super().__init__(f'Owned world configuration stopped ({error}, receipts={len(receipts)}, outcome={self.outcome}); no retry')

def decode(sent,requests,encoded):
    data=bytes.fromhex(encoded)
    if len(data)!=SIZE or data[:8]!=sent[:8] or data[16:32]!=sent[16:32] or data[36:HEADER]!=sent[36:HEADER]:
        raise ValueError('World configuration acknowledgement identity changed')
    error,done=struct.unpack_from('<II',data,8);used=struct.unpack_from('<I',data,32)[0]
    if error not in (0,4350,4351,4352) or not 0<=done<=len(requests) or not HEADER<=used<=SIZE or any(data[used:]):
        raise ValueError('World configuration acknowledgement bounds')
    at=HEADER;receipts=[]
    for request in requests[:done]:
        if used-at<4:raise ValueError('World receipt truncated')
        length=struct.unpack_from('<I',data,at)[0];at+=4
        if not length or length>used-at:raise ValueError('World receipt extent')
        raw=unpack_sparse(data[at:at+length],_retained_wire.SIZE);at+=length
        reply,tokens=_retained_wire.decode_reply(request,raw.hex())
        if tokens or reply.objects:raise ValueError('World configuration returned unexpected object ownership')
        receipts.append(reply)
    if at!=used or not error and done!=len(requests) or error==4350 and done:
        raise ValueError('World configuration prefix acknowledgement changed')
    if error:raise WorldConfigurationError(error,receipts,unknown=error==4352 or any(r.outcome=='unknown' for r in receipts))
    if any(r.error or r.outcome!='dispatch_returned' for r in receipts):raise ValueError('World setup success lacks complete receipts')
    return tuple(receipts)

def encode_plan(plan):
    return (_blueprint_wire if plan.wire_version==8 else _retained_wire).encode_plan(plan)
