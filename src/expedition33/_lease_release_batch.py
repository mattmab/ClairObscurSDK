"""Bounded explicit native lease releases; never retries uncertain outcomes."""
import struct
from .ownership import LeaseError
HEADER=struct.Struct('<6I');ROW=struct.Struct('<Q2I');CAPACITY=128;SIZE=HEADER.size+CAPACITY*ROW.size
NOT_DISPATCHED,RELEASED,DEFERRED,REJECTED,UNKNOWN=range(5)
def available(transport):
    value=getattr(transport,'lease_release_batch_protocol',0)
    return type(value) is int and value==1

def request(tokens):
    tokens=tuple(tokens)
    if not 1<=len(tokens)<=CAPACITY or len(set(tokens))!=len(tokens) or any(type(t) is not int or not 0<t<2**64 for t in tokens):raise ValueError('Lease batch requires1-128 unique owned tokens')
    data=bytearray(SIZE);HEADER.pack_into(data,0,1,len(tokens),0,0,0,0)
    for i,token in enumerate(tokens):ROW.pack_into(data,HEADER.size+i*ROW.size,token,0,0)
    return bytes(data)
def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Lease batch length')
    version,count,error,completed,active,failed=HEADER.unpack_from(data)
    if version!=1 or not 1<=count<=CAPACITY or error or completed or active or failed:raise ValueError('Lease batch header')
    rows=[ROW.unpack_from(data,HEADER.size+i*ROW.size) for i in range(CAPACITY)]
    if any(row!=(0,0,0) for row in rows[count:]) or any(not t or e or o for t,e,o in rows[:count]) or len({t for t,_,_ in rows[:count]})!=count:raise ValueError('Lease batch rows')
def decode(sent,encoded,*,capacity=8192):
    validate_request(sent)
    if type(capacity) is not int or not 1<=capacity<=8192 or type(encoded) is not str:raise ValueError('Lease batch acknowledgement bound')
    raw=bytes.fromhex(encoded)
    if len(raw)!=SIZE:raise ValueError('Lease batch acknowledgement length')
    version,count,error,completed,active,failed=HEADER.unpack_from(raw);original=HEADER.unpack_from(sent)
    if (version,count)!=original[:2] or completed>count or active>capacity or failed>count or error not in (0,3910,*range(400,412)):raise ValueError('Lease batch acknowledgement header')
    rows=[]
    for i in range(CAPACITY):
        token,effect,outcome=ROW.unpack_from(raw,HEADER.size+i*ROW.size)
        if token!=ROW.unpack_from(sent,HEADER.size+i*ROW.size)[0]:raise ValueError('Lease batch token echo changed')
        if i>=count:
            if token or effect or outcome:raise ValueError('Lease batch trailing data')
        elif i>=completed:
            if effect or outcome:raise ValueError('Lease batch undispatched suffix changed')
        else:
            good=(outcome==RELEASED and effect==0) or (outcome==DEFERRED and effect==407)
            if i==completed-1 and error:
                good=(outcome==UNKNOWN and effect==error==408) or (outcome==REJECTED and effect==error and error not in (0,407,408,3910))
            if not good:raise ValueError('Lease batch per-token acknowledgement')
        if i<count:rows.append((token,effect,outcome))
    if not error:
        if completed!=count or failed:raise ValueError('Lease batch incomplete success')
    elif completed:
        if failed!=completed:raise ValueError('Lease batch failed prefix')
    elif error==3910:
        if failed:raise ValueError('Lease batch malformed-request index')
    elif not failed:raise ValueError('Lease batch admission rejection index')
    return dict(error=error,completed=completed,active=active,failed=failed,rows=tuple(rows))

def release_many(session,leases):
    leases=tuple(leases)
    if getattr(session._transport,'target_exit_code',None) is not None:
        for lease in leases:
            if lease._state!='released':lease._state='target_exited'
        return False # No native acknowledgement exists after process exit.
    session._check()
    if not available(session._transport):
        completed=True
        for lease in leases:completed=lease.release() and completed
        return completed
    pending=[];tokens=set()
    for lease in leases:
        if lease._state=='released':continue
        if lease._state not in ('active','pending_release'):raise LeaseError('Lease batch includes unavailable ownership',outcome=lease._state)
        if lease._session() is not session or lease not in session._leases:raise LeaseError('Lease batch belongs to another session',outcome='not_dispatched')
        if lease._token in tokens:raise LeaseError('Lease batch duplicates ownership',outcome='not_dispatched')
        if any(menu.protects(lease) for menu in getattr(session,'_menus',())):raise LeaseError('Close native menu before releasing leases',outcome='not_dispatched',native_error=403)
        tokens.add(lease._token);pending.append(lease)
    groups=[pending[at:at+CAPACITY] for at in range(0,len(pending),CAPACITY)]
    encoded=[request(lease._token for lease in group) for group in groups] # Pure validation before any revocation/dispatch.
    complete=True
    for group,sent in zip(groups,encoded):
        before=[lease._state for lease in group]
        for lease in group:lease._state='releasing' # No poll may retry an in-flight request.
        try:
            response=session._transport.command('lease-release-batch',sent)
            result=decode(sent,response['lease_release_batch_packet'],capacity=getattr(session._transport,'lease_limit',8192))
        except BaseException as error:
            session._abort_ownership()
            if not isinstance(error,Exception):raise
            raise LeaseError('Lease batch acknowledgement unavailable',outcome='unknown') from error
        for lease,prior,(_,native_error,outcome) in zip(group,before,result['rows']):
            if outcome==RELEASED:
                lease._state='released';session._leases.remove(lease)
            elif outcome==DEFERRED:
                lease._state='pending_release';complete=False
            elif outcome==UNKNOWN:lease._state='unknown'
            elif outcome==REJECTED:lease._state='invalid'
            else:lease._state=prior
        if any(row[2]==UNKNOWN for row in result['rows']):
            session._abort_ownership()
            raise LeaseError('Native lease destructor outcome unknown',outcome='unknown',native_error=408)
        if result['error']:
            raise LeaseError('Native lease batch rejected',outcome='not_dispatched' if not result['completed'] else 'completed',native_error=result['error'])
    return complete
