"""Region copies with portable transforms and transactional group placement."""
import json, math, time, uuid, struct
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from .scenes import MapStore, FORMAT, pose, validate


def vector(value):
    value=getattr(value,'fields',value)
    return [float(value[k]) for k in ('X','Y','Z')]


def transform(value):
    value=getattr(value,'fields',value)
    q=getattr(value['Rotation'],'fields',value['Rotation'])
    return pose([*[float(q[k]) for k in ('X','Y','Z','W')],*vector(value['Translation']),0.,*vector(value['Scale3D']),0.])


def placed(source,origin,delta,yaw):
    if len(delta)!=3 or not all(math.isfinite(v) and abs(v)<1e7 for v in (*origin,*delta,yaw)):
        raise ValueError('Placement values must be finite and within world limits')
    p=pose(source);a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    x,y,z=p[4:7];p[4:7]=[origin[0]+delta[0]+c*x-s*y,origin[1]+delta[1]+s*x+c*y,origin[2]+delta[2]+z]
    x,y,z,w=p[:4];s,c=math.sin(a/2),math.cos(a/2)
    p[:4]=[c*x-s*y,c*y+s*x,c*z+s*w,c*w-s*z]
    return pose(p)


def framed_origin(rows,position,rotation):
    # Center the group ahead of the camera, allowing space for large structures.
    low=[min(r['transform'][4+i]-100*abs(r['transform'][8+i]) for r in rows) for i in range(3)]
    high=[max(r['transform'][4+i]+100*abs(r['transform'][8+i]) for r in rows) for i in range(3)]
    center=[(a+b)/2 for a,b in zip(low,high)]
    # Large structures must remain nearby: full-group framing can place them
    # hundreds of metres away, underground or behind streamed scenery.
    distance=min(5000.,max(500.,math.sqrt(sum(((b-a)/2)**2 for a,b in zip(low,high)))*2.5))
    pitch,yaw=map(math.radians,rotation[:2])
    forward=[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)]
    return [p+f*distance-c for p,f,c in zip(position,forward,center)]


def inside(point,low,high):return all(a<=v<=b for v,a,b in zip(point,low,high))


def region_quaternion(angles):
    if len(angles)!=3 or not all(math.isfinite(v) and abs(v)<=360000 for v in angles):raise ValueError('Rotation angles must be finite degrees')
    r,p,y=[math.radians(v)/2 for v in angles]
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
    return [sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy]

def rotate_point(point,center,q):
    x,y,z=[v-c for v,c in zip(point,center)];a,b,c,w=q
    tx,ty,tz=2*(b*z-c*y),2*(c*x-a*z),2*(a*y-b*x)
    return [center[0]+x+w*tx+b*tz-c*ty,center[1]+y+w*ty+c*tx-a*tz,center[2]+z+w*tz+a*ty-b*tx]

def region_contains(point,low,high,angles):
    q=region_quaternion(angles);q[:3]=[-v for v in q[:3]]
    return inside(rotate_point(point,[(a+b)/2 for a,b in zip(low,high)],q),low,high)


class Templates:
    def __init__(self,library):
        self.library=library;self.mod=library.mod
        self.store=MapStore(library.store.root.parent/'templates')
        self.angles=[0.,0.,0.];self.points=[None,None];self.world=None;self.job=None;self.draft=[];self.queue=[];self.moves=[]
        self.scan_worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='region-discovery');self.scan_future=None
        self.failed=False;self.origin=[0.,0.,0.];self.delta=[0.,0.,0.];self.yaw=0.;self.draw_at=0.;self.planner=None;self.lines=[];self.line_queue=[]
    def mark(self,number):
        if number not in (1,2):raise ValueError('Corner must be 1 or 2')
        if self.queue or self.moves or self.draft:raise ValueError('Apply or cancel the template placement first')
        if not self.mod.active or self.mod.booth_pending:raise ValueError('Use the builder camera to mark corners')
        if self.job:raise ValueError('Wait for the region scan to finish')
        _,_,_,world=self.library.context()
        if world!=self.world:self.points=[None,None];self.world=world
        self.mod.command(26);self.points[number-1]=list(self.mod.last['position'])
        self.update_box()
        self.library.message=f'Corner {number}: '+', '.join(f'{v:.0f}' for v in self.points[number-1])
        return self.status()
    def status(self):
        return dict(corners=self.points,rotation=self.angles,scanning=bool(self.job),pending=len(self.queue)+len(self.moves),preview=len(self.draft),message=self.library.message)
    def function(self,owner,name):
        return next(o for o in self.catalog.objects if o.name==name and o.class_name=='Function' and self.catalog.by_index[o.outer_index].name==owner)
    def invoke(self,obj,owner,name,**args):
        with self.planner.prepare(obj,self.function(owner,name),**args).invoke() as r:
            return r.return_value,dict(r.outputs)
    def setup(self):
        from expedition33.catalog import capture
        self.catalog=capture();self.planner=self.mod.session.invocation_planner(selected_results=True,catalog=self.catalog)
    def save(self,name):
        if self.job or self.queue or self.draft:raise ValueError('Finish the current scan or placement first')
        if any(p is None for p in self.points):raise ValueError('Mark both corners with F3 and F4')
        _,_,_,world=self.library.context()
        if world!=self.world:raise ValueError('Corners belong to another level; mark them again')
        low=[min(a,b) for a,b in zip(*self.points)];high=[max(a,b) for a,b in zip(*self.points)]
        if any(b-a<1 for a,b in zip(low,high)):raise ValueError('Region must have width, depth and height')
        # Validate the name before starting engine work.
        validate(dict(format=FORMAT,version=1,name=name,world=world,objects=[],assets=[]))
        if self.scan_future is not None and not self.scan_future.done():raise ValueError('Previous discovery is finishing; try again shortly')
        from expedition33.catalog import capture
        self.failed=False;self.scan_future=self.scan_worker.submit(capture)
        self.job=dict(name=name,world=world,low=low,high=high,objects=None,index=0,rows=[],skipped=0,assets={},pending=[],angles=list(self.angles))
        q=region_quaternion(self.angles);center=[(a+b)/2 for a,b in zip(low,high)]
        corners=[rotate_point([x,y,z],center,q) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])]
        self.job['query_low']=[min(p[i] for p in corners) for i in range(3)];self.job['query_high']=[max(p[i] for p in corners) for i in range(3)]
        self.library.message='Discovering loaded components in background; Cancel scan is available'
        return self.status()
    def add(self,asset,p):
        j=self.job
        if not region_contains(p[4:7],j['low'],j['high'],j.get('angles',[0.,0.,0.])):return
        if len(j['rows'])>=5900:raise ValueError('Region exceeds 5900 props; choose a smaller region')
        p=list(p);p[4:7]=[v-a for v,a in zip(p[4:7],j['low'])]
        j['rows'].append(dict(id=uuid.uuid4().hex,kind='mesh',asset=asset,transform=pose(p)))
    def scan_one(self):
        from expedition33.values import read_values_with_references
        j=self.job
        if j['objects'] is None:
            if not self.scan_future.done():return
            self.catalog=self.scan_future.result();self.scan_future=None
            if self.catalog.pid!=self.mod.session.pid:raise ValueError('Game session changed during discovery')
            j['objects']=[o for o in self.catalog.select('StaticMeshComponent') if not o.object_flags&0x30]
            return
        if j['pending']:
            from expedition33.values import read_values_many
            hits=j['pending'][:64]
            needed={identity:self.catalog.by_index[identity[0]] for identity,p in hits if identity not in j['assets']}
            if needed:
                observed=read_values_many(self.catalog,list(needed.values()),fields=('StaticMesh',))
                for identity,obj in needed.items():
                    values=observed[obj.index];mesh=next((v for k,v in values.values.items() if k[1]=='StaticMesh'),None)
                    if values.errors:
                        # A mesh loaded after discovery needs a fresh reference closure.
                        values,c=read_values_with_references(self.catalog,obj,fields=('StaticMesh',))
                        mesh=next(v for k,v in values.values.items() if k[1]=='StaticMesh')
                    else:c=self.catalog
                    j['assets'][identity]=c.path_name(mesh) if mesh else None
            for identity,p in hits:
                asset=j['assets'][identity]
                if asset:self.add(asset,p)
            del j['pending'][:len(hits)]
            self.library.message=f"Scanning {j['index']}/{len(j['objects'])} components; {len(j['rows'])}/5900 meshes"
            return
        if j['index']>=len(j['objects']):
            if not j['rows']:raise ValueError('No loaded visible mesh origins inside this region')
            data=dict(format=FORMAT,version=1,name=j['name'],world=j['world'],objects=j['rows'],assets=sorted({r['asset'] for r in j['rows']}))
            key=self.store.save(data);self.job=None
            self.library.message=f"Saved template: {data['name']} ({len(data['objects'])} meshes)"
            self.last_saved=key;return
        batch=j['objects'][j['index']:j['index']+64]
        self.mod.command(65,bulk=batch,region=(j['query_low'],j['query_high'],j.get('instance',0)))
        raw=self.mod.last_raw
        count,consumed,instance,skipped=struct.unpack_from('<4I',raw,3560)
        if count>64 or consumed>len(batch) or (not consumed and not count and instance==j.get('instance',0)):raise RuntimeError('Invalid region scan progress')
        excluded={tuple(r['component']) for r in self.library.owned.values() if r.get('duplication_preview') or r['id']==self.library.preview_key}
        for i in range(count):
            at=4096+128*i;identity=struct.unpack_from('<iiQ',raw,at)
            if identity in excluded:continue
            obj=self.catalog.by_index[identity[0]]
            if (obj.serial,obj.address)!=identity[1:]:raise ValueError('Region changed while scanning; mark it again')
            p=pose(list(struct.unpack_from('<12d',raw,at+16)))
            if region_contains(p[4:7],j['low'],j['high'],j.get('angles',[0.,0.,0.])):j['pending'].append((identity,p))
        j['index']+=consumed;j['instance']=instance;j['skipped']+=skipped
        self.library.message=f"Scanning {j['index']}/{len(j['objects'])}; {len(j['rows'])} meshes in region"
    def begin(self,key):
        if self.job:raise ValueError('Wait for the region scan')
        self.cancel();self.clear_box()
        from .bulk import prepare,SCENE_LIMIT
        data=self.store.read(key)
        if not data['objects']:raise ValueError('Template is empty')
        if len(self.library.owned)+len(data['objects'])>SCENE_LIMIT-16:raise ValueError('Not enough scene capacity')
        prepare(self.library)
        if any(r['kind']!='mesh' or r['asset'] not in self.library.bulk_indices and r['asset']!='/Engine/BasicShapes/Cube.Cube' for r in data['objects']):raise ValueError('Template contains assets unavailable in this game catalog')
        self.mod.command(26);self.origin=framed_origin(data['objects'],self.mod.last['position'],self.mod.last['rotation']);self.delta=[0.,0.,0.];self.yaw=0.
        self.failed=False;self.draft_world=self.library.world;self.queue=list(data['objects']);self.total=len(self.queue)
        self.library.message=f'Placing template: 0/{self.total}. Apply keeps it; Cancel removes it.'
    def bring_here(self):
        rows=[row for _,row in self.draft]+list(self.queue)
        if not rows:raise ValueError('Preview a template first')
        rotated=[dict(row,transform=placed(row['transform'],[0.,0.,0.],[0.,0.,0.],self.yaw)) for row in rows]
        self.mod.command(26)
        self.origin=framed_origin(rotated,self.mod.last['position'],self.mod.last['rotation'])
        self.reposition([0.,0.,0.],self.yaw)
    def reposition(self,delta,yaw):
        if not self.draft and not self.queue:raise ValueError('Preview a saved template first')
        if len(delta)!=3 or not all(math.isfinite(v) for v in delta) or not math.isfinite(yaw):raise ValueError('Placement XYZ and yaw must be finite')
        planned=[(key,placed(row['transform'],self.origin,delta,yaw)) for key,row in self.draft]
        self.delta=list(delta);self.yaw=yaw;self.moves=planned
        self.library.message=f'Updating placement: {len(planned)} existing props; new props use the latest position'
    def apply(self):
        if self.queue or self.moves:raise ValueError(f'Placement updating: {len(self.queue)} props to spawn, {len(self.moves)} to move')
        if not self.draft:raise ValueError('Preview a template first')
        if self.failed:raise ValueError('Placement failed; cancel and preview again')
        for key,_ in self.draft:self.library.owned[key].pop('duplication_preview',None)
        count=len(self.draft);self.draft=[];self.library.message=f'Applied template: {count} props tracked for map saving'
    def cancel(self):
        from .bulk import delete_many
        self.queue=[];self.moves=[]
        delete_many(self.library,[key for key,_ in self.draft]);self.draft=[]
    def clear_box(self):
        from .bulk import delete_many
        delete_many(self.library,self.lines);self.lines=[];self.line_queue=[];self.line_moves=[]
    def rotate_bounds(self,angles):
        if self.job:raise ValueError('Cancel the scan before changing the bounds')
        region_quaternion(angles)
        self.angles=[((v+180)%360)-180 for v in angles];self.update_box()
        self.library.message='Selection rotation (roll, pitch, yaw): '+', '.join(f'{v:g}' for v in self.angles)

    def adjust_bounds(self,mode,axis,amount,corner=None):
        if self.job:raise ValueError('Cancel the scan before changing bounds')
        if any(p is None for p in self.points):raise ValueError('Mark both corners with F3 and F4 first')
        if mode not in ('Move','Rotate','Resize','Scale') or axis not in (0,1,2,3) or not math.isfinite(amount):raise ValueError('Invalid bounds adjustment')
        if corner is not None and corner not in range(8):raise ValueError('Invalid selection corner')
        if axis==3 and mode!='Scale':raise ValueError('Uniform adjustment requires Scale mode')
        if mode=='Rotate':
            angles=list(self.angles);angles[axis]+=amount;self.rotate_bounds(angles);return
        low=[min(a,b) for a,b in zip(*self.points)];high=[max(a,b) for a,b in zip(*self.points)]
        center=[(a+b)/2 for a,b in zip(low,high)];size=[b-a for a,b in zip(low,high)]
        q=region_quaternion(self.angles)
        signs=[1 if corner is not None and corner&(1<<i) else -1 for i in range(3)]
        if mode=='Move':
            delta=[amount if i==axis else 0. for i in range(3)]
            if corner is None:center=[c+d for c,d in zip(center,delta)]
            else:
                inverse=[-q[0],-q[1],-q[2],q[3]]
                local=rotate_point(delta,[0,0,0],inverse)
                size=[v+d*sign for v,d,sign in zip(size,local,signs)]
                center=[c+d/2 for c,d in zip(center,delta)]
        else:
            change=[(v*amount/100 if mode=='Scale' else amount) if axis==3 or i==axis else 0. for i,v in enumerate(size)]
            size=[v+d for v,d in zip(size,change)]
            if corner is not None:
                shift=rotate_point([d*sign/2 for d,sign in zip(change,signs)],[0,0,0],q)
                center=[c+d for c,d in zip(center,shift)]
        if any(v<1 or v>1e7 for v in size) or any(not math.isfinite(v) or abs(v)>1e7 for v in center):raise ValueError('Selection dimensions must stay between 1 and 10000000 units')
        self.points=[[c-v/2 for c,v in zip(center,size)],[c+v/2 for c,v in zip(center,size)]]
        self.update_box()
        self.library.message=mode+' selection: '+', '.join(f'{v:g}' for v in size)+' units'

    def update_box(self):
        existing=list(self.lines)
        self.line_queue=[]
        self.line_moves=[]
        if all(p is None for p in self.points):self.clear_box();return
        from .bulk import prepare
        prepare(self.library)
        if any(p is None for p in self.points):
            self.clear_box()
            point=next(p for p in self.points if p is not None)
            self.line_queue.append(pose([0.,0.,0.,1.,*point,0.,.3,.3,.3,0.]))
            return
        low=[min(a,b) for a,b in zip(*self.points)];high=[max(a,b) for a,b in zip(*self.points)]
        thickness=max(.08,min(.5,max(b-a for a,b in zip(low,high))/50000))
        for axis in range(3):
            others=[i for i in range(3) if i!=axis]
            for a in (0,1):
                for b in (0,1):
                    location=[(x+y)/2 for x,y in zip(low,high)];scale=[thickness]*3
                    location[others[0]]=(low,high)[a][others[0]];location[others[1]]=(low,high)[b][others[1]]
                    scale[axis]=max(.02,(high[axis]-low[axis])/100)
                    q=region_quaternion(self.angles);center=[(x+y)/2 for x,y in zip(low,high)]
                    location=rotate_point(location,center,q)
                    self.line_queue.append(pose([*q,*location,0.,*scale,0.]))
        corner=getattr(self,'selected_corner',None)
        if corner is not None:
            location=rotate_point([(high if corner&(1<<i) else low)[i] for i in range(3)],center,q)
            marker=max(.6,thickness*5)
            self.line_queue.append(pose([*q,*location,0.,marker,marker,marker,0.]))
        if len(existing)>=12 and all(key in self.library.owned for key in existing):
            # Keep the twelve edges alive, including when adding/removing the corner marker.
            poses=self.line_queue
            if len(existing)>len(poses):
                from .bulk import delete_many
                delete_many(self.library,existing[len(poses):]);self.lines=existing[:len(poses)]
                existing=list(self.lines)
            self.line_moves=list(zip(existing,poses));self.line_queue=poses[len(existing):]
        else:
            poses=self.line_queue;self.clear_box();self.line_queue=poses

    def cancel_scan(self):
        self.job=None
        if self.scan_future is not None:self.scan_future.cancel()
        self.library.message='Template scan cancelled; corners kept'

    def close(self):
        self.cancel_scan();self.scan_worker.shutdown(wait=False,cancel_futures=True)
        self.job=None;self.cancel();self.clear_box();self.points=[None,None]

    def poll(self):
        try:
            if (self.job or self.queue or self.moves or self.line_queue or getattr(self,'line_moves',[])) and not self.mod.active:
                self.job=None;self.cancel();self.clear_box();return
            if getattr(self,'line_moves',[]):
                moves=self.line_moves;self.line_moves=[]
                for key,p in moves:
                    row=self.library.owned[key]
                    component=SimpleNamespace(**dict(zip(('index','serial','address'),row['component'])))
                    self.mod.scene_command(30,objects=(component,),transform=p)
            elif self.line_queue:
                from .bulk import spawn_batch,CUBE
                result=spawn_batch(self.library,[(CUBE,p) for p in self.line_queue[:8]],prepared=True)
                for row in result:
                    if 'error' in row:continue
                    self.lines.append(row['id']);self.library.owned[row['id']]['duplication_preview']=True
                if any('error' in row for row in result):self.line_queue=[];raise RuntimeError('Region box could not be created')
                del self.line_queue[:len(result)]
            elif self.job:
                # Resolve references in batches, with a bounded controller budget.
                deadline=time.monotonic()+.06
                with self.mod.menu_reads():
                    for _ in range(8):
                        self.scan_one()
                        if not self.job or self.job['objects'] is None or time.monotonic()>=deadline:break
            elif self.queue:
                from .bulk import spawn_batch
                rows=self.queue[:64]
                result=spawn_batch(self.library,[(r['asset'],placed(r['transform'],self.origin,self.delta,self.yaw)) for r in rows],prepared=True)
                for row,created in zip(rows,result):
                    if 'error' in created:continue
                    self.library.owned[created['id']]['duplication_preview']=True;self.draft.append((created['id'],row))
                if any('error' in row for row in result):raise RuntimeError('Some template assets failed to spawn')
                del self.queue[:len(result)]
                self.library.message=f'Preview {len(self.draft)}/{self.total}. Adjust XYZ/yaw then Apply.'
            elif self.moves:
                from .bulk import transform_batch
                deadline=time.monotonic()+.04
                for _ in range(16):
                    if not self.moves:break
                    done=transform_batch(self.library,self.moves)
                    del self.moves[:done]
                    if time.monotonic()>=deadline:break
                self.library.message=f'Updating placement: {len(self.moves)} props remaining' if self.moves else f'Preview ready: {len(self.draft)} props. Apply to keep.'

        except Exception as exc:
            self.failed=True
            self.job=None;self.queue=[];self.moves=[]
            self.library.message='Template operation stopped: '+str(exc)+'; Cancel removes any preview copies.'
            self.draw_at=float('inf')
