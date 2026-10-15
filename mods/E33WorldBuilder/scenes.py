"""Portable scene files. Native identities are never written to disk."""
import json, math, re, uuid
from pathlib import Path

FORMAT='e33.world-builder.scene'

def pose(values):
    if type(values) is not list or len(values)!=12 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e8 for x in values):
        raise ValueError('Expected a finite 12-number transform')
    if not .999 <= sum(x*x for x in values[:4]) <= 1.001 or any(not .001<=abs(x)<=10000 for x in values[8:11]):
        raise ValueError('Invalid rotation or scale')
    return list(values)

def path(value):
    if type(value) is not str or not value.startswith(('/Game/','/Engine/','/Script/')) or len(value)>2048 or any(ord(c)<32 for c in value):
        raise ValueError('Expected an engine object path')
    return value

def validate(data,world=None):
    if type(data) is not dict or data.get('format')!=FORMAT or data.get('version')!=1:raise ValueError('Unsupported scene format')
    if type(data.get('name')) is not str or not 1<=len(data['name'])<=80 or any(ord(c)<32 for c in data['name']):raise ValueError('Map name must be 1–80 characters')
    path(data['world'])
    if world is not None and data['world']!=world:raise ValueError('Load the same game level before loading this builder map')
    rows=data.get('objects')
    if type(rows) is not list or len(rows)>128:raise ValueError('A map supports at most 128 tracked objects')
    ids=set();assets=set()
    for row in rows:
        if type(row) is not dict or row.get('kind') not in ('mesh','actor','world_edit'):raise ValueError('Invalid tracked object')
        key=row.get('id')
        if type(key) is not str or not re.fullmatch('[a-f0-9]{32}',key) or key in ids:raise ValueError('Invalid or duplicate object ID')
        ids.add(key);pose(row['transform']);path(row['asset']);assets.add(row['asset'])
        if row['kind']=='world_edit':path(row['component'])
        children=row.get('component_edits',[])
        if type(children) is not list or len(children)>128:raise ValueError('Too many component edits')
        seen=set()
        for child in children:
            suffix=child.get('component')
            if type(suffix) is not str or not re.fullmatch(r'\.[A-Za-z0-9_.:-]{1,512}',suffix) or suffix in seen:raise ValueError('Invalid relative component path')
            seen.add(suffix);pose(child['transform']);path(child['asset']);assets.add(child['asset'])
    if data.get('assets')!=sorted(assets):raise ValueError('Asset manifest does not match tracked objects')
    return json.loads(json.dumps(data,allow_nan=False))

class MapStore:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def file(self,key):
        if type(key) is not str or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Choose a saved map ID')
        return self.root/(key+'.e33map.json')
    def save(self,data):
        data=validate(data);key=uuid.uuid4().hex;dst=self.file(key);tmp=dst.with_suffix('.tmp')
        tmp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf8');tmp.replace(dst);return key
    def read(self,key):
        p=self.file(key)
        if p.stat().st_size>4*1024*1024:raise ValueError('Scene file is too large')
        return validate(json.loads(p.read_text(encoding='utf8')))
    def list(self):
        result=[]
        for p in sorted(self.root.glob('*.e33map.json')):
            try:
                key=p.name.split('.')[0];d=self.read(key);result.append(dict(id=key,name=d['name'],count=len(d['objects']),world=d['world']))
            except (ValueError,KeyError,TypeError,OSError):continue
        return result
