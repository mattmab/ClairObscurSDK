"""Exact no-autoplay LevelSequence factory envelope, not arbitrary struct ABI."""
from dataclasses import replace
import math
import struct
from . import _retained_wire as retained, _invocation_wire as call

def settings(rate=1.):
    if type(rate) not in (int,float) or not math.isfinite(rate) or not .25<=rate<=2:
        raise ValueError('Sequence playback rate must be .25 to 2')
    value=bytearray(40)
    value[16]=1  # Verified nested bTickWhenPaused.
    value[32]=2  # Verified ForceRestoreState enum member.
    struct.pack_into('<f',value,20,rate)
    return bytes(value)

def encode_plan(plan):
    if (plan.wire_version!=7 or plan.entry_rva!=0x321b6a0 or plan.function_flags!=71443459 or
        plan.parameter_size!=72 or plan.allocation_extent!=72 or plan.return_offset!=64 or
        len(plan.parameters)!=5 or len(plan.objects)!=2 or plan.texts or len(plan.data)!=72):
        raise ValueError('Unverified sequence factory contract')
    names=('WorldContextObject','LevelSequence','Settings','OutActor','ReturnValue')
    offsets=(0,8,16,56,64)
    flags=(6755468160533120,6755468160533120,4503668346847360,6755468160533376,6755468160534400)
    for i,p in enumerate(plan.parameters):
        if (p.name!=names[i] or p.kind!=('SequencePlaybackSettings' if i==2 else 'ObjectProperty') or
            p.offset!=offsets[i] or p.width!=(40 if i==2 else 8) or p.dimension!=1 or
            p.flags!=flags[i] or p.boolean_encoding or p.constraint is None):
            raise ValueError('Unverified sequence factory signature')
    rate=struct.unpack_from('<f',plan.data,36)[0]
    if plan.data[16:56]!=settings(rate): raise ValueError('Unverified sequence settings')
    if tuple(o.offset for o in plan.objects)!=(0,8): raise ValueError('Factory object inputs mismatch')
    params=list(plan.parameters)
    params[2]=replace(params[2],kind='UInt16Property',width=2,dimension=20)
    encoded=bytearray(retained.encode_plan(replace(plan,wire_version=2,parameters=tuple(params))))
    struct.pack_into('<I',encoded,0,7)
    struct.pack_into('<4I',encoded,call.FIELDS_AT+2*call.FIELD.size,18,16,40,1)
    return bytes(encoded)

def decode_reply(request,encoded):
    reply,leases=retained.decode_reply(request,encoded)
    if reply.outcome=='dispatch_returned' and reply.data[16:56]!=request[call.DATA_AT+16:call.DATA_AT+56]:
        raise ValueError('Input-only playback settings changed')
    return reply,leases
