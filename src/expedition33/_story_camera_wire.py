"""Owned dialogue camera request; not enabled without its native capability."""
import struct
SIZE=20984
IDENTITY=struct.Struct('<iiQ')


def encode(nonce,owner,camera_owner,lease,system,dialogue,npc,camera_npc,setter,handler,*,pose_functions=(),view_functions=()):
    packet=bytearray(SIZE)
    struct.pack_into('<4I4Q',packet,0,3,234,0,0,nonce,owner,camera_owner,lease)
    for i,obj in enumerate((system,dialogue,npc,camera_npc,setter,handler)):
        IDENTITY.pack_into(packet,48+16*i,obj.index,obj.serial,obj.address)
    if pose_functions:
        if len(pose_functions)!=2:raise ValueError('Story camera pose functions')
        for i,obj in enumerate(pose_functions):
            IDENTITY.pack_into(packet,144+16*i,obj.index,obj.serial,obj.address)
    if view_functions:
        if len(view_functions)!=2:raise ValueError('Story camera view functions')
        for i,obj in enumerate(view_functions):
            IDENTITY.pack_into(packet,176+16*i,obj.index,obj.serial,obj.address)
    result=bytes(packet);validate(result);return result


def validate(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Story camera packet size')
    version,op,error,state,nonce,owner,camera_owner,lease=struct.unpack_from('<4I4Q',packet)
    if (version,op,error,state)!=(3,234,0,0) or not all((nonce,owner,camera_owner,lease)):
        raise ValueError('Story camera ownership header')
    for at in range(48,144,16):
        index,serial,address=IDENTITY.unpack_from(packet,at)
        if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:
            raise ValueError('Story camera identity')
    if any(packet[144:176]):
        for at in (144,160):
            index,serial,address=IDENTITY.unpack_from(packet,at)
            if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:
                raise ValueError('Story camera pose identity')
    if any(packet[176:208]):
        for at in (176,192):
            index,serial,address=IDENTITY.unpack_from(packet,at)
            if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:
                raise ValueError('Story camera view identity')
    retire,reserved=struct.unpack_from('<II',packet,208)
    if retire not in (0,1) or reserved or any(packet[216:]):raise ValueError('Story camera retirement/padding')


def retire(packet,nonce):
    """Release a journal only after the native runtime proves its world retired."""
    validate(packet)
    result=bytearray(packet)
    struct.pack_into('<Q',result,16,nonce)
    struct.pack_into('<I',result,208,1)
    result=bytes(result);validate(result);return result
