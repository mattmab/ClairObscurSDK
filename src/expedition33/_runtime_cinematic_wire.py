"""Isolated fixed-demo envelope. Does not extend reflected argument codecs."""
import struct

SIZE=20984
INPUT_COUNT=57
HEADER=struct.Struct('<4IQ')
IDENTITY=struct.Struct('<iiQ')


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Cinematic packet size')
    version,op,error,state,owner=HEADER.unpack_from(data)
    if version!=3 or op not in (70,71,72,73) or error or state or not owner or any(data[24:88]):
        raise ValueError('Cinematic request header/output fields')
    end=88+16*INPUT_COUNT if op==70 else 88
    if any(data[end:]):raise ValueError('Cinematic request has unexpected payload')
    if op==70:
        for i in range(INPUT_COUNT):
            index,serial,address=IDENTITY.unpack_from(data,88+16*i)
            if index<0 or serial<0 or not address:raise ValueError('Invalid cinematic object identity')
