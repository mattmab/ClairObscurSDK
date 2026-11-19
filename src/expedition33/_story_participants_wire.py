"""Owned native dialogue participant registration and cleanup packets."""
import struct
SIZE=20984
CAPACITY=256
IDENTITY=struct.Struct('<iiQ')
RECORD=struct.Struct('<QQiiQ')

def encode(nonce,lease,system,dialogue,update,participants,*,remove=False):
    if type(remove) is not bool or not 1<=len(participants)<=CAPACITY:raise ValueError('Dialogue participant count or mode')
    p=bytearray(SIZE);struct.pack_into('<4IQQ',p,0,3,233,0,0,nonce,lease)
    for i,obj in enumerate((system,dialogue,update)):IDENTITY.pack_into(p,32+16*i,obj.index,obj.serial,obj.address)
    struct.pack_into('<II',p,80,int(remove),len(participants))
    for i,(owner,token,obj) in enumerate(participants):RECORD.pack_into(p,88+32*i,owner,token,obj.index,obj.serial,obj.address)
    result=bytes(p);validate(result);return result

def valid_identity(index,serial,address):
    return index>=0 and serial>0 and 0x10000<=address<=0x7fffffffffff and not address&7

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Participant packet size')
    version,op,error,state,nonce,lease=struct.unpack_from('<4IQQ',p)
    mode,count=struct.unpack_from('<II',p,80)
    if (version,op,error,state)!=(3,233,0,0) or not nonce or not lease or mode>1 or not 1<=count<=CAPACITY:
        raise ValueError('Participant packet header')
    for at in range(32,80,16):
        if not valid_identity(*IDENTITY.unpack_from(p,at)):raise ValueError('Participant context identity')
    owners=set();tokens=set();indices=set();addresses=set()
    for i in range(CAPACITY):
        owner,token,index,serial,address=RECORD.unpack_from(p,88+32*i)
        if i>=count:
            if any((owner,token,index,serial,address)):raise ValueError('Unused participant')
            continue
        if not owner or not token or not valid_identity(index,serial,address) or owner in owners or token in tokens or index in indices or address in addresses:
            raise ValueError('Duplicate or invalid participant ownership')
        owners.add(owner);tokens.add(token);indices.add(index);addresses.add(address)
    if any(p[8280:]):raise ValueError('Participant padding')
