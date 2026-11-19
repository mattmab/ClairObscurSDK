"""Configuration of a retained, originally constructed story NPC only."""
import struct
SIZE=20984
IDENTITY=struct.Struct('<iiQ')


def encode(owner,npc,dialogue_class,speaker,system_cdo,definitions,*,activate=False):
    if type(activate) is not bool:raise ValueError('Expected activation flag')
    if len(definitions)!=4:raise ValueError('Four exact NPC configuration functions required')
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,230,0,0,owner)
    for index,obj in enumerate((npc,dialogue_class,speaker,system_cdo,*definitions)):
        IDENTITY.pack_into(packet,24+16*index,obj.index,obj.serial,obj.address)
    struct.pack_into('<I',packet,152,int(activate))
    result=bytes(packet);validate_request(result);return result


def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Story NPC packet size')
    header=struct.unpack_from('<4IQ',packet)
    if header[:4]!=(3,230,0,0) or not header[4] or struct.unpack_from('<I',packet,152)[0]>1:
        raise ValueError('Story NPC packet header')
    for at in range(24,152,16):
        index,serial,address=IDENTITY.unpack_from(packet,at)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address&7:raise ValueError('Story NPC identity')
    if any(packet[156:]):raise ValueError('Story NPC padding')
