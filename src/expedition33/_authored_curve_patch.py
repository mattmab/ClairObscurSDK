"""Bounded construction-time edits of private copied numeric sequence channels."""
import math,secrets,struct
from .invocation import InvocationError

SIZE=20984
IDENTITY=struct.Struct('<iiQ')
SELECTOR=struct.Struct('<64sII')
EDIT=struct.Struct('<IiiIQQ')
KINDS={'MovieSceneBoolChannel':1,'MovieSceneByteChannel':2,'MovieSceneIntegerChannel':3,
       'MovieSceneFloatChannel':4,'MovieSceneDoubleChannel':5}


def _bits(kind,value):
    if kind==1:
        if type(value) is not bool:raise ValueError('Boolean channel value required')
        return int(value)
    if kind in (2,3):
        if type(value) is not int or not (0<=value<=255 if kind==2 else -(1<<31)<=value<(1<<31)):
            raise ValueError('Integer channel value is out of range')
        return value&0xffffffff
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite curve value required')
    try:return int.from_bytes(struct.pack('<f' if kind==4 else '<d',value),'little')
    except (OverflowError,struct.error) as error:raise ValueError('Curve value exceeds native precision') from error


def _number(kind,bits):
    if kind==1:return bits<=1
    if kind==2:return bits<=255
    if kind==3:return bits<=0xffffffff
    if kind==4:return bits<=0xffffffff and math.isfinite(struct.unpack('<f',bits.to_bytes(4,'little'))[0])
    return kind==5 and math.isfinite(struct.unpack('<d',bits.to_bytes(8,'little'))[0])


def encode(objects,tokens,signature,kind,path,key_count,edits):
    if kind not in KINDS:raise ValueError('Supported stored channel required')
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,226,0,0,secrets.randbits(64) or 1)
    if len(objects)!=4 or len(tokens)!=4:raise ValueError('Four retained curve inputs required')
    for i,obj in enumerate(objects):IDENTITY.pack_into(packet,24+i*16,obj.index,obj.serial,obj.address)
    if any(type(token) is not int or not 0<token<1<<64 for token in tokens):raise ValueError('Retained curve tokens required')
    if len(signature)!=4 or any(type(value) is not int or not -(1<<31)<=value<(1<<31) for value in signature):raise ValueError('Exact source signature required')
    struct.pack_into('<4Q',packet,88,*tokens);struct.pack_into('<4i',packet,120,*signature)
    selectors=[]
    for item in path:
        if type(item) is str:selectors.append([item,0xffffffff])
        elif type(item) is int and selectors and selectors[-1][1]==0xffffffff:selectors[-1][1]=item
        else:raise ValueError('Invalid channel selector')
    if not 1<=len(selectors)<=16 or type(key_count) is not int or not 1<=key_count<=65536 or not 1<=len(edits)<=64:
        raise ValueError('Bounded channel keys and selectors required')
    struct.pack_into('<4I',packet,136,KINDS[kind],len(selectors),key_count,len(edits))
    for i,(name,element) in enumerate(selectors):
        data=name.encode('ascii')
        if not 1<=len(data)<=63:raise ValueError('Bounded channel field name required')
        if element!=0xffffffff and not 0<=element<64:raise ValueError('Bounded static channel element required')
        SELECTOR.pack_into(packet,160+i*SELECTOR.size,data,element,0)
    for i,edit in enumerate(edits):
        values=(edit['index'],edit['before_time'],edit['after_time'])
        if any(type(value) is not int for value in values):raise ValueError('Integer source key ordinal and times required')
        EDIT.pack_into(packet,1312+i*EDIT.size,*values,0,_bits(KINDS[kind],edit['before']),_bits(KINDS[kind],edit['after']))
    data=bytes(packet);validate_request(data);return data


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Curve edit packet size')
    version,operation,error,state,request=struct.unpack_from('<4IQ',data)
    kind,depth,total,count,outcome,reserved=struct.unpack_from('<6I',data,136)
    if (version!=3 or operation!=226 or error or state or not request or kind not in range(1,6) or
        not 1<=depth<=16 or not 1<=total<=65536 or not 1<=count<=64 or outcome or reserved or
        not any(data[120:136]) or any(data[3360:])):raise ValueError('Curve edit header/padding')
    ids=[]
    for at in range(24,88,16):
        i,s,p=IDENTITY.unpack_from(data,at)
        if i<0 or s<=0 or not 0x10000<=p<=0x7fffffffffff or p%8:raise ValueError('Stable curve input identity required')
        ids.append(p)
    if ids[0]==ids[1] or not all(struct.unpack_from('<4Q',data,88)):raise ValueError('Private target and retained tokens required')
    for i in range(16):
        row=data[160+i*72:160+(i+1)*72]
        if i>=depth:
            if any(row):raise ValueError('Unused curve selector is nonzero')
            continue
        name,element,padding=SELECTOR.unpack(row)
        prefix,separator,tail=name.partition(b'\0')
        if not prefix or not separator or any(tail) or any(not 32<=c<127 for c in prefix) or padding or element!=0xffffffff and element>=64:
            raise ValueError('Invalid curve selector')
    previous=-1
    for i in range(64):
        row=data[1312+i*32:1312+(i+1)*32]
        if i>=count:
            if any(row):raise ValueError('Unused curve edit is nonzero')
            continue
        index,_,_,padding,before,after=EDIT.unpack(row)
        if not previous<index<total or padding or not _number(kind,before) or not _number(kind,after):raise ValueError('Invalid/duplicate curve key edit')
        previous=index


def decode(request,reply):
    validate_request(request)
    if type(reply) is not bytes or len(reply)!=SIZE:raise ValueError('Curve edit acknowledgement size')
    if reply[:8]!=request[:8] or reply[16:152]!=request[16:152] or reply[156:]!=request[156:]:raise ValueError('Curve edit acknowledgement correlation')
    error,state=struct.unpack_from('<2I',reply,8);outcome=struct.unpack_from('<I',reply,152)[0]
    if (error,state,outcome)==(3780,0,0):raise InvocationError('Private curve edit rejected before writing',outcome='not_dispatched',native_error=error)
    if (error,state,outcome)==(3783,2,2):raise InvocationError('Private curve edit outcome unknown; assets retained',outcome='unknown',native_error=error)
    if (error,state,outcome)!=(0,1,1):raise ValueError('Inconsistent curve edit acknowledgement')
    return True


def patch(scope,objects,signature,kind,path,key_count,edits):
    scope._check();session=scope._session;transport=session._transport
    cap=getattr(transport,'authored_curve_patch_protocol',0)
    if type(cap) is not int or cap!=1:raise RuntimeError('Native authored curve editing capability required')
    from ._stable_lease import acquire_stable
    held=[acquire_stable(scope,obj)[0] for obj in objects]
    request=encode([lease.object for lease in held],[lease._token for lease in held],signature,kind,path,key_count,edits)
    try:
        with scope._lease_context():reply=transport.command('mesh',request)
        return decode(request,bytes.fromhex(reply['mesh_packet']))
    except InvocationError as error:
        if error.outcome!='not_dispatched':session._abort_ownership()
        raise
    except BaseException:
        session._abort_ownership();raise
