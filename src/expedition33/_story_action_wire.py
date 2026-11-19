"""Bounded, save-correlated original game-action completion receipts."""
import struct,uuid
SIZE=20984
IDENTITY=struct.Struct('<iiQ')

def encode(owner,function,gi,sources,key,*,mode=0,after=0):
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,236,0,0,owner)
    for at,held in ((24,function),(40,gi)):
        o=held.object;IDENTITY.pack_into(p,at,o.index,o.serial,o.address)
    struct.pack_into('<QQ',p,56,function._token,gi._token)
    if type(key) is not str or uuid.UUID(key).hex!=key:raise ValueError('Canonical playthrough identity required')
    struct.pack_into('<6I',p,72,*(int(key[i:i+8],16) for i in range(0,32,8)),mode,len(sources))
    for i,held in enumerate(sources):
        o=held.object;IDENTITY.pack_into(p,96+i*24,o.index,o.serial,o.address);struct.pack_into('<Q',p,112+i*24,held._token)
    struct.pack_into('<Q',p,288,after)
    p=bytes(p);validate(p);return p

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Story action packet size')
    v,op,error,state,owner=struct.unpack_from('<4IQ',p)
    prefix,_,_,_,mode,count=struct.unpack_from('<6I',p,72)
    if (v,op,error,state)!=(3,236,0,0) or not owner or prefix!=0xe33c5701 or mode>2 or not 1<=count<=8 or any(p[296:]):raise ValueError('Story action header/padding')
    if not all(struct.unpack_from('<QQ',p,56)):raise ValueError('Story action context leases')
    identities=[24,40]+[96+i*24 for i in range(count)]
    for at in identities:
        index,serial,address=IDENTITY.unpack_from(p,at)
        if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:raise ValueError('Story action identity')
    seen=set()
    for i in range(count):
        at=96+i*24;address=IDENTITY.unpack_from(p,at)[2]
        if address in seen or not struct.unpack_from('<Q',p,at+16)[0]:raise ValueError('Story action source leases')
        seen.add(address)
    if any(p[96+count*24:288]):raise ValueError('Unused story action sources')

def decode(sent,reply):
    if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Story action receipt size')
    error,state=struct.unpack_from('<II',reply,8);used=struct.unpack_from('<I',reply,296)[0]
    check=bytearray(reply);check[8:16]=sent[8:16];check[296:300]=sent[296:300];check[304:1328]=sent[304:1328]
    if bytes(check)!=sent or used>32:raise RuntimeError('Story action context changed')
    if error:raise RuntimeError('Story action observer error '+str(error))
    mode=struct.unpack_from('<I',sent,88)[0]
    if state!=mode+1:raise RuntimeError('Story action state acknowledgement')
    count=struct.unpack_from('<I',sent,92)[0];previous=struct.unpack_from('<Q',sent,288)[0];rows=[]
    for i in range(32):
        at=304+i*32;sequence,source,reserved=struct.unpack_from('<QII',reply,at)
        world=IDENTITY.unpack_from(reply,at+16)
        if i>=used:
            if any(reply[at:at+32]):raise RuntimeError('Unused story action receipt')
            continue
        if mode!=1 or sequence<=previous or source>=count or reserved or world[0]<0 or world[1]<=0 or world[2]<0x10000 or world[2]&7:raise RuntimeError('Story action receipt correlation')
        previous=sequence;rows.append(dict(sequence=sequence,source=source,world=world))
    return tuple(rows)
