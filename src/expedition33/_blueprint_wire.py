"""Explicit retained Blueprint calls using lifetime-free typed codecs."""
from dataclasses import replace
import struct
from . import _retained_wire as retained
from .invocation import UnsupportedInvocation

VERSION = 8
NAME_KIND = 21
FORBIDDEN_FLAGS = (0x400 | 0x40 | 0x80 | 0x100 | 0x1000 | 0x2000 |
                   0x4000 | 0x8000 | 0x10000 | 0x100000 | 0x200000 |
                   0x1000000 | 0x80000000)

def validate_function(flags, entry_rva, name):
    if (flags & FORBIDDEN_FLAGS or entry_rva != 0x13937a0 or
            not name or name.startswith('ExecuteUbergraph')):
        raise UnsupportedInvocation('Blueprint calls reject native/RPC/delegate/ubergraph/static functions and unverified thunks')

def encode_name(parameter, value):
    if type(value) is not str or not value or not all(ch.isascii() and (ch.isalnum() or ch in '_./-') for ch in value):
        raise ValueError('FName input requires an explicit nonempty registered ASCII name')
    data = parameter.encode('ascii') + b'\0' + value.encode('ascii') + b'\0'
    if len(data) > 96:
        raise UnsupportedInvocation('FName parameter and expected name exceed the 96-byte wire field')
    return data

def encode_plan(plan):
    if type(plan.wire_version) is not int or plan.wire_version != VERSION:
        raise UnsupportedInvocation('Expected an explicit typed Blueprint v8 plan')
    validate_function(plan.function_flags, plan.entry_rva, plan.function.name)
    if any(p.pod_profile in ('/Script/CoreUObject.QualifiedFrameTime', '/Script/CoreUObject.Timespan') for p in plan.parameters):
        raise UnsupportedInvocation('Blueprint calls do not support specialized time codecs')
    from . import _invocation_wire as call
    names = dict(plan.texts)
    name_fields = [(i, p) for i, p in enumerate(plan.parameters) if p.kind == 'NameProperty']
    if len(names) != len(plan.texts) or set(names) != {p.name for _, p in name_fields}:
        raise UnsupportedInvocation('Blueprint name payload does not match its fields')
    normalized = list(plan.parameters)
    for i, p in name_fields:
        if (p.width != 8 or p.dimension != 1 or not p.input or p.flags & 0x400 or (p.flags & 0x100 and not p.flags & 0x8000000) or
                p.constraint is not None or p.boolean_encoding or p.pod_profile or
                any(plan.data[p.offset:p.offset+8])):
            raise UnsupportedInvocation('FName supports zeroed scalar input storage only')
        normalized[i] = replace(p, kind='DoubleProperty')
    packet = bytearray(retained.encode_plan(replace(plan, parameters=tuple(normalized), wire_version=2, texts=())))
    struct.pack_into('<I', packet, 0, VERSION)
    for i, p in name_fields:
        at = call.FIELDS_AT + i * call.FIELD.size
        struct.pack_into('<I', packet, at, NAME_KIND)
        encoded = encode_name(p.name, names[p.name])
        packet[at+28:at+124] = encoded.ljust(96, b'\0')
    return bytes(packet)

def decode_reply(request, encoded):
    if type(request) is not bytes or len(request) != retained.SIZE or int.from_bytes(request[:4], 'little') != VERSION:
        raise ValueError('Invalid Blueprint request packet')
    return retained.decode_reply(request, encoded)
