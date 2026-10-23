"""Shared component-pose receipt; helper correction preserves observed scale.

Uses opcode154 and its existing native transform profiles, with ownership held
by the caller. A failed or uncertain helper write requires retirement.
"""
import math
import struct
import threading


def scaled(pose):
    return (len(pose)==12 and all(math.isfinite(v) and abs(v)<=100000 for v in pose)
        and abs(sum(v*v for v in pose[:4])-1)<=1e-6 and pose[7]==pose[11]==0
        and all(0<v<=1000 for v in pose[8:11]))


def preserves_scale(a,b):
    return scaled(a) and scaled(b) and all(abs(a[i]-b[i])<=1e-6 for i in range(8,11))


def same_scaled(a,b):
    return (preserves_scale(a,b) and abs(abs(sum(x*y for x,y in zip(a[:4],b[:4])))-1)<=1e-6
        and all(abs(a[i]-b[i])<=.001 for i in range(4,7)))


def decode_report(packet,raw,pose,valid_before,same_after):
    if len(raw)!=len(packet):raise RuntimeError('Component pose acknowledgement malformed; preserve owner')
    error,state=struct.unpack_from('<II',raw,8)
    expected=bytearray(packet);struct.pack_into('<II',expected,8,error,state);expected[4096:4304]=raw[4096:4304]
    if raw!=bytes(expected) or state!=(0 if error else 1):
        raise RuntimeError('Component pose acknowledgement differs; preserve owner')
    before=struct.unpack_from('<12d',raw,4096);after=struct.unpack_from('<12d',raw,4192)
    flags=struct.unpack_from('<4I',raw,4288)
    if any(v not in (0,1) for v in flags) or any(flags[i+1]>flags[i] for i in range(3)):
        raise RuntimeError('Component pose report malformed; preserve owner')
    report=dict(error=error,before=before,after=after,attempted=bool(flags[0]),
        acknowledged=bool(flags[1]),readback=bool(flags[2]),verified=bool(flags[3]))
    if not error and (flags!=(1,1,1,1) or not valid_before(before) or not same_after(after,pose)):
        raise RuntimeError('Component pose readback differs; preserve owner')
    return report


def set_helper_pose(owner,component,setter,getter,pose):
    from .owned_battle_arena import validate_request,COMPONENT_POSE,SIZE
    owner._scope._check()
    if threading.get_ident()!=owner._thread:raise RuntimeError('Helper requires its owning Python thread')
    cap=getattr(owner._transport,'owned_helper_component_pose_protocol',0)
    if type(cap) is not int or cap!=1:raise RuntimeError('Owned helper component pose unavailable')
    if (owner._closed or owner.phase!='spawned' or not owner._prepared or owner._grounded
            or not owner.has_native_work or owner.actor_identity is None):
        raise RuntimeError('Owned inert prepared helper required')
    key=(component.index,component.serial,component.address)
    if key in owner._component_pose_attempts:raise RuntimeError('Helper component pose already attempted; no replay')
    pose=tuple(pose)
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,COMPONENT_POSE,0,0,owner._owner);packet[24]=1
    for i,obj in enumerate((component,setter,getter)):
        struct.pack_into('<iiQ',packet,88+16*i,obj.index,obj.serial,obj.address)
    struct.pack_into('<12d',packet,2000,*pose);validate_request(bytes(packet))
    owner._component_pose_attempts.add(key);owner.phase='unknown'
    owner.last_operation=COMPONENT_POSE
    reply=owner._transport.command('mesh',bytes(packet))
    report=decode_report(packet,bytes.fromhex(reply['mesh_packet']),pose,
                         lambda before:preserves_scale(before,pose),same_scaled)
    if report['error']:
        owner.last_error='HelperComponentPoseRejected'
        error=RuntimeError('Owned helper component pose rejected: '+str(report['error']));error.report=report;raise error
    owner.phase='spawned';owner.last_error=None
    return report
