"""Copied ambient-dialogue inputs and correlated native playback receipts."""
import math,struct
from ._text_wire import encode_units

SIZE=20984;OP=235;CAPACITY=16;UNITS=8192;LINES=192;LINE_SIZE=184;TEXT=3136
IDENTITY=struct.Struct('<iiQ')
NAMES=('carrier','asset','system','play','query','interrupt','finished','widget_interrupt')

class InWorldError(RuntimeError):
    def __init__(self,error):
        super().__init__('In-world dialogue native error '+str(error)+'; retain owner, do not replay dispatch')
        self.native_error=error

def identity(packet,offset,obj):
    if obj is None:return
    IDENTITY.pack_into(packet,offset,obj.index,obj.serial,obj.address)

def encode(owner,ticket,asset_lease,system_lease,objects,*,mode=0,lines=()):
    p=bytearray(SIZE);struct.pack_into('<4I4Q',p,0,3,OP,0,0,owner,ticket,asset_lease,system_lease)
    for i,key in enumerate(NAMES):identity(p,48+16*i,objects[key])
    used=0
    for i,line in enumerate(lines):
        if i>=CAPACITY:raise ValueError('At most sixteen ambient lines')
        text=encode_units(line['text']);count=len(text)//2
        if used+count>UNITS:raise ValueError('Ambient text capacity exceeded')
        at=LINES+i*LINE_SIZE
        flags=int(line.get('use_sound_duration',False))|int(line.get('portrait_on_right',False))<<1
        struct.pack_into('<6I2d',p,at,line.get('character',0),line.get('emotion',0),flags,used,count,0,line['delay_to_delete'],line['delay_to_answer'])
        for j,key in enumerate(('dialogue_wave','sound','sound_table')):identity(p,at+40+16*j,line.get(key))
        name=line.get('sound_row') or ''
        if type(name) is not str or len(name)>95:raise ValueError('Existing sound-event row name required')
        row=name.encode('ascii');p[at+88:at+88+len(row)]=row
        p[TEXT+used*2:TEXT+(used+count)*2]=text;used+=count
    struct.pack_into('<4I',p,176,mode,len(lines),used,0)
    result=bytes(p);validate(result);return result

def validate(p):
    if type(p) is not bytes or len(p)!=SIZE:raise ValueError('Ambient packet size')
    version,op,error,state,owner,ticket,asset_lease,system_lease=struct.unpack_from('<4I4Q',p)
    if (version,op,error,state)!=(3,OP,0,0) or not all((owner,ticket,asset_lease,system_lease)):raise ValueError('Ambient packet header')
    def check_id(at,optional=False):
        i,s,a=IDENTITY.unpack_from(p,at)
        if optional and (i,s,a)==(0,0,0):return
        if i<0 or s<=0 or not 0x10000<=a<=0x7fffffffffff or a&7:raise ValueError('Ambient object identity')
    for at in range(48,176,16):check_id(at)
    mode,count,used,reserved=struct.unpack_from('<4I',p,176)
    if mode>4 or count>CAPACITY or used>UNITS or reserved or (not count or not used if mode==0 else count or used):raise ValueError('Ambient operation bounds')
    end=0
    for i in range(CAPACITY):
        at=LINES+i*LINE_SIZE
        if i>=count:
            if any(p[at:at+LINE_SIZE]):raise ValueError('Unused ambient line data')
            continue
        character,emotion,flags,start,length,reserve,delete,answer=struct.unpack_from('<6I2d',p,at)
        if character not in (0,9) or emotion or flags>3 or reserve or start!=end or not 1<=length<=4096 or length>used-end or any(not math.isfinite(v) or not 0<=v<=120 for v in (delete,answer)):raise ValueError('Ambient line bounds')
        text=p[TEXT+start*2:TEXT+(start+length)*2]
        try:value=text[:-2].decode('utf-16-le')
        except UnicodeError:raise ValueError('Ambient text Unicode') from None
        if text[-2:]!=b'\0\0' or '\0' in value:raise ValueError('Ambient text terminator')
        for pos in (at+40,at+56,at+72):check_id(pos,True)
        row=p[at+88:at+184];name,sep,padding=row.partition(b'\0')
        if not sep or any(padding) or any(c<32 or c>126 for c in name):raise ValueError('Ambient sound row')
        end+=length
    if end!=used or any(p[TEXT+used*2:]):raise ValueError('Ambient trailing data')

def decode(request,response):
    validate(request)
    if type(response) is not bytes or len(response)!=SIZE or response[:8]!=request[:8] or response[16:]!=request[16:]:raise RuntimeError('Ambient receipt identity changed; retain native owner')
    error,state=struct.unpack_from('<II',response,8)
    if error:raise InWorldError(error)
    if state not in (1,2,3,4,5):raise RuntimeError('Ambient operation was not acknowledged')
    return ('unused','playing','completed','not_played','interrupted','world_retired')[state]
