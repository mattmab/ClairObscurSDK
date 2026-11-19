"""Bounded scalar DataLayerManager calls with correlated ordered receipts."""
import struct
from . import _enum_wire,_invocation_wire
from ._ui_batch import pack_sparse,unpack_sparse

SIZE,LIMIT,HEADER,OP=20984,16,64,264
ID=struct.Struct('<iiQ')

def _identity(value):
    value=tuple(value)
    if len(value)!=3 or any(type(n) is not int for n in value) or value[0]<0 or value[1]<0 or not 0x10000<=value[2]<=0x7fffffffffff or value[2]&7:
        raise ValueError('Exact layer batch identity required')
    return value

def encode(world,controller,requests):
    requests=tuple(requests)
    if not 1<=len(requests)<=LIMIT:raise ValueError('One to sixteen layer operations required')
    body=[]
    for request in requests:
        if type(request) is not bytes or len(request)!=_enum_wire.SIZE or struct.unpack_from('<I',request)[0]!=4:
            raise ValueError('Retained enum layer call required')
        packed=pack_sparse(request);body.extend((struct.pack('<I',len(packed)),packed))
    body=b''.join(body);used=HEADER+len(body)
    if used>SIZE-LIMIT*64:raise ValueError('Layer batch exceeds its bounded envelope')
    output=bytearray(SIZE);struct.pack_into('<4I',output,0,3,OP,0,0)
    ID.pack_into(output,16,*_identity(world));ID.pack_into(output,32,*_identity(controller))
    struct.pack_into('<4I',output,48,len(requests),used,0,0);output[HEADER:used]=body
    result=bytes(output);validate_request(result);return result

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Layer batch packet size')
    if struct.unpack_from('<4I',data)!=(3,OP,0,0) or any(data[56:64]):raise ValueError('Layer batch request header')
    _identity(ID.unpack_from(data,16));_identity(ID.unpack_from(data,32))
    count,used=struct.unpack_from('<2I',data,48)
    if not 1<=count<=LIMIT or not HEADER<=used<=SIZE-LIMIT*64 or any(data[used:]):
        raise ValueError('Layer batch request bounds')
    at=HEADER
    for _ in range(count):
        if used-at<4:raise ValueError('Layer batch item truncated')
        length=struct.unpack_from('<I',data,at)[0];at+=4
        if not length or length>used-at:raise ValueError('Layer batch item bounds')
        request=unpack_sparse(data[at:at+length],_enum_wire.SIZE);at+=length
        h=_invocation_wire.HEADER.unpack_from(request)
        if h[0]!=4 or h[6] not in (2,4) or h[7]!=1 or h[8:]!=(0,0):
            raise ValueError('Layer batch requires untouched scalar enum calls')
    if at!=used:raise ValueError('Layer batch trailing items')

class LayerBatchError(RuntimeError):
    def __init__(self,error,receipts=(),*,unknown=False):
        self.native_error=error;self.receipts=tuple(receipts);self.unknown=unknown
        self.outcome='unknown' if unknown else 'partial' if receipts else 'not_dispatched'
        super().__init__(f'Data-layer batch stopped ({error}, receipts={len(receipts)}, outcome={self.outcome}); no retry')

def decode(sent,requests,encoded):
    data=bytes.fromhex(encoded)
    if len(data)!=SIZE or data[:8]!=sent[:8] or data[16:52]!=sent[16:52] or data[56:64]!=sent[56:64]:
        raise ValueError('Layer batch acknowledgement identity changed')
    error,done=struct.unpack_from('<2I',data,8);used=struct.unpack_from('<I',data,52)[0]
    if not 0<=done<=len(requests) or not HEADER<=used<=SIZE or any(data[used:]) or error not in (0,4330,4331,4332):
        raise ValueError('Invalid layer batch acknowledgement extent')
    receipts=[];at=HEADER
    for request in requests[:done]:
        if used-at<4:raise ValueError('Layer receipt truncated')
        length=struct.unpack_from('<I',data,at)[0];at+=4
        if not length or length>used-at:raise ValueError('Layer receipt extent changed')
        raw=unpack_sparse(data[at:at+length],_enum_wire.SIZE);at+=length
        reply,tokens=_enum_wire.decode_reply(request,raw.hex())
        expected=(_invocation_wire.OBJECT.unpack_from(request,_invocation_wire.OBJECTS_AT),)
        if tokens or reply.outcome=='dispatch_returned' and reply.objects!=expected:
            raise ValueError('Layer batch returned changed input or object ownership')
        receipts.append(reply)
    if at!=used or not error and done!=len(requests) or error==4330 and done:
        raise ValueError('Layer batch acknowledgement prefix changed')
    if error:
        raise LayerBatchError(error,receipts,unknown=error==4332 or any(r.outcome=='unknown' for r in receipts))
    if any(r.error or r.outcome!='dispatch_returned' for r in receipts):
        raise ValueError('Layer batch reported success without successful receipts')
    return tuple(receipts)
