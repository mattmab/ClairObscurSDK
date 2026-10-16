"""Persistent one-save-per-world assignments and once-per-visit scheduling."""
import json,re
from pathlib import Path

class Assignments:
    def __init__(self,path):
        self.path=Path(path);self.values={}
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf8'))
            if data.get('version')!=1 or not isinstance(data.get('maps'),dict):raise ValueError('Invalid overlay settings')
            for world,key in data['maps'].items():self.validate(world,key)
            self.values=data['maps']
    @staticmethod
    def validate(world,key):
        if not isinstance(world,str) or not world.startswith('/Game/') or len(world)>2048:raise ValueError('Invalid game map')
        if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Invalid save ID')
    def select(self,world,key):
        if key is not None:self.validate(world,key)
        updated=dict(self.values)
        if key is None:updated.pop(world,None)
        else:updated[world]=key
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(dict(version=1,maps=updated),indent=2),encoding='utf8');tmp.replace(self.path)
        self.values=updated

class Visits:
    def __init__(self):self.visit=None;self.since=0.;self.attempted=False
    def observe(self,context,now):
        if not context or not context['ready']:
            self.since=now
            return False
        visit=(context['world'],*context['visit'])
        if visit!=self.visit:self.visit=visit;self.since=now;self.attempted=False
        return not self.attempted and now-self.since>=2.
