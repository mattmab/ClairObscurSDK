"""Replaceable bounded gallery batches, measured packing and persisted plans."""
import json,math,time
from . import bulk
class Gallery:
    def __init__(self,menu):
        self.menu=menu;self.library=menu.library;self.assets=[];self.index=0;self.size=1000;self.spacing=600.;self.tight=True
        self.queue=[];self.owned=[];self.paused=False;self.failures=[];self.origin=None;self.cursor=0;self.positions=[];self.views=[];self.x=0.;self.y=0.;self.row_depth=0.
        self.last_paint=0.;self.started_at=0.;self.elapsed=0.;self.columns=32
        self.file=self.library.store.root.parent/'gallery.json'
    def clear(self):
        self.queue=[]
        bulk.delete_many(self.library,self.owned)
        self.owned=[]
        self.positions=[];self.views=[];self.cursor=0
    def start(self,assets,size=18,spacing=600.):
        size=int(size);spacing=float(spacing)
        if not 1<=size<=5000 or not math.isfinite(spacing) or not 50<=spacing<=10000:raise ValueError('Batch size 1â€“100; spacing 50â€“100000 cm')
        if size+len(self.library.owned)-len(self.owned)>bulk.SCENE_LIMIT-17:raise ValueError('Save or clear scene objects before adding this gallery batch')
        self.assets=list(dict.fromkeys(assets));self.size=size;self.spacing=spacing;self.index=0
        self.origin=list(self.menu.mod.last['position']);self.origin[0]+=1200.;self.request(0)
    def request(self,delta):
        if not self.assets:raise ValueError('Choose assets and spawn the first batch')
        bulk.prepare(self.library)
        self.clear();self.index=max(0,min((len(self.assets)-1)//self.size,self.index+delta));self.queue=list(self.assets[self.index*self.size:(self.index+1)*self.size]);self.paused=False;self.failures=[]
        self.columns=max(6,min(100,math.ceil(math.sqrt(len(self.queue)))))
        result=bulk.floor(self.library,self.origin,self.spacing,self.tight,self.columns);self.owned.append(result['id'])
        self.started_at=time.monotonic();self.elapsed=0.
    def tick(self):
        if self.paused or not self.queue:return
        # Keep a failed asset from blocking later rows, and retain unprocessed
        # requests when the native per-frame budget ends a batch early.
        requests=[]
        for asset in self.queue[:64]:
            if asset not in self.library.bulk_indices and asset!=bulk.CUBE:break
            requests.append((asset,[0.,0.,0.,1.,*self.origin,0.,1.,1.,1.,0.]))
        if not requests:
            asset=self.queue.pop(0);key=None
            try:
                result=self.library.spawn(asset,[0.,0.,0.,1.,*self.origin,0.,1.,1.,1.,0.]);key=result['id']
                results=[bulk.place_existing(self.library,key)]
            except Exception as error:
                if key is not None:self.library.delete(key)
                results=[dict(asset=asset,error=str(error))]
        else:
            try:results=bulk.spawn_batch(self.library,requests,gallery=True,prepared=True)
            except Exception:
                self.paused=True;raise
            del self.queue[:len(results)]
        for result in results:
            if 'error' in result:self.failures.append(result);continue
            self.owned.append(result['id']);self.positions.append(result['transform'][4:7])
            center=result['center'];extent=result['extent'];distance=max(300.,sum(v*v for v in extent)**.5*2.5)
            self.views.append([center[0]-distance,center[1],center[2]+distance*.27,-15,0,0,0,0])
        self.elapsed=time.monotonic()-self.started_at
        self.library.message=self.summary()
    def summary(self):return f'Gallery batch {self.index+1}/{max(1,math.ceil(len(self.assets)/self.size))}: {len(self.positions)} placed, {len(self.queue)} queued, {len(self.failures)} failed'+f' / {self.elapsed:.1f}s'+(' / paused' if self.paused else '')
    def visit(self):
        if not self.positions:raise ValueError('Spawn a gallery first')
        view=self.views[self.cursor%len(self.views)];self.cursor+=1
        self.menu.mod.command(42,values=view);self.menu.hide()
    def save(self):
        if not self.assets:raise ValueError('Create a gallery first')
        data=dict(version=1,world=self.library.world,assets=self.assets,index=self.index,size=self.size,spacing=self.spacing,tight=self.tight,origin=self.origin)
        tmp=self.file.with_suffix('.tmp');tmp.write_text(json.dumps(data),encoding='utf8');tmp.replace(self.file);self.library.message='Saved gallery layout'
    def rebuild(self):
        d=json.loads(self.file.read_text(encoding='utf8'))
        _,_,_,world=self.library.context()
        if d.get('version')!=1 or d['world']!=world:raise ValueError('Load the saved gallery game level first')
        assets=d['assets'];size=d['size'];spacing=d['spacing'];origin=d['origin']
        if not isinstance(assets,list) or not assets or len(assets)>250000 or any(a not in self.library.known for a in assets):raise ValueError('Saved gallery assets unavailable')
        if type(size)!=int or not 1<=size<=5000 or not 50<=spacing<=10000 or len(origin)!=3 or any(not math.isfinite(v) or abs(v)>1e7 for v in origin):raise ValueError('Invalid saved gallery layout')
        self.assets=assets;self.size=size;self.spacing=spacing;self.origin=origin;self.tight=bool(d['tight']);self.index=int(d['index']);self.request(0)
