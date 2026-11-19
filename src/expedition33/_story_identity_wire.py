"""Fixed, namespaced save identity insertion request; no arbitrary map writes."""
import struct
import uuid
SIZE=20984
OPERATION=231
PREFIX=0xe33c5701
IDENTITY=struct.Struct('<iiQ')


def encode(owner,lease,objects,key,*,insert=False):
    if type(insert) is not bool or type(objects) not in (list,tuple) or len(objects)!=6:
        raise ValueError('Six current context identities required')
    if type(key) is not str or uuid.UUID(key).hex!=key or not key.startswith('e33c5701'):
        raise ValueError('Namespaced story identity required')
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,OPERATION,0,0,owner)
    for index,obj in enumerate(objects):IDENTITY.pack_into(p,24+index*16,obj.index,obj.serial,obj.address)
    words=tuple(int(key[i:i+8],16) for i in range(0,32,8))
    struct.pack_into('<Q6I',p,120,lease,*words,int(insert),0)
    p=bytes(p);validate_request(p);return p


def validate_request(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Story identity packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',p)
    lease,a,b,c,d,mode,reserved=struct.unpack_from('<Q6I',p,120)
    if (version,op,error,state)!=(3,OPERATION,0,0) or not owner or not lease or a!=PREFIX or mode>1 or reserved or any(p[152:]):
        raise ValueError('Story identity packet header or padding')
    for at in range(24,120,16):
        index,serial,address=IDENTITY.unpack_from(p,at)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address&7:
            raise ValueError('Story identity context')
