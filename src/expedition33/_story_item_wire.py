"""Owned additive cosmetic definitions and private SDK asset-name registration."""
import re,struct
from ._story_original_wire import SIZE,ID,identity,put_id,OriginalNarrativeError
from ._text_wire import encode_units

def names(owner,cdo,function,path,*,original=False):
    pattern=r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1(?:_C)?' if original else r'/Game/SDK/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1'
    if type(path) is not str or re.fullmatch(pattern,path) is None:
        raise ValueError('Canonical private SDK asset path required')
    data=encode_units(path)
    if len(data)//2>1024:raise ValueError('SDK asset-name bounds')
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,243 if original else 240,0,0,owner)
    put_id(p,24,cdo.object);put_id(p,40,function.object)
    struct.pack_into('<2Q2I',p,56,cdo._token,function._token,len(data)//2,0)
    p[96:96+len(data)]=data
    result=bytes(p);validate(result);return result

def definitions(owner,target,source,map_class,map_add,package,asset,rows,*,mode=0):
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,241,0,0,owner)
    for i,held in enumerate((target,source,map_class,map_add)):
        put_id(p,24+i*16,held.object);struct.pack_into('<Q',p,88+i*8,held._token)
    struct.pack_into('<2I',p,120,mode,len(rows))
    def ascii(at,value,limit):
        data=value.encode('ascii')
        if not 0<len(data)<limit:raise ValueError('Item definition name bounds')
        p[at:at+len(data)]=data
    ascii(136,package,256);ascii(392,asset,96)
    for i,name in enumerate(rows):
        if i>=16:raise ValueError('At most sixteen additive cosmetic rows')
        ascii(488+i*96,name,96)
    result=bytes(p);validate(result);return result

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Story item packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',p)
    if (version,error,state)!=(3,0,0) or not owner or op not in (240,241,243):raise ValueError('Story item packet header')
    if op in (240,243):
        identity(p,24);identity(p,40)
        a,b,count,reserved=struct.unpack_from('<2Q2I',p,56)
        if not a or not b or reserved or any(p[80:96]) or not 16<=count<=1024 or any(p[96+count*2:]):raise ValueError('SDK resource-name request')
        data=p[96:96+count*2]
        if data[-2:]!=b'\0\0':raise ValueError('SDK resource-name terminator')
        text=data[:-2].decode('utf-16-le')
        pattern=r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1(?:_C)?' if op==243 else r'/Game/SDK/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1'
        if re.fullmatch(pattern,text) is None:raise ValueError('SDK resource-name namespace')
    else:
        for at in (24,40,56,72):identity(p,at)
        if not all(struct.unpack_from('<4Q',p,88)):raise ValueError('Item definition leases')
        mode,count,old,new=struct.unpack_from('<4I',p,120)
        if mode>2 or not 1<=count<=16 or old or new:raise ValueError('Item definition request bounds')
        def ascii(at,length,pattern):
            text,sep,padding=p[at:at+length].partition(b'\0')
            if not sep or any(padding) or re.fullmatch(pattern,text) is None:raise ValueError('Item definition namespace/name')
        ascii(136,256,rb'/Game/SDK/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+')
        ascii(392,96,rb'[A-Za-z0-9_]+')
        for i in range(16):
            if i<count:ascii(488+i*96,96,rb'[A-Za-z0-9_]+')
            elif any(p[488+i*96:488+(i+1)*96]):raise ValueError('Unused cosmetic row')
        if any(p[2024:]):raise ValueError('Item definition padding')

def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Story item acknowledgement size')
    op=struct.unpack_from('<I',sent,4)[0];error,state=struct.unpack_from('<2I',reply,8)
    clean=bytearray(reply);clean[8:16]=sent[8:16]
    clean[80:96] = sent[80:96] if op in (240,243) else clean[80:96]
    if op==241:clean[128:136]=sent[128:136]
    if bytes(clean)!=sent:raise RuntimeError('Story item acknowledgement identity changed')
    if error:raise OriginalNarrativeError(error)
    if op in (240,243):
        values=struct.unpack_from('<2Q',reply,80)
        if state!=1 or not all(values):raise RuntimeError('SDK resource-name acknowledgement')
        return values
    if state!=struct.unpack_from('<I',sent,120)[0]+1:raise RuntimeError('Cosmetic definition acknowledgement')
    old,new=struct.unpack_from('<2I',reply,128)
    if state in (1,2) and (old<1 or new!=old+struct.unpack_from('<I',sent,124)[0]):raise RuntimeError('Cosmetic definition row-count readback')
    return dict(original_rows=old,registered_rows=new)
