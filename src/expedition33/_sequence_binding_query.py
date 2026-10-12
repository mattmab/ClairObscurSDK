"""Bounded diagnostic query for native-owned, no-play sequence bindings.

Results are counters, not callable object handles or permission to play.
The native owner independently verifies the function and authored asset profile.
"""
import struct

PACKET = struct.Struct('<4IiiQ8I')
MAGIC = 0x51423345
PROFILE_LIMITS = {1: 1, 2: 5}


def encode(profile, function):
    if type(profile) is not int or profile not in PROFILE_LIMITS:
        raise ValueError('Unsupported sequence binding profile')
    identity = (function.index, function.serial, function.address)
    if (any(type(v) is not int for v in identity) or
            not 0 <= identity[0] < 2**31 or not 0 <= identity[1] < 2**31 or
            not 0 < identity[2] < 2**64):
        raise ValueError('Invalid sequence binding function identity')
    return PACKET.pack(MAGIC, 1, profile, 0, *identity, *([0] * 8))


def validate_request(data):
    if type(data) is not bytes or len(data) != PACKET.size:
        raise ValueError('Sequence binding query size')
    magic, version, profile, reserved, index, serial, address, *fields = PACKET.unpack(data)
    if ((magic, version, reserved) != (MAGIC, 1, 0) or
            profile not in PROFILE_LIMITS or index < 0 or serial < 0 or not address or any(fields)):
        raise ValueError('Sequence binding query request')


def decode(request, response):
    validate_request(request)
    if type(response) is not bytes or len(response) != PACKET.size or response[:32] != request[:32]:
        raise ValueError('Sequence binding query acknowledgement mismatch')
    completed, matched, active, peak, outcome, *reserved = PACKET.unpack(response)[7:]
    limit = PROFILE_LIMITS[PACKET.unpack(request)[2]]
    if (completed > limit or matched > completed or active > peak or peak > 17 or
            outcome > 2 or any(reserved)):
        raise ValueError('Sequence binding query response bounds')
    return dict(completed_queries=completed, matched_bindings=matched,
                private_active=active, private_peak=peak, outcome=outcome)
