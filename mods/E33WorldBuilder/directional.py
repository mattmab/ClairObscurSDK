"""Single-selected-prop duplication; no folder or scene duplication."""
import math,time
from types import SimpleNamespace


def offsets(transform,axis,sign,count,spacing,local=False):
    if axis not in ('X','Y','Z') or sign not in (-1,1):
        raise ValueError('Choose X, Y or Z and a positive or negative direction')
    if isinstance(count,bool) or int(count)!=count or not 1<=count<=250:
        raise ValueError('Copy count must be a whole number from 1 to 250')
    if not math.isfinite(spacing) or spacing<=0:
        raise ValueError('Spacing must be a positive finite number of game units (cm)')
    direction=[float(axis==a) for a in ('X','Y','Z')]
    if local:
        x,y,z,w=transform[:4]
        norm=math.sqrt(x*x+y*y+z*z+w*w)
        if not math.isfinite(norm) or norm<1e-8:raise ValueError('Selected prop has an invalid rotation')
        x,y,z,w=(v/norm for v in (x,y,z,w))
        # Quaternion rotate the chosen local unit axis, without scaling spacing.
        vx,vy,vz=direction
        tx,ty,tz=2*(y*vz-z*vy),2*(z*vx-x*vz),2*(x*vy-y*vx)
        direction=[vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx]
    return [tuple(v*sign*spacing*i for v in direction) for i in range(1,int(count)+1)]


class DirectionalCopies:
    def __init__(self,library):
        self.library=library;self.pending=[];self.source=None;self.completed=0
    def start(self,key,axis,sign,count,spacing,local=False):
        if self.pending:raise ValueError('Wait for the current duplication to finish')
        if key not in self.library.owned or key==self.library.preview_key:
            raise ValueError('Select one spawned scene or gallery prop first')
        source=next((r for r in self.library.snapshot('Duplicate')['objects'] if r['id']==key),None)
        if source is None:raise ValueError('Selected prop is no longer available')
        planned=offsets(source['transform'],axis,sign,count,spacing,local)
        from .bulk import SCENE_LIMIT
        if len(self.library.owned)+len(planned)>SCENE_LIMIT-16:raise ValueError('Not enough scene capacity for these copies')
        self.source=source;self.pending=planned;self.completed=0;self.total=len(planned)
        self.world=self.library.world
        self.library.message=f'Duplicating selected prop: 0/{self.total}'
    def poll(self):
        if not self.pending:return
        key=self.source['id']
        if key not in self.library.owned or self.library.world!=self.world:
            self.pending=[];self.library.message='Duplication stopped: source or map changed';return
        offset=self.pending.pop(0)
        try:
            self.library.duplicate(key,offset,self.source)
            self.library.selected=key
            self.completed+=1
            self.library.message=f'Duplicated selected prop: {self.completed}/{self.total}'
        except Exception as exc:
            self.pending=[];self.library.message=f'Duplication stopped after {self.completed} copies: {exc}'


class DuplicationDraft:
    """Temporary scene copies become map assets only when Apply is pressed."""
    def __init__(self,library):
        self.library=library;self.source=None;self.pending=[];self.previews=[];self.delta=[0.,0.,0.];self.moves=[]
    def begin(self,key):
        self.cancel()
        if key not in self.library.owned or key==self.library.preview_key:raise ValueError('Select one spawned scene prop first')
        self.source=next(r for r in self.library.snapshot('Duplicate')['objects'] if r['id']==key)
        self.world=self.library.world;self.delta=[0.,0.,0.]
    def preview(self,count,delta,local=False):
        if self.source is None:raise ValueError('Select a source prop first')
        if len(delta)!=3 or not all(math.isfinite(v) for v in delta):raise ValueError('XYZ offsets must be finite numbers')
        # Validate the count and rotate each axis using the same quaternion rules.
        unit=offsets(self.source['transform'],'X',1,count,1.,local)
        direction=[0.,0.,0.]
        for axis,value in zip('XYZ',delta):
            basis=offsets(self.source['transform'],axis,1,1,1.,local)[0]
            direction=[a+b*value for a,b in zip(direction,basis)]
        from .bulk import SCENE_LIMIT
        if len(self.library.owned)-len(self.previews)+len(unit)>SCENE_LIMIT-16:raise ValueError('Not enough scene capacity')
        from .bulk import prepare,delete_many,CUBE
        prepare(self.library)
        self.batched=self.source['kind']=='mesh' and not self.source.get('component_edits') and (self.source['asset'] in self.library.bulk_indices or self.source['asset']==CUBE)
        self.delta=list(delta);self.total=len(unit)
        if not self.batched:self.clear_previews()
        if len(self.previews)>self.total:
            delete_many(self.library,self.previews[self.total:]);del self.previews[self.total:]
        planned_offsets=[tuple(v*i for v in direction) for i in range(1,self.total+1)]
        self.moves=[]
        for key,offset in zip(self.previews,planned_offsets):
            p=list(self.source['transform']);p[4:7]=[v+d for v,d in zip(p[4:7],offset)]
            self.moves.append((key,p))
        self.pending=planned_offsets[len(self.previews):]
        self.preview_started=time.monotonic()
        self.library.message='Building temporary preview; Apply keeps the copies'
    def clear_previews(self):
        self.pending=[];self.moves=[]
        from .bulk import delete_many
        delete_many(self.library,self.previews)
        self.previews=[]
    def cancel(self):
        self.clear_previews();self.source=None
    def apply(self):
        if self.pending or getattr(self,'moves',[]):raise ValueError('Preview is updating; Apply when its remaining count reaches zero')
        if not self.previews:raise ValueError('Create a preview first')
        for key in self.previews:self.library.owned[key].pop('duplication_preview',None)
        count=len(self.previews);self.previews=[]
        self.library.message=f'Applied {count} copies; included in map saves'
        return count
    def poll(self):
        if not self.pending and not getattr(self,'moves',[]):return
        if self.source['id'] not in self.library.owned or self.library.world!=self.world:
            self.cancel();self.library.message='Preview cancelled: source or map changed';return
        try:
            if self.pending and getattr(self,'batched',False):
                from .bulk import spawn_batch
                requests=[]
                for offset in self.pending[:64]:
                    p=list(self.source['transform']);p[4:7]=[v+d for v,d in zip(p[4:7],offset)]
                    requests.append((self.source['asset'],p))
                results=spawn_batch(self.library,requests,prepared=True)
                for result in results:
                    if 'error' not in result:
                        self.previews.append(result['id']);self.library.owned[result['id']]['duplication_preview']=True
                if any('error' in r for r in results):raise RuntimeError('Native preview batch failed')
                del self.pending[:len(results)]
            elif self.pending:
                delta=self.pending.pop(0)
                result=self.library.duplicate(self.source['id'],delta,self.source)
                self.previews.append(result['id']);self.library.owned[result['id']]['duplication_preview']=True
            else:
                from .bulk import transform_batch
                deadline=time.monotonic()+.04
                for _ in range(16):
                    if not self.moves:break
                    done=transform_batch(self.library,self.moves)
                    del self.moves[:done]
                    if time.monotonic()>=deadline:break
            self.library.selected=self.source['id']
            remaining=len(self.pending)+len(getattr(self,'moves',[]))
            self.library.message=f'Preview {len(self.previews)}/{self.total}; {remaining} updates remaining | Apply to keep'
        except Exception as exc:
            self.clear_previews()
            self.library.message='Preview failed; no copies applied: '+str(exc)
