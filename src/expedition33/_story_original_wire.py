"""Save-scoped original-dialogue rewrites, continuations and ambient overlays."""
import math, struct, uuid
from ._text_wire import encode_units
SIZE=20984
ID=struct.Struct('<iiQ')

class OriginalNarrativeError(RuntimeError):
    def __init__(self,code,reason=None):
        self.code=code
        self.reason=reason
        super().__init__('Original narrative operation rejected ('+str(code)+'); retain owner after uncertain outcomes'+(' [proof '+str(reason)+']' if reason is not None else ''))

def put_id(p,at,obj):
    ID.pack_into(p,at,obj.index,obj.serial,obj.address)

def guid(key):
    if type(key) is not str or uuid.UUID(key).hex!=key or not key.startswith('e33c5701'):
        raise ValueError('Canonical selected-story identity required')
    return tuple(int(key[i:i+8],16) for i in range(0,32,8))

def identity(p,at,optional=False):
    i,s,a=ID.unpack_from(p,at)
    if optional and (i,s,a)==(0,0,0):return
    if i<0 or s<=0 or not 0x10000<=a<=0x7fffffffffff or a&7:raise ValueError('Original narrative identity')

def units(p,start,count,limit):
    if not 1<=count<=4096 or not 0<=start<=limit-count:raise ValueError('Original narrative text bounds')
    text=p[start*2:(start+count)*2]
    value=text[:-2].decode('utf-16-le')
    if text[-2:]!=b'\0\0' or '\0' in value:raise ValueError('Original narrative text terminator')

def common(op,owner,function,gi,source,key,mode):
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,op,0,0,owner)
    for at,held in ((24,function),(40,gi),(56,source)):put_id(p,at,held.object)
    struct.pack_into('<3Q4I',p,72,function._token,gi._token,source._token,*guid(key))
    struct.pack_into('<I',p,112,mode)
    return p

def rewrite(owner,function,gi,source,key,profile,text_cdo,text_query,*,mode=0,texts=(),sound=None,sound_mask=0):
    if sound is None and sound_mask:raise ValueError('Sound replacement requires an owned identity')
    p=common(237,owner,function,gi,source,key,mode)
    struct.pack_into('<3I',p,116,len(texts),profile,0)
    put_id(p,16704,text_cdo.object);put_id(p,16720,text_query.object)
    struct.pack_into('<2Q',p,16736,text_cdo._token,text_query._token)
    if sound is not None:
        put_id(p,16752,sound.object);struct.pack_into('<QI',p,16768,sound._token,sound_mask)
    end=0
    for i,(before,after) in enumerate(texts):
        if i>=8:raise ValueError('At most eight replacement lines per original class')
        starts=[]
        for value in (before,after):
            encoded=encode_units(value);n=len(encoded)//2
            if end+n>8192:raise ValueError('Original narrative text capacity')
            starts.extend((end,n));p[320+end*2:320+(end+n)*2]=encoded;end+=n
        struct.pack_into('<4I',p,192+i*16,*starts)
    result=bytes(p);validate(result);return result

def continuation(owner,function,gi,source,key,*,mode=0,sequence=0):
    p=common(238,owner,function,gi,source,key,mode)
    struct.pack_into('<Q',p,120,sequence);struct.pack_into('<i',p,176,-1)
    result=bytes(p);validate(result);return result

def ambient(owner,asset,gi,world,system,query,key,expected_count,*,mode=0,lines=()):
    p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,239,0,0,owner)
    for at,obj in ((24,asset.object),(40,gi.object),(56,world),(128,system),(144,query)):put_id(p,at,obj)
    struct.pack_into('<3Q4I4I',p,72,asset._token,gi._token,0,*guid(key),mode,len(lines),0,expected_count)
    end=0
    for i,line in enumerate(lines):
        if i>=16:raise ValueError('At most sixteen source ambient lines')
        text=encode_units(line['text']);n=len(text)//2
        if end+n>8192:raise ValueError('Original ambient text capacity')
        at=160+i*184
        flags=int(line.get('use_sound_duration',False))|int(line.get('portrait_on_right',False))<<1
        struct.pack_into('<6I2d',p,at,line['character'],line['emotion'],flags,end,n,0,line['delay_to_delete'],line['delay_to_answer'])
        for offset,name in ((40,'dialogue_wave'),(56,'sound'),(72,'sound_table')):
            if line.get(name) is not None:put_id(p,at+offset,line[name])
        row=(line.get('sound_row') or '').encode('ascii')
        if len(row)>95:raise ValueError('Original sound row bounds')
        p[at+88:at+88+len(row)]=row
        p[3104+end*2:3104+(end+n)*2]=text;end+=n
    struct.pack_into('<I',p,120,end)
    result=bytes(p);validate(result);return result

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Original narrative packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',p)
    if (version,error,state)!=(3,0,0) or not owner or op not in (237,238,239):raise ValueError('Original narrative header')
    if struct.unpack_from('<I',p,96)[0]!=0xe33c5701:raise ValueError('Original narrative save identity')
    for at in (24,40,56):identity(p,at)
    if not all(struct.unpack_from('<2Q',p,72)):raise ValueError('Original narrative context leases')
    mode=struct.unpack_from('<I',p,112)[0]
    if op==237:
        count,profile,reserved=struct.unpack_from('<3I',p,116)
        if mode>2 or profile>=8 or reserved or (count if mode else not 1<=count<=8) or not struct.unpack_from('<Q',p,88)[0] or any(p[128:192]):raise ValueError('Original replacement bounds')
        end=0
        for i in range(8):
            row=struct.unpack_from('<4I',p,192+i*16)
            if i>=count:
                if any(row):raise ValueError('Unused original replacement')
                continue
            for start,n in (row[:2],row[2:]):
                if start!=end:raise ValueError('Original replacement text order')
                units(p[320:16704],start,n,8192);end+=n
        identity(p,16704);identity(p,16720)
        sound_lease,sound_mask,sound_reserved=struct.unpack_from('<QII',p,16768)
        if sound_mask:
            identity(p,16752)
            if not sound_lease or sound_mask>255 or (not mode and sound_mask>>count):raise ValueError('Original replacement sound mask/lease')
        elif any(p[16752:16780]):raise ValueError('Original replacement sound without mask')
        if not all(struct.unpack_from('<2Q',p,16736)) or any(p[320+end*2:16704]) or sound_reserved or any(p[16784:]):raise ValueError('Original replacement padding/query leases')
    elif op==238:
        if mode>4 or any(p[116:120]) or not struct.unpack_from('<Q',p,88)[0] or any(p[128:176]) or struct.unpack_from('<i',p,176)[0]!=-1 or any(p[180:]):raise ValueError('Original continuation padding')
    else:
        count,used,expected=struct.unpack_from('<3I',p,116)
        if mode>2 or expected>16 or count>16 or used>8192 or (count or used if mode else not count or not used) or struct.unpack_from('<Q',p,88)[0]:raise ValueError('Original ambient bounds')
        identity(p,128);identity(p,144);end=0
        for i in range(16):
            at=160+i*184
            if i>=count:
                if any(p[at:at+184]):raise ValueError('Unused original ambient line')
                continue
            character,emotion,flags,start,n,reserved,delete,answer=struct.unpack_from('<6I2d',p,at)
            if character not in (0,1,8,9) or emotion or flags>3 or reserved or start!=end or n>used-end or any(not math.isfinite(x) or not 0<=x<=120 for x in (delete,answer)):raise ValueError('Original ambient line')
            units(p[3104:19488],start,n,8192);end+=n
            for offset in (40,56,72):identity(p,at+offset,True)
            name,sep,padding=p[at+88:at+184].partition(b'\0')
            if not sep or any(padding) or any(c<32 or c>126 for c in name):raise ValueError('Original ambient row')
        if end!=used or any(p[3104+end*2:]):raise ValueError('Original ambient padding')

def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Original narrative reply size')
    op=struct.unpack_from('<I',sent,4)[0];error,state=struct.unpack_from('<2I',reply,8)
    clean=bytearray(reply);clean[8:16]=sent[8:16]
    if op==237:clean[128:192]=sent[128:192]
    if op==238:clean[120:184]=sent[120:184]
    if bytes(clean)!=sent:raise RuntimeError('Original narrative acknowledgement context changed')
    if error:raise OriginalNarrativeError(error,state if state>=100 else None)
    if op==237:
        if state!=struct.unpack_from('<I',sent,112)[0]+1:raise RuntimeError('Original rewrite state')
        return struct.unpack_from('<8Q',reply,128)
    if op==238:
        if state!=struct.unpack_from('<I',sent,112)[0]+1:raise RuntimeError('Original continuation state')
        sequence=struct.unpack_from('<Q',reply,120)[0];choice,pending=struct.unpack_from('<iI',reply,176)
        if pending>2 or (pending and choice not in (0,1)):raise RuntimeError('Original continuation choice')
        return dict(sequence=sequence,pending=pending,choice=choice,system=ID.unpack_from(reply,128),dialogue=ID.unpack_from(reply,144),world=ID.unpack_from(reply,160))
    if state not in (1,2,3):raise RuntimeError('Original ambient state')
    return state
