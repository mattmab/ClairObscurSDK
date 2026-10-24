"""Canonical translation-only origin request for an SDK-owned sequence actor."""
import math
import struct

PACKET = struct.Struct('<IIddd')
MAGIC = 0x4f533345
LIMIT = 10_000_000.


def encode(translation):
    if type(translation) not in (tuple, list) or len(translation) != 3:
        raise ValueError('Sequence origin requires three translation coordinates')
    if any(type(value) not in (int, float) or abs(value) > LIMIT or
           not math.isfinite(value) for value in translation):
        raise ValueError('Sequence origin translation is outside finite bounds')
    return PACKET.pack(MAGIC, 1, *translation)


def validate_request(data):
    if type(data) is not bytes or len(data) != PACKET.size:
        raise ValueError('Sequence origin request size')
    magic, version, *translation = PACKET.unpack(data)
    if magic != MAGIC or version != 1 or encode(translation) != data:
        raise ValueError('Sequence origin request header or coordinates')
