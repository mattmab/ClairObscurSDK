"""Persistent timeline edits over copied authored source data.

Source assets are immutable inputs. Edits use section paths, channel fields and
source key ordinals, never UObject identities. Applying them to an owned native
sequence is a separate operation; this module never invokes the game.
"""
import copy,hashlib,json,math,os,re,uuid
from pathlib import Path
from .authored_source import MAX_GRAPH_NODES

MAX_TIMELINE_BYTES=64*1024*1024


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode('utf8')).hexdigest()


def _unshared_json_tree(root):
    """Fast-copy only plain JSON trees with no shared mutable identities.

    ``deepcopy`` preserves aliases and tuple/custom-object types, whereas a
    JSON round trip does not.  Validate the entire document before using that
    optimization so aliases between the source and edits also use the normal
    deepcopy path.  Inputs from imported and stored sources are plain trees.
    """
    seen=set();pending=[root]
    while pending:
        value=pending.pop();kind=type(value)
        if kind is dict:
            identity=id(value)
            if identity in seen:return False
            seen.add(identity)
            if any(type(key) is not str for key in value):return False
            pending.extend(value.values())
        elif kind is list:
            identity=id(value)
            if identity in seen:return False
            seen.add(identity);pending.extend(value)
        elif kind not in (str,int,float,bool,type(None)):return False
    return True
def frame(value):
    if type(value) is not int or not -(1<<31)<=value<(1<<31):raise ValueError('Expected a signed frame number')
    return value
def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Expected a finite key value')
    return value


def _check_source(graph,name):
    if type(name) is not str or not 1<=len(name)<=160 or any(ord(c)<32 for c in name):raise ValueError('Invalid timeline name')
    if (type(graph) is not dict or type(graph.get('nodes')) is not dict or not 1<=len(graph['nodes'])<=MAX_GRAPH_NODES
            or type(graph.get('sequence')) is not str or graph['sequence'] not in graph['nodes']
            or graph['nodes'][graph['sequence']].get('class_name')!='LevelSequence'):
        raise ValueError('Authored source graph is missing its root')


def create(graph,name):
    _check_source(graph,name)
    source=copy.deepcopy(graph)
    return dict(format='e33.authored-timeline',version=1,name=name,source=source,
                source_sha256=digest(source),section_edits={},key_edits=[],cast_edits=[],npc_tracks=[])


def set_npc(document,key,*,name,profile,start,end,offset,yaw):
    candidate=validate(document)
    rows=[r for r in candidate['npc_tracks'] if r['id']!=key]
    rows.append(dict(id=key,name=name,profile=profile,start=start,end=end,
                     placement=dict(offset=list(offset),yaw=yaw)))
    _check_npcs(rows)
    candidate['npc_tracks']=rows
    return candidate


def remove_npc(document,key):
    candidate=validate(document)
    candidate['npc_tracks']=[r for r in candidate['npc_tracks'] if r['id']!=key]
    return candidate


def place_scene(document,position):
    candidate=validate(document)
    _check_scene_position(position)
    candidate['scene_position']=list(position) if position is not None else None
    return candidate


def rotate_scene(document,yaw):
    candidate=validate(document)
    if type(yaw) not in (int,float) or not math.isfinite(yaw) or abs(yaw)>180.:
        raise ValueError('Scene yaw must be between -180 and 180 degrees')
    candidate['scene_yaw']=float(yaw)
    return candidate


def _check_scene_position(position):
    if position is not None and (type(position) is not list or len(position)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000000 for v in position)):
        raise ValueError('Scene position must be three finite world coordinates in centimeters')


def _check_placement(placement):
    if type(placement) is not dict or set(placement)!={'offset','yaw'}:raise ValueError('Invalid Blueprint placement')
    offset=placement['offset'];yaw=placement['yaw']
    if type(offset) is not list or len(offset)!=3 or any(type(n) not in (int,float) or not math.isfinite(n) or abs(n)>100000 for n in offset):raise ValueError('Blueprint offset must be three bounded finite centimeters')
    if type(yaw) not in (int,float) or not math.isfinite(yaw) or abs(yaw)>180:raise ValueError('Blueprint yaw must be between -180 and 180 degrees')


def _check_npcs(rows):
    from .blueprint_actor import PROFILES
    if type(rows) is not list or len(rows)>32:raise ValueError('At most 32 Blueprint NPC tracks are supported')
    seen=set()
    for row in rows:
        if type(row) is not dict or set(row)!={'id','name','profile','start','end','placement'}:raise ValueError('Invalid Blueprint NPC track')
        key=row['id']
        if type(key) is not str or re.fullmatch('[a-f0-9]{32}',key) is None or key in seen:raise ValueError('Invalid or duplicate NPC track ID')
        seen.add(key)
        if type(row['name']) is not str or not 1<=len(row['name'])<=160 or any(ord(c)<32 for c in row['name']):raise ValueError('Invalid NPC name')
        if type(row['profile']) is not str or row['profile'] not in PROFILES:raise ValueError('Choose a reviewed NPC Blueprint')
        frame(row['start']);frame(row['end'])
        if row['end']<=row['start']:raise ValueError('NPC end must follow its start')
        _check_placement(row['placement'])


def replace_cast(document,sequence,guid,profile):
    """Save a sequence-local actor replacement without runtime object handles."""
    candidate=validate(document)
    edits=[e for e in candidate['cast_edits'] if (e['sequence'],e['guid'])!=(sequence,guid)]
    if profile is not None:
        edit=dict(sequence=sequence,guid=guid,profile=profile)
        previous=next((e for e in candidate['cast_edits'] if (e['sequence'],e['guid'])==(sequence,guid)),None)
        if previous is not None and 'placement' in previous:edit['placement']=previous['placement']
        edits.append(edit)
    candidate['cast_edits']=edits
    _check_cast_edits(candidate,edits)
    return candidate


def place_cast(document,sequence,guid,offset,yaw):
    """Place an owned Blueprint replacement relative to the preview anchor."""
    candidate=validate(document)
    edit=next((e for e in candidate['cast_edits'] if (e['sequence'],e['guid'])==(sequence,guid)),None)
    if edit is None:raise ValueError('Choose a replacement Blueprint before placing it')
    edit['placement']=dict(offset=list(offset),yaw=yaw)
    _check_cast_edits(candidate,candidate['cast_edits'])
    return candidate


def _check_cast_edits(document,edits):
    if type(edits) is not list or len(edits)>64:raise ValueError('Cast replacement bounds exceeded')
    if not edits:return
    from .authored_cast import bindings
    from .blueprint_actor import PROFILES
    rows={(r['sequence'],r['guid']):r for r in bindings(document['source'])};seen=set()
    for edit in edits:
        if type(edit) is not dict or set(edit) not in ({'sequence','guid','profile'},{'sequence','guid','profile','placement'}):raise ValueError('Invalid cast replacement')
        if any(type(edit[k]) is not str for k in ('sequence','guid','profile')):raise ValueError('Invalid cast replacement fields')
        if 'placement' in edit:
            _check_placement(edit['placement'])
        key=(edit['sequence'],edit['guid']);row=rows.get(key)
        if key in seen:raise ValueError('Duplicate cast replacement')
        seen.add(key)
        if row is None or row['kind']!='spawnable' or not row['template'] or not row['template']['class'].startswith('BP_Cine_'):
            raise ValueError('Choose an authored cinematic Blueprint actor')
        if edit['profile'] not in PROFILES:raise ValueError('Choose a reviewed replacement Blueprint')


def _section(document,path):
    node=document['source']['nodes'].get(path)
    if node is None or 'Section' not in node['class_name']:raise ValueError('Choose a source section')
    return node


def source_range(document,path):
    bounds=_section(document,path)['fields'].get('SectionRange',{}).get('frame_range')
    if bounds is None:raise ValueError('Section frame range has not been decoded')
    from ..values import StoredFrameRange
    result=StoredFrameRange(bounds['lower']['kind'],bounds['lower']['value'],bounds['upper']['kind'],bounds['upper']['value'])
    return result.start,result.end


def retime(document,path,start,end):
    source_range(document,path);frame(start);frame(end)
    if end<=start:raise ValueError('Section end must follow its start')
    candidate=copy.deepcopy(document)
    candidate['section_edits'][path]=dict(start=start,end=end)
    return candidate


def channel(document,section,path):
    if type(path) is not list or not 1<=len(path)<=16:raise ValueError('Invalid channel field path')
    value={'fields':_section(document,section)['fields']}
    for part in path:
        if type(part) is str:
            value=value.get('fields',{}).get(part)
        elif type(part) is int and 0<=part<64:
            items=value.get('static_array',[])
            value=items[part] if part<len(items) else None
        else:raise ValueError('Invalid channel field selector')
        if type(value) is not dict:raise ValueError('Channel field is unavailable')
    kind=value.get('struct','').rsplit('.',1)[-1]
    if kind not in ('MovieSceneDoubleChannel','MovieSceneFloatChannel','MovieSceneIntegerChannel','MovieSceneBoolChannel','MovieSceneByteChannel'):
        raise ValueError('Unsupported editable channel type')
    fields=value['fields'];times=fields.get('Times',{});values=fields.get('Values',{})
    if times.get('complete') is not True or values.get('complete') is not True or times['length']!=values['length']:
        raise ValueError('Complete matching key arrays are required')
    keys=[]
    for t,v in zip(times['array'],values['array']):
        at=frame(t['fields']['Value'])
        number=v.get('fields',{}).get('Value') if type(v) is dict else v
        if kind=='MovieSceneBoolChannel':
            if type(number) is not bool:raise ValueError('Boolean channel requires Boolean keys')
        else:finite(number)
        keys.append(dict(at=at,value=number))
    if any(a['at']>=b['at'] for a,b in zip(keys,keys[1:])):raise ValueError('Channel keys must be strictly ordered')
    return kind,keys


def edit_key(document,section,path,index,*,at,value):
    edits=copy.deepcopy(document['key_edits'])
    edits=[e for e in edits if (e['section'],e['path'],e['index'])!=(section,path,index)]
    edits.append(dict(section=section,path=list(path),index=index,at=at,value=value))
    _check_key_edits(document,edits)
    candidate=copy.deepcopy(document);candidate['key_edits']=edits
    return candidate


def reset_key(document,section,path,index):
    candidate=validate(document)
    _,keys=channel(candidate,section,path)
    if type(index) is not int or not 0<=index<len(keys):raise ValueError('Choose an existing source key')
    candidate['key_edits']=[e for e in candidate['key_edits']
        if (e['section'],e['path'],e['index'])!=(section,path,index)]
    # Restoring one key can cross a neighbor that was independently moved.
    _check_key_edits(candidate,candidate['key_edits'])
    return candidate


def channels(document,section):
    """Enumerate editable complete curves, retaining their exact field paths."""
    result=[]
    def visit(value,path):
        if type(value) is not dict or len(path)>16:return
        if value.get('struct','').rsplit('.',1)[-1] in (
                'MovieSceneDoubleChannel','MovieSceneFloatChannel','MovieSceneIntegerChannel',
                'MovieSceneBoolChannel','MovieSceneByteChannel'):
            try:kind,keys=channel(document,section,path)
            except ValueError:return
            edits={(e['index']):e for e in document['key_edits'] if e['section']==section and e['path']==path}
            keys=[dict(index=i,at=edits.get(i,key)['at'],value=edits.get(i,key)['value']) for i,key in enumerate(keys)]
            result.append(dict(path=list(path),kind=kind,keys=keys));return
        for name,child in value.get('fields',{}).items():visit(child,path+[name])
        for index,child in enumerate(value.get('static_array',[])):visit(child,path+[index])
    visit({'fields':_section(document,section)['fields']},[])
    return tuple(result)


def _check_key_edits(document,edits):
    groups={};seen=set()
    for edit in edits:
        if type(edit) is not dict or set(edit)!={'section','path','index','at','value'}:raise ValueError('Invalid key edit')
        group=canonical([edit['section'],edit['path']]);token=(group,edit['index'])
        if type(edit['index']) is not int or token in seen:raise ValueError('Invalid or duplicate source key edit')
        seen.add(token)
        if group not in groups:groups[group]=channel(document,edit['section'],edit['path'])
        kind,keys=groups[group];index=edit['index'];value=edit['value']
        if not 0<=index<len(keys):raise ValueError('Choose an existing source key')
        frame(edit['at'])
        if kind=='MovieSceneBoolChannel':
            if type(value) is not bool:raise ValueError('Boolean channel requires a Boolean value')
        else:
            finite(value)
            if kind in ('MovieSceneIntegerChannel','MovieSceneByteChannel'):
                frame(value)
                if kind=='MovieSceneByteChannel' and not 0<=value<=255:raise ValueError('Byte key is outside its range')
        keys[index]=dict(at=edit['at'],value=value)
    for _,keys in groups.values():
        if any(a['at']>=b['at'] for a,b in zip(keys,keys[1:])):raise ValueError('Edited key crosses or duplicates a neighboring key')


def validate(document):
    expected={'format','version','name','source','source_sha256','section_edits','key_edits'}
    if type(document) is not dict or not expected<=set(document)<=expected|{'cast_edits','npc_tracks','scene_position','scene_yaw'} or document['format']!='e33.authored-timeline' or type(document['version']) is not int or document['version']!=1:
        raise ValueError('Unsupported authored timeline document')
    # Checking is read-only; the independent return value is copied below.
    # Avoid copying a large source graph twice on every validation.
    _check_source(document['source'],document['name'])
    encoded_source=canonical(document['source'])
    if hashlib.sha256(encoded_source.encode('utf8')).hexdigest()!=document['source_sha256']:raise ValueError('Authored source snapshot has changed')
    if type(document['section_edits']) is not dict or len(document['section_edits'])>2048 or type(document['key_edits']) is not list or len(document['key_edits'])>8192:
        raise ValueError('Authored edit bounds exceeded')
    for path,edit in document['section_edits'].items():
        if type(edit) is not dict or set(edit)!={'start','end'}:raise ValueError('Invalid section edit')
        source_range(document,path);frame(edit['start']);frame(edit['end'])
        if edit['end']<=edit['start']:raise ValueError('Section end must follow its start')
    _check_key_edits(document,document['key_edits'])
    _check_cast_edits(document,document.get('cast_edits',[]))
    _check_npcs(document.get('npc_tracks',[]))
    _check_scene_position(document.get('scene_position'))
    yaw=document.get('scene_yaw',0.)
    if type(yaw) not in (int,float) or not math.isfinite(yaw) or abs(yaw)>180.:
        raise ValueError('Scene yaw must be between -180 and 180 degrees')
    # Round-trip plain JSON source trees without sorting so original key order
    # remains unchanged.  This is much faster for large graphs than Python's
    # generic deepcopy, while unusual inputs retain its exact semantics.
    memo={id(document['source']):json.loads(json.dumps(document['source'],separators=(',',':'),allow_nan=False))} if _unshared_json_tree(document) else None
    result=copy.deepcopy(document,memo);result.setdefault('cast_edits',[]);result.setdefault('npc_tracks',[])
    return result


class TimelineStore:
    def __init__(self,root):self.root=Path(root);self._listing={}
    def file(self,key):
        if type(key) is not str or re.fullmatch('[a-f0-9]{32}',key) is None:raise ValueError('Invalid authored timeline ID')
        return self.root/(key+'.authored.json')
    def save(self,document,key=None):
        document=validate(document);key=key or uuid.uuid4().hex;target=self.file(key)
        # Source graphs can be large; compact JSON avoids spending most of the
        # file budget on indentation while remaining compatible with old files.
        data=(json.dumps(document,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')
        if len(data)>MAX_TIMELINE_BYTES:raise ValueError('Authored timeline exceeds size limit')
        self.root.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():raise ValueError('Refusing linked timeline file')
        temp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('xb') as stream:
                stream.write(data);stream.flush();os.fsync(stream.fileno())
            temp.replace(target)
        finally:
            if temp.exists():temp.unlink()
        return key
    def read(self,key):
        path=self.file(key)
        if path.is_symlink() or path.stat().st_size>MAX_TIMELINE_BYTES:raise ValueError('Invalid authored timeline file')
        return validate(json.loads(path.read_text(encoding='utf8')))
    def list(self):
        rows=[]
        for path in sorted(self.root.glob('*.authored.json')):
            if len(rows)>=256:break
            key=path.name.split('.')[0]
            try:
                stat=path.stat();stamp=(stat.st_mtime_ns,stat.st_size)
                cached=self._listing.get(key)
                if cached is None or cached[0]!=stamp:
                    doc=self.read(key);cached=(stamp,dict(id=key,name=doc['name'],source=doc['source']['sequence']))
                    self._listing[key]=cached
                rows.append(dict(cached[1]))
            except (ValueError,TypeError,KeyError,OSError):continue
        return rows
