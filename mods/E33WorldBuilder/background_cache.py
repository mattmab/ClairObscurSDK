"""Persistent idle-time thumbnail scheduling. Never retains engine identities."""
from collections import deque
import json,time
from . import thumbnail_cache as cache

class BackgroundCache:
    def __init__(self,root):
        self.file=root/'background-thumbnails.json';self.enabled=True;self.mode="idle";self.failures={}
        try:
            data=json.loads(self.file.read_text(encoding='utf8'))
            if data.get('build')==cache.build_key():
                self.enabled=data.get('enabled',True) is True
                self.mode='afk' if data.get('mode')=='afk' else 'idle'
                self.failures=data.get('failures',{})
                if data.get('async_version')!=3 and isinstance(self.failures,dict):self.failures={k:v for k,v in self.failures.items() if 'error 1948' not in str(v) and 'Asynchronous thumbnail readback' not in str(v)}
                if data.get('resolver_version')!=2 and isinstance(self.failures,dict):self.failures={k:v for k,v in self.failures.items() if 'operation 47 rejected: error 1947' not in str(v)}
        except (OSError,ValueError,TypeError):pass
        if not isinstance(self.failures,dict):self.failures={}
        self.queue=deque();self.assets=set();self.done=set();self.current=None
        self.next_at=0.;self.last_input=time.monotonic();self.delay=.15;self.last_step_ms=0.
    def save(self):
        self.file.parent.mkdir(parents=True,exist_ok=True)
        temp=self.file.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(build=cache.build_key(),enabled=self.enabled,mode=self.mode,resolver_version=2,async_version=3,failures=self.failures)),encoding='utf8');temp.replace(self.file)
    def set_enabled(self,value):self.enabled=bool(value);self.save()
    def set_mode(self,mode):
        if mode not in ('idle','afk'):raise ValueError('Cache mode must be idle or afk')
        self.mode=mode;self.delay=0. if mode=='afk' else .15;self.next_at=0.;self.save()
    def poll_interval(self):
        return .05 if self.mode=='afk' and self.input(False) else .5
    def sync(self,rows):
        for row in rows:
            asset=row['path']
            # Arbitrary actor constructors can play audio or run gameplay logic.
            # Unattended capture only spawns the builder's plain mesh actor.
            if row['kind']!='mesh' or not asset.startswith('/Game/') or asset in self.assets:continue
            self.assets.add(asset)
            if cache.cached_png(cache.thumbnail_key(asset)):self.done.add(asset)
            elif asset not in self.failures:self.queue.append(asset)
    def input(self,busy,now=None):
        now=time.monotonic() if now is None else now
        if busy:self.last_input=now
        return self.enabled and not busy and now-self.last_input>=5. and now>=self.next_at
    def take(self):
        while self.queue:
            asset=self.queue.popleft()
            if asset in self.done or asset in self.failures:continue
            if cache.cached_png(cache.thumbnail_key(asset)):self.done.add(asset);continue
            self.current=asset;return asset
    def finish(self,asset,error=None):
        if error:self.failures[asset]=str(error)[:300];self.save()
        else:
            self.done.add(asset)
            if self.failures.pop(asset,None) is not None:self.save()
        if self.current==asset:self.current=None
    def interrupted(self,asset):
        if self.current==asset:
            self.current=None
            if asset not in self.done and asset not in self.failures:self.queue.appendleft(asset)
    def cost(self,elapsed):
        self.last_step_ms=round(elapsed*1000,1)
        # Cheap steps should not impose seconds of dead time on every asset.
        # Keep a conservative recovery interval after expensive engine calls.
        self.delay=0. if self.mode=='afk' else min(30.,max(.15,elapsed*4 if elapsed>=.1 else .15,self.delay*.5))
        self.next_at=time.monotonic()+self.delay
    def status(self):
        return dict(enabled=self.enabled,mode=self.mode,total=len(self.assets),cached=len(self.done),remaining=len(self.assets-self.done-set(self.failures)),failed=len(self.assets&set(self.failures)),current=self.current,cooldown_seconds=round(self.delay,1),last_step_ms=self.last_step_ms,idle_seconds=round(time.monotonic()-self.last_input,1))
