"""Feature-gated wire format for retained native binding observations.

This diagnostic is not an actor replacement or evidence of animation. The
runtime independently authenticates source occurrence and binding membership;
the wire never contains or supplies a trusted native binding ID.
"""
import struct

MAGIC=0x41423345
SIZE=288
IDENTITY=struct.Struct('<iiQ')

def encode(objects,tokens,guid):
    if len(objects)!=5 or len(tokens)!=5 or len(guid)!=4:raise ValueError('Exact diagnostic inputs required')
    data=bytearray(SIZE);struct.pack_into('<4I',data,0,MAGIC,1,0,0)
    for i,obj in enumerate(objects):
        try:index,serial,address=obj.index,obj.serial,obj.address
        except AttributeError as error:raise ValueError('Exact diagnostic identities required') from error
        if any(type(v) is not int for v in (index,serial,address)) or not 0<=index<2**31 or not 0<serial<2**31 or not 0x10000<=address<2**64 or address%8:
            raise ValueError('Stable diagnostic identity required')
        IDENTITY.pack_into(data,16+i*16,index,serial,address)
    if any(type(t) is not int or not 0<t<2**64 for t in tokens):raise ValueError('Diagnostic input leases required')
    if any(type(g) is not int or not 0<=g<2**32 for g in guid) or not any(guid):raise ValueError('Nonempty diagnostic GUID required')
    struct.pack_into('<5Q4I',data,96,*tokens,*guid)
    result=bytes(data);validate_request(result);return result

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(MAGIC,1,0,0):raise ValueError('Diagnostic request header')
    for offset in range(16,96,16):
        index,serial,address=IDENTITY.unpack_from(data,offset)
        if index<0 or serial<=0 or address<0x10000 or address%8:raise ValueError('Stable diagnostic identity required')
    if not all(struct.unpack_from('<5Q',data,96)) or not any(struct.unpack_from('<4I',data,136)) or any(data[152:]):raise ValueError('Diagnostic input and padding required')

def decode(request,response):
    validate_request(request)
    if type(response) is not bytes or len(response)!=SIZE or response[:12]!=request[:12] or response[16:152]!=request[16:152] or any(response[156:160]):raise ValueError('Diagnostic acknowledgement mismatch')
    outcome=struct.unpack_from('<I',response,12)[0];count=struct.unpack_from('<I',response,152)[0]
    if outcome not in (0,1,2) or count>8 or (outcome!=1 and count):raise ValueError('Diagnostic outcome mismatch')
    objects=tuple(IDENTITY.unpack_from(response,160+i*16) for i in range(count))
    if any(index<0 or serial<=0 or address<0x10000 or address%8 for index,serial,address in objects) or len(set(objects))!=len(objects) or any(response[160+count*16:]):raise ValueError('Diagnostic result identity mismatch')
    return dict(outcome=outcome,objects=objects)
