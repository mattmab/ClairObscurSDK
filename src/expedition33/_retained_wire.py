"""Isolated v8 retained-call envelope; tokens belong to the native session."""
import struct
from . import _invocation_wire as call

SIZE = 26192
HEADER = struct.Struct('<II')
LEASE = struct.Struct('<IQ')
LEASES_AT = call.SIZE + HEADER.size


def encode_plan(plan):
    return call.encode_plan(plan) + HEADER.pack(1, 0) + bytes(128 * LEASE.size)


def decode_reply(request, encoded):
    if type(request) is not bytes or len(request) != SIZE:
        raise ValueError('Invalid retained request')
    if not isinstance(encoded, str) or len(encoded) != SIZE * 2:
        raise ValueError('Invalid retained response length')
    packet = bytes.fromhex(encoded)
    if len(packet) != SIZE:
        raise ValueError('Invalid retained response encoding')
    version, count = HEADER.unpack_from(packet, call.SIZE)
    if version != 1 or count > 128:
        raise ValueError('Invalid retained envelope')
    reply = call.decode_reply(request[:call.SIZE], packet[:call.SIZE].hex())
    leases = tuple(LEASE.unpack_from(packet, LEASES_AT + i * LEASE.size) for i in range(count))
    if (any(not token for _, token in leases) or
            len({offset for offset, _ in leases}) != count or
            len({token for _, token in leases}) != count or
            any(packet[LEASES_AT + count * LEASE.size:])):
        raise ValueError('Invalid retained tokens')
    if reply.outcome == 'not_dispatched' and leases:
        raise ValueError('Undispatched call acquired ownership')
    if reply.outcome == 'dispatch_returned':
        output_offsets = set()
        fields = call.HEADER.unpack_from(request)[6]
        for number in range(fields):
            kind, offset, width, dimension, flags, *_ = call.FIELD.unpack_from(
                request, call.FIELDS_AT + number * call.FIELD.size)
            if kind in (7, 8) and flags & 0x500:
                output_offsets.update(offset + i * width for i in range(dimension))
        expected = {offset for offset, *_ in reply.objects if offset in output_offsets}
        if {offset for offset, _ in leases} != expected:
            raise ValueError('Missing or unexpected output ownership')
    # Unknown outcomes may contain partial ownership. Never expose those tokens
    # as usable results: caller must abort its controller and await GT cleanup.
    return reply, leases
