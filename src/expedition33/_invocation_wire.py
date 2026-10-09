"""Experimental v6 wire format. Does not attach, dispatch, or retain objects."""
from dataclasses import dataclass
import struct

from .invocation import UnsupportedInvocation

SIZE, MAX_BYTES, MAX_FIELDS, MAX_OBJECTS = 24648, 4096, 128, 128
HEADER = struct.Struct('<10I')
IDENTITY = struct.Struct('<iiQ')
FIELD = struct.Struct('<4IQI96siiQ')
OBJECT = struct.Struct('<IiiQ')
FIELDS_AT = HEADER.size + 2 * IDENTITY.size
OBJECTS_AT = FIELDS_AT + MAX_FIELDS * FIELD.size
DATA_AT = OBJECTS_AT + MAX_OBJECTS * OBJECT.size
KINDS = ('BoolProperty', 'ByteProperty', 'UInt16Property', 'IntProperty',
         'FloatProperty', 'DoubleProperty', 'ObjectProperty', 'ClassProperty')


def _identity(value):
    if value is None:
        return -1, 0, 0
    if value.index < 0 or value.address <= 0:
        raise ValueError('Invalid object identity')
    return value.index, value.serial, value.address


def encode_plan(plan):
    """Encode an observed plan; the native backend independently validates it."""
    if (not 0 <= plan.parameter_size <= MAX_BYTES or
            not plan.parameter_size <= plan.allocation_extent <= 65536 or
            len(plan.parameters) > MAX_FIELDS or len(plan.objects) > MAX_OBJECTS or
            len(plan.data) != plan.parameter_size):
        raise UnsupportedInvocation('Plan exceeds v6 transport bounds')
    packet = bytearray(SIZE)
    HEADER.pack_into(packet, 0, 1, plan.parameter_size, plan.allocation_extent,
                     plan.return_offset, plan.function_flags, plan.entry_rva,
                     len(plan.parameters), len(plan.objects), 0, 0)
    IDENTITY.pack_into(packet, HEADER.size, *_identity(plan.target))
    IDENTITY.pack_into(packet, HEADER.size + IDENTITY.size, *_identity(plan.function))
    for number, parameter in enumerate(plan.parameters):
        try:
            kind = KINDS.index(parameter.kind) + 1
            name = parameter.name.encode('ascii')
        except (ValueError, UnicodeError) as error:
            raise UnsupportedInvocation('Unsupported wire parameter kind or name') from error
        if not name or len(name) > 95 or b'\0' in name:
            raise UnsupportedInvocation('Wire parameter name must contain 1–95 ASCII bytes')
        FIELD.pack_into(packet, FIELDS_AT + number * FIELD.size, kind, parameter.offset,
                        parameter.width, parameter.dimension, parameter.flags,
                        parameter.boolean_encoding or 0, name, *_identity(parameter.constraint))
    for number, patch in enumerate(plan.objects):
        OBJECT.pack_into(packet, OBJECTS_AT + number * OBJECT.size,
                         patch.offset, *_identity(patch.object))
    packet[DATA_AT:DATA_AT + plan.parameter_size] = plan.data
    return bytes(packet)


@dataclass(frozen=True)
class CallReply:
    # Dispatch return is not proof that a native function body or RPC executed.
    outcome: str
    error: int
    data: bytes
    objects: tuple  # (offset, index, serial, address); observations, not handles


def decode_reply(request, encoded):
    """Check reply correlation before exposing any returned bytes/identities.

Errors carry no result values. Unknown outcomes must never be retried
automatically: the target may already have performed side effects.
"""
    if type(request) is not bytes or len(request) != SIZE:
        raise ValueError('Invalid request packet')
    if type(encoded) is not str or len(encoded) != SIZE * 2:
        raise ValueError('Invalid reply packet size')
    try:
        reply = bytes.fromhex(encoded)
    except ValueError as error:
        raise ValueError('Invalid reply packet encoding') from error
    if len(reply) != SIZE:
        raise ValueError('Invalid reply packet size')
    sent, received = HEADER.unpack_from(request), HEADER.unpack_from(reply)
    if (received[:7] != sent[:7] or reply[HEADER.size:OBJECTS_AT] != request[HEADER.size:OBJECTS_AT]):
        raise ValueError('Invocation reply does not match its request')
    count, outcome, error = received[7:]
    if count > MAX_OBJECTS or outcome not in (0, 1, 2) or ((outcome == 1) != (error == 0)):
        raise ValueError('Inconsistent invocation outcome')
    if outcome != 1:
        return CallReply('not_dispatched' if outcome == 0 else 'unknown', error, b'', ())
    size = received[1]
    if size > MAX_BYTES or received[6] > MAX_FIELDS:
        raise ValueError('Invalid reply bounds')
    data = reply[DATA_AT:DATA_AT + size]
    slots = set()
    for number in range(received[6]):
        kind, offset, width, dimension, *_ = FIELD.unpack_from(reply, FIELDS_AT + number * FIELD.size)
        if offset + width * dimension > size:
            raise ValueError('Invalid result layout')
        if kind in (7, 8):
            if width != 8:
                raise ValueError('Invalid object result width')
            for element in range(dimension):
                at = offset + element * 8
                slots.add(at)
                if any(data[at:at + 8]):
                    raise ValueError('Unscoped pointer in result data')
    objects, seen = [], set()
    for number in range(count):
        item = OBJECT.unpack_from(reply, OBJECTS_AT + number * OBJECT.size)
        at, index, serial, address = item
        if at not in slots or at in seen or index < 0 or not address:
            raise ValueError('Invalid result object observation')
        seen.add(at)
        objects.append(item)
    if any(reply[DATA_AT + size:]):
        raise ValueError('Unexpected data outside result extent')
    return CallReply('dispatch_returned', 0, data, tuple(objects))
