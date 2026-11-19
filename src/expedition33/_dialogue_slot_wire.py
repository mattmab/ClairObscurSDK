"""Narrow native animation-slot contract; independent of Blueprint v8."""
from dataclasses import replace
import struct
from . import _blueprint_wire as blueprint,_retained_wire as retained
from .invocation import UnsupportedInvocation
VERSION=12
def validate(plan):
    if (plan.entry_rva!=0x33a3bc0 or plan.function_flags!=67240963 or plan.function.name!='PlaySlotAnimationAsDynamicMontage' or
        plan.parameter_size!=48 or plan.allocation_extent!=48 or plan.return_offset!=40):
        raise UnsupportedInvocation('Only the verified native dialogue-slot function is supported')
    if dict(plan.texts)!={'SlotNodeName':dict(plan.texts).get('SlotNodeName')} or dict(plan.texts).get('SlotNodeName') not in ('DefaultSlot','Mouth'):
        raise UnsupportedInvocation('Only original DefaultSlot and Mouth animation slots are supported')
    blendin,blendout,rate,loops,trigger,start=struct.unpack_from('<3fi2f',plan.data,16)
    if not ((abs(blendin-.4)<1e-6 and abs(blendout-.4)<1e-6) or (abs(blendin-.35)<1e-6 and abs(blendout-.35)<1e-6)) or rate!=1 or loops not in (1,10000) or trigger!=-1 or start!=0:
        raise UnsupportedInvocation('Reviewed dialogue montage timing required')
def encode_plan(plan):
    if plan.wire_version!=VERSION:raise UnsupportedInvocation('Explicit dialogue-slot plan required')
    validate(plan)
    normalized=replace(plan,wire_version=8,function_flags=0,entry_rva=0x13937a0)
    packet=bytearray(blueprint.encode_plan(normalized))
    struct.pack_into('<I',packet,0,VERSION)
    struct.pack_into('<II',packet,16,plan.function_flags,plan.entry_rva)
    return bytes(packet)
def decode_reply(request,encoded):return retained.decode_reply(request,encoded)
