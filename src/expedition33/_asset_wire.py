"""Narrow retained LoadAsset_Blocking envelope; no caller-owned native pointers."""
from dataclasses import replace
import struct
from . import _retained_wire as retained, _invocation_wire as call


def encode_plan(plan):
    class_load = plan.entry_rva == 0x3860250
    if (plan.wire_version!=6 or plan.entry_rva not in (0x3860130,0x3860250) or plan.function_flags!=67249155 or
            plan.parameter_size!=48 or plan.allocation_extent!=48 or plan.return_offset!=40 or
            len(plan.parameters)!=2 or plan.objects or plan.texts):
        raise ValueError('Unverified asset loader contract')
    a,r=plan.parameters
    if (a.kind!=('SoftClassProperty' if class_load else 'SoftObjectProperty') or a.name!=('AssetClass' if class_load else 'Asset') or a.offset or a.width!=40 or a.dimension!=1 or
            a.flags!=7881299347898496 or a.boolean_encoding or a.constraint is None or
            r.kind!=('ClassProperty' if class_load else 'ObjectProperty') or r.name!='ReturnValue' or r.offset!=40 or r.width!=8 or
            r.dimension!=1 or r.flags!=6755468160534400 or r.constraint!=a.constraint):
        raise ValueError('Unverified soft reference signature')
    if (len(plan.data)!=48 or any(plan.data[:8]+plan.data[12:16]+plan.data[20:]) or
            not struct.unpack_from('<I',plan.data,8)[0] or not struct.unpack_from('<I',plan.data,16)[0]):
        raise ValueError('Soft reference must contain only two name IDs')
    normalized=replace(a,kind='UInt16Property',width=2,dimension=20)
    wire=bytearray(retained.encode_plan(replace(plan,wire_version=2,parameters=(normalized,r))))
    struct.pack_into('<I',wire,0,6)
    struct.pack_into('<4I',wire,call.FIELDS_AT,17,0,40,1)
    return bytes(wire)


def decode_reply(request,encoded):
    reply,leases=retained.decode_reply(request,encoded)
    if reply.outcome=='dispatch_returned' and reply.data[:40]!=request[call.DATA_AT:call.DATA_AT+40]:
        raise ValueError('Input-only soft reference changed')
    return reply,leases
