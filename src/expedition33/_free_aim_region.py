"""Read-only game-thread crosshair collision query; no attack is executed."""
import struct,math,secrets
from . import RuntimeQueryError

SIZE=20984
IDENTITY=struct.Struct('<iiQ')
OUTPUT=struct.Struct('<IIiiQiiQiiQdd')

def identity(obj):return obj.index,obj.serial,obj.address

def encode(manager,token,source,definitions,owner):
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,228,0,0,owner)
    IDENTITY.pack_into(packet,24,*identity(manager));struct.pack_into('<Q',packet,40,token)
    IDENTITY.pack_into(packet,48,*identity(source))
    if len(definitions)!=7:raise ValueError('Seven aim-region definitions required')
    for i,obj in enumerate(definitions):IDENTITY.pack_into(packet,64+16*i,*identity(obj))
    result=bytes(packet);validate_request(result);return result

def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Aim-region packet size')
    header=struct.unpack_from('<4IQ',packet)
    if header[:4]!=(3,228,0,0) or not header[4] or not struct.unpack_from('<Q',packet,40)[0]:raise ValueError('Aim-region header')
    for at in (24,48,*range(64,176,16)):
        index,serial,address=IDENTITY.unpack_from(packet,at)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address&7:raise ValueError('Aim-region identity')
    if any(packet[176:]):raise ValueError('Aim-region reserved/output bytes')

def decode(sent,raw):
    if type(raw) is not bytes or len(raw)!=SIZE or raw[:8]!=sent[:8] or raw[16:256]!=sent[16:256] or any(raw[328:]):
        raise RuntimeQueryError('Aim-region response differs from its request')
    error,state=struct.unpack_from('<II',raw,8)
    if error or state!=1:raise RuntimeQueryError('Aim-region observation unavailable')
    hit,part_type,*values=OUTPUT.unpack_from(raw,256)
    if hit not in (0,1) or part_type>4:raise RuntimeQueryError('Aim-region response flags')
    actor,component,part=(tuple(values[i:i+3]) for i in (0,3,6));multiplier,base=values[-2:]
    if not all(type(v) is float and math.isfinite(v) and 0<=v<=1.e6 for v in (multiplier,base)):
        raise RuntimeQueryError('Aim-region damage values')
    for obj in (actor,component,part):
        if obj!=(0,0,0) and (obj[0]<0 or obj[1]<0 or obj[2]<0x10000 or obj[2]&7):raise RuntimeQueryError('Aim-region output identity')
    if not hit:
        if any(raw[260:328]):raise RuntimeQueryError('Empty aim region has payload')
        return None
    if actor==(0,0,0) or component==(0,0,0):raise RuntimeQueryError('Aim-region hit lacks identity')
    return dict(actor=actor,component=component,part=part,body_part=part_type,multiplier=multiplier,base_damage=base)

class FreeAimRegion:
    def __init__(self,scope,manager):
        scope._check();self.scope=scope;self.owner=secrets.randbits(64) or 1
        if getattr(scope._session._transport,'free_aim_region_query_protocol',0)!=1:raise RuntimeQueryError('Aim-region runtime unavailable')
        from .catalog import capture_matching
        c=capture_matching(scope.pid,names=('Default__KismetSystemLibrary','GetCameraLocation','GetCameraRotation','LineTraceSingle','BreakHitResult','BP_FreeAimTargetPart_C','Default__GameplayStatics'))
        paths=('/Script/Engine.Default__KismetSystemLibrary','/Script/Engine.PlayerCameraManager:GetCameraLocation',
               '/Script/Engine.PlayerCameraManager:GetCameraRotation','/Script/Engine.KismetSystemLibrary:LineTraceSingle',
               '/Script/Engine.GameplayStatics:BreakHitResult','/Game/Gameplay/FreeAim/BP_FreeAimTargetPart.BP_FreeAimTargetPart_C',
               '/Script/Engine.Default__GameplayStatics')
        self.definitions=tuple(c.find_path(path) for path in paths)
        from ._stable_lease import acquire_stable
        self.held,_=acquire_stable(scope,manager);self.manager=self.held.object

    def sample(self,source):
        self.scope._check()
        packet=encode(self.manager,self.held._token,source,self.definitions,self.owner)
        with self.scope._lease_context():reply=self.scope._session._transport.command('mesh',packet)
        return decode(packet,bytes.fromhex(reply['mesh_packet']))

    def close(self):
        if self.held.active:return self.held.release()
        return True
