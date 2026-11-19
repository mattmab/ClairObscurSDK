"""One scalar setting on an existing, native-owned story streaming component."""
import math
import struct

SIZE=20984
HEADER=struct.Struct('<4IQ')
IDENTITY=struct.Struct('<iiQ')


def checked_radius(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 1000<=value<=50000:
        raise ValueError('Story streaming radius must be finite and between 1000 and 50000')
    return struct.unpack('<f',struct.pack('<f',float(value)))[0]


def encode(owner,actor,component,radius):
    packet=bytearray(SIZE);HEADER.pack_into(packet,0,3,263,0,0,owner)
    IDENTITY.pack_into(packet,24,*actor);IDENTITY.pack_into(packet,40,component.index,component.serial,component.address)
    struct.pack_into('<f',packet,56,checked_radius(radius))
    result=bytes(packet);validate_request(result);return result


def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Streaming radius packet size')
    header=HEADER.unpack_from(packet)
    if header[:4]!=(3,263,0,0) or not header[4] or any(packet[60:]):raise ValueError('Streaming radius packet fields')
    for offset in (24,40):
        index,serial,address=IDENTITY.unpack_from(packet,offset)
        if index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff or address&7:
            raise ValueError('Streaming radius identity')
    checked_radius(struct.unpack_from('<f',packet,56)[0])


def acknowledge(request,response):
    validate_request(request)
    try:packet=bytes.fromhex(response['mesh_packet'])
    except (KeyError,TypeError,ValueError) as error:raise RuntimeError('Streaming radius acknowledgement malformed; not replayed') from error
    if len(packet)!=SIZE:raise RuntimeError('Streaming radius acknowledgement size; not replayed')
    error,state=struct.unpack_from('<II',packet,8)
    expected=bytearray(request);struct.pack_into('<II',expected,8,error,state)
    if packet!=bytes(expected) or (error,state) not in ((0,1),(4310,0),(4311,0)):
        raise RuntimeError('Streaming radius acknowledgement changed; not replayed')
    if error:raise RuntimeError(f'Streaming radius rejected or uncertain: {error}; not replayed')
