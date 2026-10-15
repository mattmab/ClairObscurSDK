"""Replaceable bounded gallery batches, measured packing and persisted plans."""
import json,math
class Gallery:
    def __init__(self,menu):
        self.menu=menu;self.library=menu.library;self.assets=[];self.index=0;self.size=18;self.spacing=600.;self.tight=True
        self.queue=[];self.owned=[];self.paused=False;self.failures=[];self.origin=None;self.cursor=0;self.positions=[];self.views=[];self.x=0.;self.y=0.;self.row_depth=0.
        self.file=self.library.store.root.parent/'gallery.json'
    def clear(self):
        self.queue=[]
        while self.owned:
            key=self.owned[-1]
            if key in self.library.owned:self.library.delete(key)
            self.owned.pop()
        self.positions=[];self.views=[];self.cursor=0
    def start(self,assets,size=18,spacing=600.):
        size=int(size);spacing=float(spacing)
        if not 1<=size<=100 or not math.isfinite(spacing) or not 50<=spacing<=100000:raise ValueError('Batch size 1–100; spacing 50–100000 cm')
        if size+len(self.library.owned)-len(self.owned)>110:raise ValueError('Save or clear scene objects before adding this gallery batch')
        self.assets=list(dict.fromkeys(assets));self.size=size;self.spacing=spacing;self.index=0
        self.origin=list(self.menu.mod.last['position']);self.origin[0]+=1200.;self.request(0)
    def request(self,delta):
        if not self.assets:raise ValueError('Choose assets and spawn the first batch')
        self.clear();self.index=max(0,min((len(self.assets)-1)//self.size,self.index+delta));self.queue=list(self.assets[self.index*self.size:(self.index+1)*self.size]);self.paused=False;self.failures=[];self.x=self.y=self.row_depth=0.
    def tick(self):
        if self.paused or not self.queue:return
        asset=self.queue.pop(0);key=None
        try:
            result=self.library.spawn(asset,[0.,0.,0.,1.,*self.origin,0.,1.,1.,1.,0.]);key=result['id'];self.owned.append(key)
            center,extent=self.menu.bounds(key);width=max(50.,extent[1]*2);depth=max(50.,extent[0]*2)
            if self.tight:
                if self.y and self.y+width>max(3000.,self.spacing*6):self.x+=self.row_depth+50.;self.y=0.;self.row_depth=0.
                pos=[self.origin[0]+self.x+depth/2,self.origin[1]+self.y+width/2,self.origin[2]+extent[2]];self.y+=width+50.;self.row_depth=max(self.row_depth,depth)
            else:
                n=len(self.positions);pos=[self.origin[0]+(n//6)*self.spacing,self.origin[1]+(n%6)*self.spacing,self.origin[2]+extent[2]]
            # Bounds center can differ from actor origin; keep exhibits grounded.
            pos=[pos[i]-(center[i]-self.origin[i]) for i in range(3)]
            self.library.place(key,pos);self.positions.append(pos)
            distance=max(300.,sum(v*v for v in extent)**.5*2.5);target=[center[i]+pos[i]-self.origin[i] for i in range(3)];self.views.append([target[0]-distance,target[1],target[2]+distance*.27,-15,0,0,0,0])
        except Exception as error:
            self.failures.append(dict(asset=asset,error=str(error)))
            if key is not None:self.library.delete(key);self.owned.remove(key)
        self.library.message=self.summary()
    def summary(self):return f'Gallery batch {self.index+1}/{max(1,math.ceil(len(self.assets)/self.size))}: {len(self.positions)} placed, {len(self.queue)} queued, {len(self.failures)} failed'+(' / paused' if self.paused else '')
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
        if type(size)!=int or not 1<=size<=100 or not 50<=spacing<=100000 or len(origin)!=3 or any(not math.isfinite(v) or abs(v)>1e7 for v in origin):raise ValueError('Invalid saved gallery layout')
        self.assets=assets;self.size=size;self.spacing=spacing;self.origin=origin;self.tight=bool(d['tight']);self.index=int(d['index']);self.request(0)
