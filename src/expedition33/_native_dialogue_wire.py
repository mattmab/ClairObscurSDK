"""Bounded copied text for original dialogue line and choice entry points.

No native pointers to strings or arrays cross the process boundary. Dispatch is
not enabled until the native dialogue capability is advertised by the runtime.
"""
import struct
from ._string_wire import encode_units
SIZE=20984
OPERATION=229
CAPACITY=16
UNITS=8192
IDENTITY=struct.Struct('<iiQ')
STARTS=112
LENGTHS=176
TEXT=240
TAIL=16624


def encode(owner,lease,system,dialogue,function,texts,*,speaker=None,finish=False):
    if type(finish) is not bool or finish and (texts or speaker is not None):raise ValueError('Native dialogue end has no text or speaker')
    if type(texts) not in (list,tuple) or (len(texts)!=0 if finish else not 1<=len(texts)<=CAPACITY):
        raise ValueError('Native dialogue requires 1–16 text entries')
    packet=bytearray(SIZE);mode=2 if finish else int(speaker is None)
    struct.pack_into('<4IQ',packet,0,3,OPERATION,0,0,owner)
    for at,obj in ((24,system),(40,dialogue),(56,function)):
        IDENTITY.pack_into(packet,at,obj.index,obj.serial,obj.address)
    if speaker is not None:IDENTITY.pack_into(packet,72,speaker.index,speaker.serial,speaker.address)
    struct.pack_into('<QII',packet,88,lease,mode,len(texts))
    end=0
    for index,text in enumerate(texts):
        encoded=encode_units(text);count=len(encoded)//2
        if end+count>UNITS:raise ValueError('Native dialogue text exceeds packet capacity')
        struct.pack_into('<I',packet,STARTS+4*index,end)
        struct.pack_into('<I',packet,LENGTHS+4*index,count)
        packet[TEXT+2*end:TEXT+2*(end+count)]=encoded;end+=count
    struct.pack_into('<I',packet,104,end)
    result=bytes(packet);validate_request(result);return result


def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Native dialogue packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',packet)
    lease,mode,count,used,reserved=struct.unpack_from('<Q4I',packet,88)
    if (version,op,error,state)!=(3,OPERATION,0,0) or not owner or not lease or mode not in (0,1,2) or not 0<=count<=CAPACITY or not 0<=used<=UNITS or reserved:
        raise ValueError('Native dialogue packet header')
    if (mode==2 and (count or used)) or (mode!=2 and (not count or not used)):
        raise ValueError('Native dialogue text count differs from its mode')
    for at in ((24,40,56,72) if mode==0 else (24,40,56)):
        index,serial,address=IDENTITY.unpack_from(packet,at)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address&7:raise ValueError('Native dialogue identity')
    if mode and any(packet[72:88]):raise ValueError('Native choice packet must not supply a speaker')
    end=0
    for index in range(CAPACITY):
        start=struct.unpack_from('<I',packet,STARTS+4*index)[0]
        length=struct.unpack_from('<I',packet,LENGTHS+4*index)[0]
        if index>=count:
            if start or length:raise ValueError('Native dialogue unused text slot')
            continue
        if start!=end or not 1<=length<=4096 or end+length>used:raise ValueError('Native dialogue text bounds')
        data=packet[TEXT+2*start:TEXT+2*(start+length)]
        if data[-2:]!=b'\0\0':raise ValueError('Native dialogue text terminator')
        value=data[:-2].decode('utf-16-le')
        if '\0' in value:raise ValueError('Native dialogue embedded NUL')
        end+=length
    if end!=used or any(packet[TEXT+2*end:]):raise ValueError('Native dialogue padding')
