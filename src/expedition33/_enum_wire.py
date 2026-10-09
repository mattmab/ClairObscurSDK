"""Candidate version4 retained calls. Not connected to the running session."""
from dataclasses import replace
import struct
from . import _invocation_wire as call, _retained_wire as retained

VERSION, KIND, SIZE = 4, 14, retained.SIZE


def encode_plan(plan):
    if type(plan.wire_version) is not int or plan.wire_version != VERSION or plan.texts:
        raise ValueError('Expected a version4 enum plan without owned text')
    fields = [(i, p) for i, p in enumerate(plan.parameters) if p.kind == 'EnumProperty']
    if not fields:
        raise ValueError('Enum packet requires enum fields')
    normalized = list(plan.parameters)
    for i, p in fields:
        if (p.width != 1 or p.dimension != 1 or p.boolean_encoding or p.pod_profile or
                p.constraint is None or p.constraint.serial < 0):
            raise ValueError('Invalid enum field layout or identity')
        normalized[i] = replace(p, kind='ByteProperty')
    packet = bytearray(retained.encode_plan(replace(plan, parameters=tuple(normalized), wire_version=2)))
    struct.pack_into('<I', packet, 0, VERSION)
    for i, _ in fields:
        struct.pack_into('<I', packet, call.FIELDS_AT + i*call.FIELD.size, KIND)
    return bytes(packet)


def decode_reply(request, encoded):
    if type(request) is not bytes or len(request) != SIZE or call.HEADER.unpack_from(request)[0] != VERSION:
        raise ValueError('Invalid enum request packet')
    return retained.decode_reply(request, encoded)
