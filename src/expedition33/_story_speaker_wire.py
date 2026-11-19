"""Bounded copied speaker names; never accepts property names or addresses to write."""
import struct
SIZE=20984
CAPACITY=512
IDENTITY=struct.Struct('<iiQ')

def encode(owner,lease,npc,speaker,system_cdo,setter,name):
    if type(name) is not str or not name.strip() or len(name)>160 or '\x00' in name:
        raise ValueError('Expected a nonempty speaker name up to 160 characters')
    try:data=name.encode('utf-16-le')+b'\0\0'
    except UnicodeEncodeError:raise ValueError('Invalid speaker name Unicode') from None
    p=bytearray(SIZE);struct.pack_into('<4IQQ',p,0,3,232,0,0,owner,lease)
    for i,obj in enumerate((npc,speaker,system_cdo,setter)):
        IDENTITY.pack_into(p,32+i*16,obj.index,obj.serial,obj.address)
    struct.pack_into('<I',p,96,len(data)//2);p[100:100+len(data)]=data
    result=bytes(p);validate(result);return result

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Speaker packet size')
    version,op,error,state,owner,lease=struct.unpack_from('<4IQQ',p)
    if (version,op,error,state)!=(3,232,0,0) or not owner or not lease:raise ValueError('Speaker packet header')
    for at in range(32,96,16):
        index,serial,address=IDENTITY.unpack_from(p,at)
        if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:raise ValueError('Speaker identity')
    count=struct.unpack_from('<I',p,96)[0]
    if not 2<=count<=CAPACITY:raise ValueError('Speaker name length')
    data=p[100:100+count*2]
    if data[-2:]!=b'\0\0':raise ValueError('Speaker name terminator')
    try:name=data[:-2].decode('utf-16-le')
    except UnicodeDecodeError:raise ValueError('Speaker name Unicode') from None
    if not name.strip() or len(name)>160 or '\x00' in name:raise ValueError('Speaker name')
    if any(p[100+count*2:]):raise ValueError('Speaker packet padding')
