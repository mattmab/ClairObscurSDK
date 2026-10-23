"""Bounded milestone-one documents. No transient Unreal identities on disk."""
import copy,json,math,re,struct,uuid,os
from pathlib import Path
from .palette import ASSETS,ASSEMBLIES,CHARACTERS,ROLES,CLIPS,CLIP_LABELS

SAMPLE=Path(__file__).with_name('sample.scene.json')
TEMPLATE=json.loads(SAMPLE.read_text(encoding='utf8'))
PLAN=struct.Struct('<II412d')
MAGIC=0x314E4353
MAX_ACTORS=6
ASSEMBLIES.update(TEMPLATE['assemblies'])
ACTOR_TEMPLATES={a['assembly']:copy.deepcopy(a) for a in TEMPLATE['actors']}
for role,row in CHARACTERS.items():
    ACTOR_TEMPLATES.setdefault(role,dict(id=role,name=row['label'],kind='character',assembly=role,transform=dict(position=[0,0,0],rotation=[0,0,0],scale=[row['scale']]*3)))

def number(value,low,high):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'Expected a finite number from {low} to {high}')
    return float(value)

def text(value,limit=80):
    if type(value) is not str or not 1<=len(value)<=limit or any(ord(c)<32 for c in value):raise ValueError('Invalid scene text')
    return value

def canonical(value):return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))

def sound_path(value):
    if type(value) is not str or len(value)>511 or not re.fullmatch(r'/Game/[A-Za-z0-9_/-]+\.[A-Za-z0-9_-]+',value):raise ValueError('Choose a game audio asset from the audio library')
    package,name=value.rsplit('.',1)
    if package.rsplit('/',1)[-1]!=name:raise ValueError('Invalid sound object path')
    return value

# These exact body-only recipes were saved before the five actor assemblies
# gained their inspected face/hair parts. No other catalog mismatch migrates.
_LEGACY_BODY_ASSEMBLIES={
    'mesh-a5ddbbff8d49':'/Game/Characters/Gestrals/Golgra/SK_Golgra.SK_Golgra',
    'mesh-098be90fc9a5':'/Game/Characters/Gestrals/Noco/SK_Noco.SK_Noco',
    'mesh-530d4c6218bf':'/Game/Characters/Enemies/Axons/Many_faces/Faces/Face_Sadness.Face_Sadness',
    'mesh-3bcd02b8bbf3':'/Game/Characters/Enemies/Paintress/SK_Paintress_UE5_V2.SK_Paintress_UE5_V2',
    'mesh-a44413d5b7d7':'/Game/Characters/Heros/Noah/SK_Gustave_Placeholder.SK_Gustave_Placeholder',
    'mesh-ec219a8fbdab':'/Game/Characters/Enemies/HumanEnnemies/Clea_v1/SK_Clea_Cinematics.SK_Clea_Cinematics',
    'mesh-d875adaa10b1':'/Game/Characters/Enemies/HumanEnnemies/Simon/SK_Simon.SK_Simon',
}

def _legacy_body_assembly(role,recipe,assets):
    body=role+'_body'
    return (role in _LEGACY_BODY_ASSEMBLIES
        and type(recipe) is dict
        and recipe=={'body':body,'recipe':'scene-palette-v15'}
        and assets.get(body)==ASSETS.get(body)==_LEGACY_BODY_ASSEMBLIES[role])

def validate(data):
    if type(data) is not dict or set(data)-{'anchor','camera_keys','mute_game_music'}!=set(TEMPLATE):raise ValueError('Unsupported scene fields')
    data=copy.deepcopy(data)
    if data['format']!='e33.runtime-scene' or type(data['version']) is not int or data['version']!=1:raise ValueError('Unsupported scene version')
    text(data['name']);text(data['target_map'],1024)
    if not data['target_map'].startswith('/Game/') or data['coordinate_space']!=TEMPLATE['coordinate_space']:raise ValueError('Invalid map/coordinate space')
    duration=number(data['duration'],2,120)
    if 'mute_game_music' in data and type(data['mute_game_music']) is not bool:raise ValueError('Invalid game music setting')
    for field in ('assets','assemblies'):
        expected=ASSETS if field=='assets' else ASSEMBLIES
        if type(data[field]) is not dict or any(k not in expected or (canonical(v)!=canonical(expected[k]) and not (field=='assemblies' and _legacy_body_assembly(k,v,data['assets']))) for k,v in data[field].items()):raise ValueError('Unsupported scene catalog assets or assembly recipes')
    if 'anchor' in data:
        if type(data['anchor']) is not list or len(data['anchor'])!=4:raise ValueError('Invalid scene anchor')
        for i,v in enumerate(data['anchor']):number(v,-1.e8 if i<3 else -360,1.e8 if i<3 else 360)
    camera_keys=data.get('camera_keys',[])
    if type(camera_keys) is not list or len(camera_keys)>16:raise ValueError('Up to 16 camera keys')
    key_ids=set();times=set()
    for key in camera_keys:
        if type(key) is not dict or set(key)!={'id','at','position','rotation','fov'}:raise ValueError('Invalid camera key fields')
        if type(key['id']) is not str or not re.fullmatch('camera-[a-f0-9]{12}',key['id']) or key['id'] in key_ids:raise ValueError('Invalid camera key ID')
        key_ids.add(key['id']);at=number(key['at'],0,duration)
        if at in times:raise ValueError('Camera key times must be distinct')
        times.add(at)
        for field,limit in (('position',5000),('rotation',360)):
            if type(key[field]) is not list or len(key[field])!=3:raise ValueError('Invalid camera coordinates')
            for value in key[field]:number(value,-limit,limit)
        number(key['fov'],20,120)
    if 'camera_keys' in data:data['camera_keys']=sorted(camera_keys,key=lambda k:k['at'])
    actors=data['actors']
    if type(actors) is not list or len(actors)>MAX_ACTORS:raise ValueError('A scene supports up to six character instances')
    seen=set()
    for actor in actors:
        if type(actor) is not dict or set(actor)!=set(TEMPLATE['actors'][0]):raise ValueError('Unsupported actor fields')
        key=actor['id']
        if type(key) is not str or not re.fullmatch('[a-z][a-z0-9-]{0,63}',key) or key in seen:raise ValueError('Invalid/duplicate actor ID')
        seen.add(key)
        if actor['assembly'] not in ROLES:raise ValueError('Unsupported character assembly')
        expected=ACTOR_TEMPLATES[actor['assembly']]
        if key in ROLES and key!=actor['assembly']:raise ValueError('Reserved actor ID must match its assembly')
        if (actor['kind'],actor['assembly'])!=(expected['kind'],expected['assembly']):raise ValueError('Unsupported actor assembly')
        text(actor['name']);pose=actor['transform']
        if type(pose) is not dict or set(pose)!={'position','rotation','scale'}:raise ValueError('Invalid transform')
        for field,low,high in (('position',-5000,5000),('rotation',-360,360),('scale',.001,3)):
            if type(pose[field]) is not list or len(pose[field])!=3:raise ValueError('Expected three transform coordinates')
            for value in pose[field]:number(value,low,high)
        if len(set(pose['scale']))!=1:raise ValueError('Only uniform actor scale is supported initially')
    events=data['events'];expected={e['id']:e for e in TEMPLATE['events']}
    if type(events) is not list or len(events)>96:raise ValueError('Too many scene events')
    seen=set();animated=set();actor_ids={a['id'] for a in actors}
    for event in events:
        if type(event) is not dict or set(event)!={'id','type','target','at','params'}:raise ValueError('Unsupported event fields')
        key=event['id']
        if type(key) is not str or key in seen:raise ValueError('Invalid/duplicate event ID')
        seen.add(key)
        number(event['at'],0,duration-.001)
        if event['type']=='animation':
            target=event['target'];params=event['params']
            if target not in actor_ids or not (key=='anim-'+target or re.fullmatch('useranim-[a-f0-9]{12}',key)):raise ValueError('Invalid character animation event')
            if type(params) is not dict or set(params)!={'asset','speed','loop'} or params['asset'] not in (*CLIPS,'bind_pose') or type(params['speed']) not in (int,float) or params['speed']!=1 or type(params['loop']) is not bool:raise ValueError('Unsupported animation choice or playback settings')
            if key=='anim-'+target:animated.add(target)
            continue
        if event['type']=='audio' and key.startswith('useraudio-'):
            reference=next(e for e in TEMPLATE['events'] if e['type']=='audio')
            params=event['params']
            if not re.fullmatch('useraudio-[a-f0-9]{12}',key) or event['target']!='camera' or type(params) is not dict or set(params)!={'asset','volume'} or type(params['volume']) not in (int,float) or not 0<=number(params['volume'],0,2)<=2:raise ValueError('Unsupported audio cue')
            if params['asset']!='sound':sound_path(params['asset'])
            continue
        if key not in expected:raise ValueError('Unsupported event ID')
        reference=copy.deepcopy(expected[key])
        if key=='camera-orbit':
            if type(event['params']) is not dict:raise ValueError('Invalid camera parameters')
            reference['params']['end']=number(event['params'].get('end'),.001,120)
        if event['type']=='audio':
            if type(event['params']) is not dict:raise ValueError('Invalid audio parameters')
            number(event['params'].get('volume'),0,2);reference['params']['volume']=event['params']['volume']
        if (event['type'],event['target'])!=(reference['type'],reference['target']) or canonical(event['params'])!=canonical(reference['params']):
            raise ValueError('Unsupported event operation/parameters; this milestone edits timestamps')
        if event['target']!='camera' and event['target'] not in actor_ids:raise ValueError('Event references a removed character')
        if key.startswith(('audio-','impact-','recoil-')):
            attacker='maelle' if int(key.split('-')[1]) in (1,3,6) else 'lune'
            if attacker not in actor_ids or 'target' not in actor_ids:raise ValueError('Sample attack event requires its attacker and target')
    if sum(e['id'].startswith('useranim-') for e in events)>24:raise ValueError('Up to 24 additional animation clips')
    if sum(e['type']=='audio' and e['id'].startswith('useraudio-') for e in events)>23:raise ValueError('Up to 23 additional audio cues')
    orbit=next((e for e in events if e['id']=='camera-orbit'),None)
    if orbit is None:raise ValueError('Scene camera event is required')
    if not orbit['at']<orbit['params']['end']<=duration:raise ValueError('Camera movement must end within the scene')
    roles={a['assembly'] for a in actors}|{'lune','maelle','target'}
    data['assemblies']={role:copy.deepcopy(ASSEMBLIES[role]) for role in roles}
    keys=set(TEMPLATE['assets'])|{e['params']['asset'] for e in events if e['type']=='animation' and e['params']['asset']!='bind_pose'}
    for role in roles:keys.update(v for v in ASSEMBLIES[role].values() if v in ASSETS)
    data['assets']={key:ASSETS[key] for key in keys}
    return json.loads(canonical(data))

def sample(world):
    data=copy.deepcopy(TEMPLATE);data['target_map']=world
    return validate(data)

def blank(world):
    data=sample(world);data['name']='Untitled scene';data['actors']=[]
    data['events']=[e for e in data['events'] if e['id']=='camera-orbit']
    data['camera_keys']=[]
    return validate(data)

def encode(data,editor_camera=None,*,audio_slots=None,animation_slots=None):
    data=validate(data);actors={a['id']:a for a in data['actors']};events={e['id']:e for e in data['events']}
    ordered=list(actors.values());count=len(ordered)
    values=[data['duration'],count]
    values.extend(ROLES.index(a['assembly']) for a in ordered);values.extend([0]*(MAX_ACTORS-count))
    for i in range(MAX_ACTORS):
        pose=ordered[i]['transform'] if i<count else TEMPLATE['actors'][0]['transform']
        values.extend(pose['position']+pose['rotation']+pose['scale'])
    animation=[events.get('anim-'+a['id'],dict(at=-1.,params=dict(asset='bind_pose',loop=False))) for a in ordered]
    for field in ('at','clip','loop'):
        values.extend(e['at'] if field=='at' else (-1 if e['params']['asset']=='bind_pose' else CLIPS.index(e['params']['asset'])) if field=='clip' else int(e['params']['loop']) for e in animation)
        values.extend([0]*(MAX_ACTORS-count))
    values.extend(next((i for i,a in enumerate(ordered) if a['id']==key),-1) for key in ROLES[:3])
    def event_time(key):
        event=events.get(key)
        if event is None:return -1
        # Sample combat cues only accompany the original attack selections.
        attacker='maelle' if key.startswith(('audio-','impact-','recoil-')) and int(key.split('-')[1]) in (1,3,6) else 'maelle' if key=='trail-maelle' else 'lune'
        anim=events.get('anim-'+attacker)
        if anim is None or anim['params']['asset']!=attacker+'_attack':return -1
        return event['at']
    values.extend(events[f'audio-{i}']['at'] if f'audio-{i}' in events else -1. for i in range(9))
    extra=[e for e in data['events'] if e['id'].startswith('useraudio-')]
    audio_slots=audio_slots if audio_slots is not None else {e['id']:i for i,e in enumerate(extra)}
    audio_times=[-1.]*23;gains=[events.get(f'audio-{i}',dict(params=dict(volume=.35)))['params']['volume'] for i in range(9)]+[.35]*23
    for e in extra:audio_times[audio_slots[e['id']]]=e['at'];gains[9+audio_slots[e['id']]]=e['params']['volume']
    values.extend(audio_times)
    for prefix in ('impact','recoil'):values.extend(event_time(f'{prefix}-{i}') for i in range(9))
    values.extend(event_time('trail-'+key) for key in ('lune','maelle'))
    orbit=events['camera-orbit'];p=orbit['params']
    values.extend((p['radius'],p['center_forward'],p['height'],p['rise'],orbit['at'],p['end'],p['fov']))
    values.extend(data.get('anchor',[0]*4));values.extend(editor_camera or [0]*6);values.extend((int('anchor' in data),int(editor_camera is not None)))
    keys=data.get('camera_keys',[]);values.append(len(keys))
    for key in keys:values.extend([key['at']]+key['position']+key['rotation']+[key['fov']])
    values.extend([0.]*(8*(16-len(keys))))
    extra=[e for e in data['events'] if e['id'].startswith('useranim-')]
    animation_slots=animation_slots if animation_slots is not None else {e['id']:i for i,e in enumerate(extra)}
    n=max((animation_slots[e['id']]+1 for e in extra),default=0);values.append(n)
    rows=[[0.,-1.,-1.,0.] if i<n else [0.]*4 for i in range(24)]
    for e in extra:rows[animation_slots[e['id']]]=[next(i for i,a in enumerate(ordered) if a['id']==e['target']),e['at'],-1 if e['params']['asset']=='bind_pose' else CLIPS.index(e['params']['asset']),int(e['params']['loop'])]
    for row in rows:values.extend(row)
    values.extend(gains)
    return PLAN.pack(MAGIC,6,*values)

def capture_camera(data,editor_camera,at,fov=50,*,replace=None):
    """Capture a world view into a stable, anchor-relative camera key."""
    data=validate(data)
    if 'anchor' not in data:raise ValueError('Enter live editing to establish the scene anchor')
    if type(editor_camera) not in (list,tuple) or len(editor_camera)!=6:raise ValueError('Camera view unavailable')
    for i,v in enumerate(editor_camera):number(v,-1.e8 if i<3 else -360,1.e8 if i<3 else 360)
    at=min(data['duration'],round(number(at,0,data['duration'])*30)/30)
    anchor=data['anchor'];angle=math.radians(anchor[3]);c,s=math.cos(angle),math.sin(angle)
    x,y,z=(editor_camera[i]-anchor[i] for i in range(3))
    keys=data.setdefault('camera_keys',[])
    existing=next((key for key in keys if key['id']==replace),None) if replace is not None else next((key for key in keys if abs(key['at']-at)<.00001),None)
    if replace is not None and existing is None:raise ValueError('Select a camera key on the CAM track first')
    if existing is None:
        if len(keys)>=16:raise ValueError('Sixteen camera keys maximum')
        existing=dict(id='camera-'+uuid.uuid4().hex[:12],at=at);keys.append(existing)
    existing.update(position=[x*c+y*s,-x*s+y*c,z],rotation=[editor_camera[3],math.remainder(editor_camera[4]-anchor[3],360),editor_camera[5]],fov=fov)
    return validate(data)

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

class SceneStore:
    def __init__(self,root):self.root=Path(root)
    def file(self,key):
        if type(key) is not str or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Invalid saved scene ID')
        return self.root/(key+'.scene.json')
    def read(self,key):
        path=self.file(key)
        if path.is_symlink() or path.stat().st_size>128*1024:raise ValueError('Invalid/oversized scene file')
        try:return validate(json.loads(path.read_text(encoding='utf8'),object_pairs_hook=_pairs))
        except (KeyError,TypeError,RecursionError) as error:raise ValueError('Malformed scene document') from error
    def save(self,data,key=None):
        data=validate(data);key=key or uuid.uuid4().hex;path=self.file(key)
        self.root.mkdir(parents=True,exist_ok=True)
        if path.is_symlink():raise ValueError('Refusing a linked scene file')
        temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('x',encoding='utf8') as stream:
                stream.write(json.dumps(data,indent=2,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
            temp.replace(path)
        finally:
            if temp.exists():temp.unlink()
        return key
    def list(self):
        result=[]
        for path in sorted(self.root.glob('*.scene.json')):
            key=path.name.split('.')[0]
            try:data=self.read(key)
            except (ValueError,KeyError,TypeError,OSError):continue
            result.append(dict(id=key,name=data['name'],target_map=data['target_map'],duration=data['duration'],actors=len(data['actors']),animations=sum(e['type']=='animation' for e in data['events']),audio=sum(e['type']=='audio' for e in data['events']),camera_keys=len(data.get('camera_keys',[]))))
        return result
