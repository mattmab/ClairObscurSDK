"""Bounded native retention policy and per-owner session accounting."""
import struct

HEADER=struct.Struct('<10IQ')
OWNER=struct.Struct('<QII')
SIZE=HEADER.size+64*OWNER.size
MAXIMUM=4096

class LeasePolicyRejected(RuntimeError):
    """A verified non-mutating policy rejection; existing ownership is intact."""
    pass

def request(operation,limit=0,quota=0,reserve=0):
    if operation not in (1,2) or any(type(x) is not int for x in (limit,quota,reserve)):
        raise ValueError('Lease policy request')
    if operation==1:
        if not 128<=limit<=MAXIMUM or not 1<=quota<=limit or not 0<=reserve<limit:
            raise ValueError('Lease limits out of bounds')
    elif limit or quota or reserve:raise ValueError('Status takes no limits')
    return HEADER.pack(1,operation,limit,quota,reserve,0,0,0,0,0,0)+bytes(64*OWNER.size)

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Lease policy packet size')
    values=HEADER.unpack_from(data)
    if values[0]!=1 or any(values[5:]) or any(data[HEADER.size:]) or request(*values[1:5])!=data:
        raise ValueError('Lease policy packet fields')

def decode(sent,data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Lease policy reply size')
    v,op,limit,quota,reserve,error,active,peak,capacity,count,memory=HEADER.unpack_from(data)
    if (v,op)!=HEADER.unpack_from(sent)[:2] or error or not 128<=limit<=MAXIMUM or not 1<=quota<=limit or not 0<=reserve<limit:
        raise ValueError(f'Lease policy rejected or invalid ({error})')
    if not 0<=active<=limit or not active<=peak<=MAXIMUM or not 128<=capacity<=MAXIMUM or active>capacity or not 0<=count<=64:
        raise ValueError('Inconsistent lease usage')
    if not 0<memory<2**24 or any(data[HEADER.size+count*OWNER.size:]):raise ValueError('Lease accounting bounds')
    owners=[dict(zip(('owner','active','peak'),OWNER.unpack_from(data,HEADER.size+i*OWNER.size))) for i in range(count)]
    if len({row['owner'] for row in owners})!=count or sum(row['active'] for row in owners)!=active or any(not 0<=row['active']<=row['peak']<=MAXIMUM for row in owners):
        raise ValueError('Inconsistent owner accounting')
    return dict(limit=limit,quota=quota,reserve=reserve,active=active,peak=peak,capacity=capacity,storage_bytes=memory,owners=owners)

def _send(session,operation,limit=0,quota=0,reserve=0):
    session._check();transport=session._transport
    if getattr(transport,'lease_policy_protocol',0)!=1:raise RuntimeError('Runtime has no growing lease policy')
    packet=request(operation,limit,quota,reserve)
    response=transport.command('lease-policy',packet)
    try:
        data=bytes.fromhex(response['lease_policy_packet'])
        # Native configure returns before mutation when busy/unauthorized. Only
        # accept that exact unchanged request plus error=403 as a known failure.
        rejected=bytearray(packet)
        struct.pack_into('<I',rejected,20,403)
        if operation==1 and data==bytes(rejected):
            raise LeasePolicyRejected('Lease policy requires an empty runtime-owned session')
        result=decode(packet,data)
    except (ValueError,KeyError):
        session._abort_ownership();raise
    transport.lease_limit=result['limit']
    labels=getattr(session,'_lease_owner_labels',{})
    for row in result['owners']:row['name']=labels.get(row['owner'],'runtime' if row['owner']==0 else 'unknown')
    return result

def configure(session,*,hard_limit=1024,owner_quota=256,cleanup_reserve=64):
    """Configure an empty session before enabling mods; limits are hard bounds."""
    return _send(session,1,hard_limit,owner_quota,cleanup_reserve)

def statistics(session):return _send(session,2)

def owner_id(session,name):
    if not isinstance(name,str) or not name or len(name)>128:raise ValueError('Lease owner label')
    mapping=getattr(session,'_lease_owner_ids',None)
    if mapping is None:
        session._lease_owner_ids=mapping={};session._lease_owner_labels={}
    if name not in mapping:
        if len(mapping)>=63:raise RuntimeError('Lease subsystem limit reached')
        value=len(mapping)+1;mapping[name]=value;session._lease_owner_labels[value]=name
    return mapping[name]
