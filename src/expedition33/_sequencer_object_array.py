"""Retained, bounded Sequencer Scripting channel and single-key returns."""
import secrets,struct,weakref
from .catalog import capture_matching,capture_selected
from .ownership import ObjectLease
from .invocation import InvocationError

SIZE=20984
HEADER=struct.Struct('<4IQ2I')
IDENTITY=struct.Struct('<iiQ')
ROW=struct.Struct('<iiQQ')
CHANNELS=('MovieSceneScriptingBoolChannel','MovieSceneScriptingByteChannel',
          'MovieSceneScriptingDoubleChannel','MovieSceneScriptingFloatChannel','MovieSceneScriptingIntegerChannel')


def _identity(value):
    if (value.index<0 or value.serial<=0 or value.address<0x10000 or value.address%8):
        raise ValueError('Stable current sequencer query identity required')
    return value.index,value.serial,value.address


def encode(mode,index,target,function,subject,token):
    packet=bytearray(SIZE)
    HEADER.pack_into(packet,0,3,220,0,0,secrets.randbits(64) or 1,mode,index)
    for at,obj in ((32,target),(48,function),(64,subject)):IDENTITY.pack_into(packet,at,*_identity(obj))
    struct.pack_into('<Q',packet,80,token)
    result=bytes(packet);validate_request(result);return result


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Sequencer object-array packet size')
    version,operation,error,state,request,mode,index=HEADER.unpack_from(data)
    if (version!=3 or operation!=220 or error or state or not request or mode not in (1,2) or
            (index!=0 if mode==1 else index>=65536) or not struct.unpack_from('<Q',data,80)[0] or any(data[88:])):
        raise ValueError('Sequencer object-array request header/padding')
    for at in (32,48,64):
        i,s,p=IDENTITY.unpack_from(data,at)
        if i<0 or s<=0 or p<0x10000 or p%8:raise ValueError('Stable sequencer identity required')
    if mode==2 and data[32:48]!=data[64:80]:raise ValueError('Key query targets its retained channel')


def decode(request,data):
    validate_request(request)
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Sequencer object-array acknowledgement size')
    if data[:8]!=request[:8] or data[16:88]!=request[16:88] or any(data[3176:]):
        raise ValueError('Sequencer object-array acknowledgement correlation')
    error,state=struct.unpack_from('<2I',data,8);total,count,outcome,reserved=struct.unpack_from('<4I',data,88)
    mode,index=struct.unpack_from('<2I',request,24)
    if reserved or count>128 or total>65536 or any(data[104+count*ROW.size:3176]):
        raise ValueError('Sequencer object-array result bounds/padding')
    if (error,state,outcome)==(3741,0,0) and not total and not count:
        raise InvocationError('Sequencer array query rejected before dispatch',outcome='not_dispatched',native_error=error)
    if (error,state,outcome)==(3743,2,2):raise InvocationError('Sequencer array query outcome unknown',outcome='unknown',native_error=error)
    if (error,state,outcome)==(3744,1,1) and not count and (total>128 if mode==1 else index>=total):
        raise IndexError('Sequencer returned no requested channel/key within the query bound')
    if error or state!=1 or outcome!=1 or count!=(total if mode==1 else 1) or (mode==2 and index>=total):
        raise ValueError('Inconsistent sequencer object-array result')
    rows=[];tokens=set();objects=set()
    for i in range(count):
        row=ROW.unpack_from(data,104+i*ROW.size);idx,serial,address,token=row
        if idx<0 or serial<=0 or address<0x10000 or address%8 or not token or token in tokens or address in objects:
            raise ValueError('Invalid/aliased sequencer returned lease')
        tokens.add(token);objects.add(address);rows.append(row)
    return tuple(rows),total


def _hold(scope,obj):
    cache=getattr(scope,'_sequencer_array_inputs',None)
    if cache is None:cache=scope._sequencer_array_inputs={}
    key=(obj.index,obj.serial,obj.address)
    lease=cache.get(key)
    if lease is None or not lease.active:
        from ._stable_lease import acquire_stable
        lease,_=acquire_stable(scope,obj);cache[key]=lease
        cache[_identity(lease.object)]=lease
    return lease


def _query(scope,mode,subject,index=0):
    scope._check();session=scope._session;transport=session._transport
    cap=getattr(transport,'sequencer_object_array_protocol',0)
    if type(cap) is not int or cap!=1:raise RuntimeError('Native Sequencer object-array capability required')
    if type(index) is not int or not 0<=index<65536:raise ValueError('Bounded source key ordinal required')
    if mode==2 and subject.class_name not in CHANNELS:raise ValueError('Unsupported numeric/Boolean channel family')
    subject_lease=_hold(scope,subject);subject=subject_lease.object
    fixed=getattr(scope,'_sequencer_array_functions',None)
    if fixed is None:fixed=scope._sequencer_array_functions={}
    owner='MovieSceneSectionExtensions' if mode==1 else subject.class_name
    if owner not in fixed:
        name='GetAllChannels' if mode==1 else 'GetKeys'
        catalog=capture_matching(scope.pid,names=(owner,'Default__'+owner,name))
        function=_hold(scope,catalog.find_path('/Script/SequencerScripting.'+owner+':'+name)).object
        target=_hold(scope,catalog.find_path('/Script/SequencerScripting.Default__'+owner)).object if mode==1 else None
        fixed[owner]=target,function
    target,function=fixed[owner];target=target if mode==1 else subject
    request=encode(mode,index,target,function,subject,subject_lease._token)
    try:
        with scope._lease_context():reply=transport.command('mesh',request)
        rows,total=decode(request,bytes.fromhex(reply['mesh_packet']))
    except IndexError:raise
    except InvocationError as error:
        if error.outcome!='not_dispatched':session._abort_ownership()
        raise
    except BaseException:
        session._abort_ownership();raise
    acquired=[]
    try:
        if {r[3] for r in rows}&{lease._token for lease in session._leases}:raise ValueError('Sequencer output token aliases existing ownership')
        # Adopt every token before any fallible reader operation.
        for idx,serial,address,token in rows:
            lease=ObjectLease(session,token,None);session._leases.add(lease);acquired.append(lease)
            lease._scope=weakref.ref(scope);scope._leases.append(lease)
        current=capture_selected(scope.pid,tuple(row[:3] for row in rows)) if rows else None
        result=[]
        for row,lease in zip(rows,acquired):
            obj=current.by_index[row[0]]
            if (obj.index,obj.serial,obj.address)!=row[:3]:raise ValueError('Retained sequencer result changed')
            lease._object=obj;result.append(obj)
        return tuple(result),total
    except BaseException:
        # A malformed receipt cannot leave unadopted tokens outside ownership.
        if len(acquired)!=len(rows):session._abort_ownership()
        else:
            for lease in acquired:
                try:lease.release()
                except BaseException:session._abort_ownership();break
        raise


def channels(scope,section):return _query(scope,1,section)[0]


def key(scope,channel,index):
    result,total=_query(scope,2,channel,index)
    return result[0],total
