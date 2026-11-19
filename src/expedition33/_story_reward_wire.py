"""Synchronous extensions of observed original flower/Jules inventory calls."""
import re,struct
from ._story_original_wire import SIZE,identity,put_id,guid,OriginalNarrativeError

def encode(owner,gi,system,function,sources,definitions_owner,key,origins,extras,*,mode=0):
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,242,0,0,owner)
    for at,obj in ((24,gi.object),(40,system),(56,function.object),(72,sources[0].object),(88,sources[1].object)):put_id(p,at,obj)
    struct.pack_into('<4Q4IQ4I',p,104,gi._token,function._token,sources[0]._token,sources[1]._token,*guid(key),definitions_owner,mode,0,0,0)
    def name(at,value):
        text=value.encode('ascii')
        if not 0<len(text)<96:raise ValueError('Original reward row name bounds')
        p[at:at+len(text)]=text
    for i in range(2):
        name(176+i*96,origins[i])
        for j,value in enumerate(extras[i]):
            if j>=2:raise ValueError('At most two reference cosmetic rewards')
            name(368+(i*2+j)*96,value)
    result=bytes(p);validate(result);return result

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Original reward packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',p)
    if (version,op,error,state)!=(3,242,0,0) or not owner:raise ValueError('Original reward header')
    for at in (24,40,56,72,88):identity(p,at)
    values=struct.unpack_from('<4Q4IQ4I',p,104)
    if not all(values[:4]) or values[4]!=0xe33c5701 or not values[8] or values[9]>2 or any(values[10:]):raise ValueError('Original reward binding')
    for at in (176,272,368,464,560):
        text,sep,padding=p[at:at+96].partition(b'\0')
        if not sep or any(padding) or re.fullmatch(rb'[A-Za-z0-9_]+',text) is None:raise ValueError('Original reward row')
    if any(p[656:]):raise ValueError('Original reward request padding')

def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Original reward receipt size')
    error,state=struct.unpack_from('<2I',reply,8)
    clean=bytearray(reply);clean[8:16]=sent[8:16];clean[752:784]=sent[752:784]
    if bytes(clean)!=sent:raise RuntimeError('Original reward receipt context changed')
    if error:raise OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,160)[0]+1:raise RuntimeError('Original reward receipt state')
    calls=struct.unpack_from('<2Q',reply,752);grants=struct.unpack_from('<2Q',reply,768)
    if grants[0]!=calls[0]*2 or grants[1]!=calls[1]:raise RuntimeError('Original reward extension readback count')
    return dict(original_calls=calls,verified_extra_grants=grants)
