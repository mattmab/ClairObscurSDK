"""Dedicated bounded Scene Editor adapter; no reflection codec changes."""
import struct,math
SIZE=20984
INPUT_COUNT=99
ROLE_COUNT=484
CLIP_COUNT=2689
PLAN=struct.Struct('<II119d')
AUTHOR_PLAN=struct.Struct('<II283d')
MULTI_PLAN=struct.Struct('<II380d')
EDIT_PLAN=struct.Struct('<II412d')
LEGACY_PLAN=struct.Struct('<II67d')

def validate_request(data,*,protocol=None,allow_retired=False):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Scene packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    packet_version=version
    if (allow_retired and version==7 and op==72 and struct.unpack_from('<I',data,24)[0]==0x45504f43):
        if error or state or not owner or any(data[28:]):raise ValueError('Retired-world scene request')
        if protocol is not None and protocol!=7:raise ValueError('Scene backend mismatch')
        return
    if version not in (3,4,5,6,7) or op not in (*range(70,93),98) or error or state or not owner or any(data[24:88]):raise ValueError('Scene packet header')
    if protocol is not None and packet_version!=protocol:raise ValueError('Scene backend mismatch')
    if version==3 and op in range(75,80):raise ValueError('Authoring requires protocol four')
    if op==98:
        index,serial,address=struct.unpack_from('<iiQ',data,88);slot=struct.unpack_from('<I',data,104)[0]
        if packet_version!=7 or index<0 or serial<0 or not address or slot>=24 or any(data[108:112]) or any(data[112+EDIT_PLAN.size:]):raise ValueError('Live animation insertion payload')
        nested=bytearray(SIZE);struct.pack_into('<4IQ',nested,0,7,76,0,0,owner);nested[88:88+EDIT_PLAN.size]=data[112:112+EDIT_PLAN.size]
        validate_request(bytes(nested),protocol=7)
        values=EDIT_PLAN.unpack_from(data,112)[2:];count=values[283]
        if slot>=count or values[284+slot*4+1]<0 or values[284+slot*4+2]<0:raise ValueError('Live insertion requires a real animation')
        return
    if op==92:
        action,*view=struct.unpack_from('<8d',data,88)
        if packet_version!=7 or action not in (0,1) or any(data[152:]) or any(not math.isfinite(v) for v in view):raise ValueError('Camera transfer payload')
        if action==0 and any(view) or action==1 and (any(abs(v)>(1.e8 if i<3 else 360) for i,v in enumerate(view[:6])) or not 20<=view[6]<=120):raise ValueError('Camera transfer view')
        return
    if op==91:
        if packet_version!=7:raise ValueError('Photo entry requires protocol seven')
        for at in (88,104):
            index,serial,address=struct.unpack_from('<iiQ',data,at)
            if index<0 or serial<0 or not address:raise ValueError('Photo entry identity')
        if any(data[120:]):raise ValueError('Photo entry payload')
        return
    if op==90:
        if packet_version!=7 or any(data[88:]):raise ValueError('Photo menu status payload')
        return
    if op==89:
        if packet_version!=7:raise ValueError('Photo help requires protocol seven')
        index,serial,address=struct.unpack_from('<iiQ',data,88)
        if index<0 or serial<0 or not address or any(data[104:]):raise ValueError('Photo help identity')
        return
    if op==88:
        if packet_version!=7:raise ValueError('Scene timeline ownership requires protocol seven')
        for at in (88,104):
            index,serial,address=struct.unpack_from('<iiQ',data,at)
            if index<0 or serial<0 or not address:raise ValueError('Timeline widget identity')
        if struct.unpack_from('<I',data,120)[0]>3 or any(data[124:]):raise ValueError('Timeline ownership flags')
        return
    if op>=83:
        if op>=86:
            if packet_version!=7:raise ValueError('Scene editing requires protocol seven')
            if op==86:
                slot,zero=struct.unpack_from('<2d',data,88)
                if not math.isfinite(slot) or slot!=int(slot) or not 0<=slot<23 or zero!=0 or any(data[104:]):raise ValueError('Delete audio slot')
            else:
                enabled=struct.unpack_from('<d',data,88)[0]
                if enabled not in (0,1):raise ValueError('Game music toggle')
                if enabled:
                    for at in range(96,160,16):
                        index,serial,address=struct.unpack_from('<iiQ',data,at)
                        if index<0 or serial<0 or not address:raise ValueError('Game music identity')
                elif any(data[96:160]):raise ValueError('Game music disable payload')
                if any(data[160:]):raise ValueError('Game music padding')
            return
        if packet_version not in (6,7):raise ValueError('Audio library requires protocol six')
        end=88
        if op!=85:
            index,serial,address=struct.unpack_from('<iiQ',data,88);slot,asset=struct.unpack_from('<II',data,104)
            if index<0 or serial<0 or not address or (slot>=23 if op==83 else slot!=23) or asset>=250000:raise ValueError('Audio library payload')
            kind=struct.unpack_from('<I',data,112)[0]
            if kind not in (0,2,3,4):raise ValueError('Audio asset kind')
            end=116
        if any(data[end:]):raise ValueError('Audio library padding')
        return
    if op in (80,81):
        for offset in ((88,) if op==80 else (88,104)):
            index,serial,address=struct.unpack_from('<iiQ',data,offset)
            if index<0 or serial<0 or not address:raise ValueError('Invalid catalog identity')
        if op==80:
            if struct.unpack_from('<I',data,104)[0]>4 or any(data[108:2000]) or any(data[2004:]):raise ValueError('Catalog query payload')
        elif struct.unpack_from('<I',data,124)[0]>4 or any(data[128:]):raise ValueError('Catalog load payload')
        return
    end=88
    if op==70:
        count=134 if packet_version==7 else 133 if packet_version>=5 else (109 if any(data[88+16*104:88+16*109]) else 104) if packet_version>=4 else 99 if protocol==3 or protocol is None and any(data[88+16*57:88+16*99]) else 57
        end+=16*count
        for i in range(count):
            index,serial,address=struct.unpack_from('<iiQ',data,88+16*i)
            if index<0 or serial<0 or not address:raise ValueError('Invalid scene identity')
    elif op in (74,76):
        magic,version=struct.unpack_from('<II',data,88)
        layout=EDIT_PLAN if version==6 else MULTI_PLAN if version==5 else AUTHOR_PLAN if version>=4 else LEGACY_PLAN if version==1 else PLAN
        end+=layout.size
        magic,version,*values=layout.unpack_from(data,88)
        if magic!=0x314e4353 or version not in (1,2,3,4,5,6) or any(not math.isfinite(v) for v in values):raise ValueError('Invalid scene plan')
        if packet_version>=4 and version!=(6 if packet_version==7 else min(packet_version,5)):raise ValueError('Authoring plan version mismatch')
        if protocol is not None and version!=(6 if protocol==7 else min(protocol,5)):raise ValueError('Scene plan/backend version mismatch')
        if version>=5:
            n=values[283]
            if n!=int(n) or not 0<=n<=24:raise ValueError('Additional animation count')
            for i in range(24):
                actor,at,clip,loop=values[284+i*4:288+i*4]
                if i>=n:
                    if any((actor,at,clip,loop)):raise ValueError('Unused additional animation')
                elif version==6 and at==-1:
                    if (actor,clip,loop)!=(0,-1,0):raise ValueError('Disabled animation slot')
                elif actor!=int(actor) or not 0<=actor<values[1] or not 0<=at<values[0] or clip!=int(clip) or not -1<=clip<CLIP_COUNT or loop not in (0,1):raise ValueError('Additional animation')
        if version==6 and any(not 0<=gain<=2 for gain in values[380:412]):raise ValueError('Audio clip volume')
        duration=values[0]
        if not 2<=duration<=120:raise ValueError('Scene duration')
        count=3 if version==1 else values[1]
        if count!=int(count) or not 0<=count<=6:raise ValueError('Scene actor count')
        pose_offset=1 if version==1 else 8
        for i in range(3 if version==1 else 6):
            pose=values[pose_offset+9*i:pose_offset+9*(i+1)]
            if any(abs(v)>5000 for v in pose[:3]) or any(abs(v)>360 for v in pose[3:6]) or any(not .001<=v<=3 for v in pose[6:]) or len(set(pose[6:]))!=1:raise ValueError('Scene transform')
        if version==1:
            if any(not 0<=v<duration for v in values[28:60]):raise ValueError('Scene event timestamp')
            camera_offset=60
        else:
            roles=values[2:8];animation=values[62:68];clips=values[68:74];loops=values[74:80];bindings=values[80:83]
            if any(v!=int(v) or not 0<=v<(ROLE_COUNT if version>=3 else 3) for v in roles) or any(v!=int(v) or not (-1 if version>=4 else 0)<=v<(CLIP_COUNT if version>=3 else 3) for v in clips) or any(v not in (0,1) for v in loops):raise ValueError('Scene character/animation choice')
            if any(not 0<=v<duration and not (version==6 and v==-1 and clips[i]==-1) for i,v in enumerate(animation)):raise ValueError('Scene animation start')
            for role,b in enumerate(bindings):
                if b!=int(b) or not -1<=b<count or b>=0 and roles[int(b)]!=role:raise ValueError('Scene actor binding')
            event_end=135 if version>=4 else 112
            if any(v!=-1 and not 0<=v<duration for v in values[83:event_end]):raise ValueError('Scene event timestamp')
            for i in range(9):
                attacker=1 if i in (1,3,6) else 0
                if any(values[j+i]>=0 for j in ((83,115,124) if version>=4 else (83,92,101))) and (bindings[attacker]<0 or bindings[2]<0):raise ValueError('Unbound scene attack')
            if any(values[(133 if version>=4 else 110)+i]>=0 and bindings[i]<0 for i in range(2)):raise ValueError('Unbound scene trail')
            camera_offset=135 if version>=4 else 112
        r,center,height,rise,start,finish,fov=values[camera_offset:camera_offset+7]
        if not (100<=r<=2000 and abs(center)<=5000 and 20<=height<=2000 and abs(rise)<=500 and 0<=start<finish<=duration and 20<=fov<=120):raise ValueError('Scene camera')
        if version>=4:
            if any(abs(v)>(1.e8 if i<3 else 360) for i,v in enumerate(values[142:146])) or any(abs(v)>(1.e8 if i<3 else 360) for i,v in enumerate(values[146:152])) or any(v not in (0,1) for v in values[152:154]):raise ValueError('Authoring camera/anchor')
            n=values[154]
            if n!=int(n) or not 0<=n<=16:raise ValueError('Camera key count')
            last=-1
            for i in range(16):
                key=values[155+i*8:163+i*8]
                if i>=n:
                    if any(key):raise ValueError('Unused camera key')
                    continue
                if not last<key[0]<=duration or any(abs(v)>5000 for v in key[1:4]) or any(abs(v)>360 for v in key[4:7]) or not 20<=key[7]<=120:raise ValueError('Camera key')
                last=key[0]
    elif op==75:
        end=136
        if any(data[88:136]):
            for at in (88,104,120):
                index,serial,address=struct.unpack_from('<iiQ',data,at)
                if index<0 or serial<0 or not address:raise ValueError('Photo authoring identity')
    elif op in (77,78,79):
        end=104;a,b=struct.unpack_from('<2d',data,88)
        if not math.isfinite(a) or not math.isfinite(b):raise ValueError('Authoring command')
        if op==77 and (a!=int(a) or not 0<=a<6 or b not in (0,1)):raise ValueError('Audition command')
        if op==78 and (not 0<=a<=120 or b!=0):raise ValueError('Seek command')
        if op==79 and (a!=int(a) or not 0<=a<=7 or a>=6 and b!=0 or b!=int(b) or not 0<=b<=5):raise ValueError('Editor control')
    if any(data[end:]):raise ValueError('Unexpected scene payload')
