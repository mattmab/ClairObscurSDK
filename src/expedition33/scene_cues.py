"""Bounded portable character blocking and camera cuts for owned scenes."""
import math,struct

OFFSET=4096
HEADER=struct.Struct('<4I')
KEY=struct.Struct('<IId9d')
BASE_SIZE=HEADER.size+32*KEY.size
SIZE=BASE_SIZE+30*8

def validate(document):
    actors={a['id'] for a in document['actors']}
    rows=document.get('blocking_keys',[])
    if type(rows) is not list or len(rows)>32:raise ValueError('Up to 32 character blocking keys')
    seen=set()
    for row in rows:
        if type(row) is not dict or set(row)!={'actor','at','transform','interpolation'} or row['actor'] not in actors or row['interpolation'] not in ('step','linear'):raise ValueError('Invalid character blocking key')
        at=row['at'];pose=row['transform']
        if type(at) not in (int,float) or not math.isfinite(at) or not 0<=at<=document['duration'] or (row['actor'],at) in seen:raise ValueError('Invalid/duplicate blocking timestamp')
        seen.add((row['actor'],at))
        if type(pose) is not dict or set(pose)!={'position','rotation','scale'}:raise ValueError('Invalid blocking transform')
        for name,low,high in (('position',-5000,5000),('rotation',-360,360),('scale',.001,3)):
            values=pose[name]
            if type(values) is not list or len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high for v in values):raise ValueError('Invalid blocking coordinates')
        if len(set(pose['scale']))!=1:raise ValueError('Uniform blocking scale required')
    for key in document.get('camera_keys',[]):
        if 'cut' in key and type(key['cut']) is not bool:raise ValueError('Invalid camera cut flag')
    for actor in {r['actor'] for r in rows}:
        if min(r['at'] for r in rows if r['actor']==actor)!=0:raise ValueError('Blocking tracks must start at zero')

def encode(document,*,animation_slots=None):
    validate(document)
    rows=sorted(document.get('blocking_keys',[]),key=lambda r:r['at'])
    keys=sorted(document.get('camera_keys',[]),key=lambda r:r['at'])
    cuts=sum(1<<i for i,k in enumerate(keys) if k.get('cut',False))
    offsets=[0.]*30
    ordered=list(document['actors'])
    extra=[e for e in document['events'] if e['id'].startswith('useranim-')]
    slots=animation_slots if animation_slots is not None else {e['id']:i for i,e in enumerate(extra)}
    for event in document['events']:
        if event['type']!='animation':continue
        offset=event['params'].get('source_offset',0.)
        if type(offset) not in (int,float) or not math.isfinite(offset) or not 0<=offset<=600:raise ValueError('Animation source offset')
        index=6+slots[event['id']] if event['id'].startswith('useranim-') else next(i for i,a in enumerate(ordered) if a['id']==event['target'])
        offsets[index]=offset
    if not rows and not cuts and not any(offsets):return b''
    actors={a['id']:i for i,a in enumerate(document['actors'])}
    payload=HEADER.pack(0x31514353,2 if any(offsets) else 1,len(rows),cuts)
    for row in rows:
        pose=row['transform']
        payload+=KEY.pack(actors[row['actor']],int(row['interpolation']=='linear'),row['at'],*(pose['position']+pose['rotation']+pose['scale']))
    return payload+bytes((32-len(rows))*KEY.size)+struct.pack('<30d',*offsets)

def validate_wire(payload,duration,actors,cameras):
    if len(payload)!=SIZE:raise ValueError('Scene cues size')
    magic,version,count,cuts=HEADER.unpack_from(payload)
    if magic!=0x31514353 or version not in (1,2) or count>32 or actors>6 or cameras>16 or cuts>>cameras:raise ValueError('Scene cues header')
    offsets=struct.unpack_from('<30d',payload,BASE_SIZE)
    if any(not math.isfinite(v) or not 0<=v<=600 or version==1 and v or i<6 and i>=actors and v for i,v in enumerate(offsets)):raise ValueError('Scene animation source offset')
    previous={}
    for i in range(32):
        actor,linear,at,*pose=KEY.unpack_from(payload,HEADER.size+i*KEY.size)
        if i>=count:
            if any((actor,linear,at,*pose)):raise ValueError('Unused scene cue')
            continue
        if actor>=actors or linear>1 or not math.isfinite(at) or not 0<=at<=duration or at<=previous.get(actor,-1) or (actor not in previous and at!=0):raise ValueError('Scene cue actor/time')
        previous[actor]=at
        if any(not math.isfinite(v) or not (-5000<=v<=5000 if j<3 else -360<=v<=360 if j<6 else .001<=v<=3) for j,v in enumerate(pose)) or len(set(pose[6:]))!=1:raise ValueError('Scene cue pose')
