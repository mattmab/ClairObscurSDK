"""Game-enumerated asset catalog, owned spawning and portable scene tracking."""
import json, math, struct, uuid, time
from pathlib import Path
from expedition33.catalog import capture, capture_selected, capture_matching
from expedition33.values import read_values_with_references
from .reads import reads
from . import thumbnail_cache as cache
from .scenes import MapStore,FORMAT,validate,pose

class Library:
    def __init__(self,mod):
        self.mod=mod;self._catalog=None;self.rows=[];self.known={};self.owned={};self.world=None
        self.store=MapStore(Path(__file__).resolve().parents[2]/'settings'/'E33WorldBuilder'/'maps')
        self.registry_paths=cache.read_catalog();self.registry_complete=self.registry_paths is not None
        self.registry_names_ready=False;self.loader_metadata=[];self.profile={};self.preview_key=None;self.selected=None;self.message='Browse game assets or refresh the catalog.'
    def refresh(self,force=True,observed=None):
        with reads(self.mod.session.pid):
            c=observed if observed is not None else capture();rows=[]
            for o in c.select('StaticMesh',exact=True):
                if o.object_flags&0x30:continue
                p=c.path_name(o)
                if p.startswith(('/Game/','/Engine/')):rows.append(dict(path=p,name=o.name,kind='mesh',source='loaded game objects'))
            actor=c.find_class('Actor').index
            excluded={'Pawn','Controller','GameModeBase','GameStateBase','PlayerState','LevelScriptActor','WorldSettings','GameNetworkManager','PlayerCameraManager','SceneCapture','CameraActor'}
            # Only classes with observed world instances are eligible. This also
            # excludes abstract base classes and uninstantiated generated classes.
            instances={o.class_index for o in c.select('Actor') if not o.object_flags&0x30 and o.outer_index>=0 and c.by_index[o.outer_index].class_name=='Level'}
            for index in instances:
                cls=c.by_index[index];ancestors={c.classes[i].name for i in c.ancestors(index)}
                if actor not in c.ancestors(index) or ancestors&excluded or any(k in cls.name.casefold() for k in ('enemy','combat','quest','trigger','checkpoint','portal','savepoint')):continue
                rows.append(dict(path=c.path_name(cls),name=cls.name,kind='actor',source='instantiated game actor class'))
            self._catalog=c
            if self.mod.active and (force or not self.registry_complete):
                self.registry_paths=[]
                loaded={r['path'] for r in rows}
                offset=0
                while True:
                    self.mod.command(35,registry_offset=offset);raw=self.mod.last_raw
                    total,count=struct.unpack_from('<II',raw,3560)
                    if count>32 or total>250000 or offset+count>total:raise RuntimeError('Invalid registry page')
                    for i in range(count):
                        path=raw[4096+i*512:4096+(i+1)*512].split(b'\0',1)[0].decode('ascii')
                        self.registry_paths.append(path)
                        if path not in loaded:
                            rows.append(dict(path=path,name=path.rsplit('.',1)[-1],kind='mesh',source='asset_registry'))
                            loaded.add(path)
                    offset+=count
                    if offset==total:break
                    if not count:raise RuntimeError('Registry enumeration made no progress')
                self.registry_complete=True;cache.write_catalog(self.registry_paths)
            elif self.registry_paths:
                loaded={r['path'] for r in rows}
                rows.extend(dict(path=p,name=p.rsplit('.',1)[-1],kind='mesh',source='asset_registry') for p in self.registry_paths if p not in loaded)
            self.rows=sorted(rows,key=lambda r:(r['kind'],r['name'].casefold(),r['path']))
            self.known={r['path']:r for r in self.rows}
            self.message=f'{len(self.rows)} game-enumerated meshes and actor classes'
        return dict(count=len(self.rows),source='asset registry and loaded game objects',message=self.message)
    def catalog(self,query='',kind='',offset=0,limit=8):
        if not self.rows:self.refresh(force=False)
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:raise ValueError('Invalid catalog page')
        rows=[r for r in self.rows if (not kind or r['kind']==kind) and query.casefold() in r['path'].casefold()]
        return dict(count=len(rows),rows=rows[offset:offset+limit],offset=offset)
    def context(self):
        with reads(self.mod.session.pid):
            if self._catalog is None:self.refresh(force=False)
            fresh=capture_matching(self.mod.session.pid,classes=('PlayerController',))
            c=fresh;pc=next(o for o in c.select('PlayerController') if not o.object_flags&0x30)
            v,c=read_values_with_references(c,pc,fields=('Pawn','PlayerCameraManager','ControlRotation'))
            d={k[1]:v for k,v in v.values.items()};pawn=d['Pawn'];outer=c.by_index[pawn.outer_index]
            while outer.class_name!='World' and outer.outer_index>=0:outer=c.by_index[outer.outer_index]
            world=c.path_name(outer)
            self.world=world
            return c,pc,d,world
    def mark(self,name,started):
        elapsed=time.perf_counter()-started
        row=self.profile.setdefault(name,dict(count=0,total_ms=0.,max_ms=0.))
        row['count']+=1;row['total_ms']+=elapsed*1000;row['max_ms']=max(row['max_ms'],elapsed*1000)
        return time.perf_counter()
    def spawn(self,asset,transform=None):
        if not self.mod.active:self.mod.toggle()
        if not self.rows:self.refresh(force=False)
        row=self.known.get(asset)
        if row is None:raise ValueError('Select an asset from the current game catalog')
        started=time.perf_counter();c,pc,d,world=self.context();started=self.mark('context',started)
        if self.owned and any(v['world']!=world for v in self.owned.values()):raise ValueError('Clear the previous level session first')
        if transform is None:
            rotation=d['ControlRotation'].fields;pitch=math.radians(rotation['Pitch']);yaw=math.radians(rotation['Yaw'])
            loc=self.mod.last['position'];direction=(math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch))
            transform=[0.,0.,0.,1.,*[loc[i]+direction[i]*450 for i in range(3)],0.,1.,1.,1.,0.]
        transform=pose(transform)
        if row['kind']=='mesh' and (asset in (self.registry_paths or []) or asset=='/Engine/BasicShapes/Cube.Cube'):
            from .bulk import spawn_batch
            result=spawn_batch(self,[(asset,transform)])[0]
            if result.get('error'):raise RuntimeError(result['error'])
            self.message='Spawned '+row['name'];return result
        load_scope=None
        if row['kind']=='mesh':
            from expedition33._scope import SessionScope
            from expedition33.assets import load_asset
            load_scope=SessionScope(self.mod.session)
            try:
                loaded=load_asset(load_scope,asset);obj=loaded.return_value
                if obj is None:raise ValueError('Game could not load this registered asset')
            except Exception:
                load_scope.close();raise
        else:
            fresh=capture_matching(self.mod.session.pid,names=(row['name'],));obj=fresh.find_path(asset)
        started=self.mark('load_asset',started)
        if row['kind']=='mesh':
            fresh=capture_matching(self.mod.session.pid,names=('StaticMeshActor',));cls=fresh.by_index[fresh.find_class('StaticMeshActor').index]
        else:cls=obj
        started=self.mark('class_lookup',started)
        try:raw=self.mod.scene_command(31,objects=(obj if row['kind']=='mesh' else None,cls),transform=transform)
        finally:
            if load_scope is not None:load_scope.close()
        self.mark('spawn_and_release',started)
        actor=struct.unpack_from('<iiQ',raw,3568);component=struct.unpack_from('<iiQ',raw,3584)
        key=uuid.uuid4().hex;self.owned[key]=dict(id=key,kind=row['kind'],asset=asset,actor=actor,component=component,world=world)
        self.selected=key;self.message='Spawned '+row['name'];return dict(id=key,asset=asset,actor_index=actor[0],component_index=component[0])
    def snapshot(self,name):
        from .bulk import snapshot
        return snapshot(self,name)
    def save(self,name='Builder map'):
        with reads(self.mod.session.pid):data=self.snapshot(name)
        key=self.store.save(data);self.active_map=key;self.message=f"Saved {name}: {len(data['objects'])} objects";return dict(id=key,path=str(self.store.file(key)),objects=len(data['objects']))
    def load(self,map_id):
        with reads(self.mod.session.pid):return self._load(map_id)
    def _load(self,map_id):
        self.clear_preview()
        if not self.mod.active:self.mod.toggle()
        c,pc,d,world=self.context();data=validate(self.store.read(map_id),world)
        if self.owned or self.mod.last.get('edits'):raise ValueError('Save or clear the current tracked scene before loading another')
        if not self.rows:self.refresh(force=False)
        # Complete identity/availability preflight before the first mutation.
        c=capture()
        plans=[]
        for row in data['objects']:
            if row['kind']=='world_edit':
                asset=c.find_path(row['asset'])
                component=c.find_path(row['component']);v,c=read_values_with_references(c,component,fields=('StaticMesh',));mesh=next(v for k,v in v.values.items() if k[1]=='StaticMesh')
                if mesh!=asset:raise ValueError('Saved world component now uses a different asset')
                plans.append((row,component))
            else:
                if row['asset'] not in self.known or self.known[row['asset']]['kind']!=row['kind']:raise ValueError('Saved asset is unavailable in this game catalog')
                plans.append((row,None))
        from .bulk import prepare,spawn_batch
        prepare(self)
        try:
            meshes=[row for row,component in plans if component is None and row['kind']=='mesh' and not row.get('component_edits') and (row['asset'] in self.bulk_indices or row['asset']=='/Engine/BasicShapes/Cube.Cube')]
            batched_ids={row['id'] for row in meshes}
            at=0
            while at<len(meshes):
                chunk=meshes[at:at+64];results=spawn_batch(self,[(row['asset'],row['transform']) for row in chunk],prepared=True)
                for row,result in zip(chunk,results):
                    if result.get('error'):raise RuntimeError(row['asset']+': '+result['error'])
                    tracked=self.owned.pop(result['id']);tracked['id']=row['id'];self.owned[row['id']]=tracked
                at+=len(results);self.message=f'Loading {at}/{len(meshes)} meshes'
            for row,component in plans:
                if row['id'] in batched_ids:continue
                if component:self.mod.scene_command(30,objects=(component,),transform=row['transform'])
                else:
                    result=self.spawn(row['asset'],row['transform']);tracked=self.owned.pop(result['id']);tracked['id']=row['id'];self.owned[row['id']]=tracked
                    if row.get('component_edits'):
                        current=capture();actor=current.by_index[tracked['actor'][0]];actor_path=current.path_name(actor)
                        for child in row['component_edits']:
                            target=current.find_path(actor_path+child['component']);v,current=read_values_with_references(current,target,fields=('StaticMesh',));mesh=next(v for k,v in v.values.items() if k[1]=='StaticMesh')
                            if current.path_name(mesh)!=child['asset']:raise ValueError('Spawned actor component does not match the saved asset')
                            self.mod.scene_command(30,objects=(target,),transform=child['transform'])
        except Exception:
            from .bulk import delete_many
            delete_many(self,list(self.owned));self.mod.restore();self.owned.clear();raise
        self.active_map=map_id
        self.message=f"Loaded {data['name']}: {len(plans)} objects";return dict(name=data['name'],objects=len(plans))
    def clear(self):
        from .bulk import delete_many
        delete_many(self,list(self.owned));self.mod.restore();self.owned.clear();self.active_map=None;self.selected=None;self.message='Tracked scene cleared';return dict(cleared=True)

    def duplicate(self,key):
        row=next(r for r in self.snapshot('Duplicate')['objects'] if r['id']==key)
        transform=list(row['transform']);transform[5]+=100.
        result=self.spawn(row['asset'],transform)
        try:
            if row.get('component_edits'):
                c=capture();record=self.owned[result['id']];actor=c.by_index[record['actor'][0]];prefix=c.path_name(actor)
                for child in row['component_edits']:
                    target=c.find_path(prefix+child['component']);v,c=read_values_with_references(c,target,fields=('StaticMesh',));mesh=next(v for k,v in v.values.items() if k[1]=='StaticMesh')
                    if c.path_name(mesh)!=child['asset']:raise ValueError('Duplicated component does not match saved asset')
                    pose=list(child['transform']);pose[5]+=100.;self.mod.scene_command(30,objects=(target,),transform=pose)
        except Exception:
            self.delete(result['id']);raise
        return result
    def delete(self,key):
        from .bulk import delete_many
        delete_many(self,[key])
    def place(self,key,position):
        record=self.owned[key]
        with reads(self.mod.session.pid):
            c=capture_selected(self.mod.session.pid,[tuple(record['component'])]);component=c.by_index[record['component'][0]]
        self.mod.scene_command(30,objects=(component,),transform=[0.,0.,0.,1.,*position,0.,1.,1.,1.,0.])
    def clear_preview(self):
        if self.preview_key is None:return
        record=self.owned.get(self.preview_key)
        if record:
            # Native deletion checks this identity against its owned actor list;
            # cleanup must also work after a failed read or self-destroyed actor.
            from types import SimpleNamespace
            actor=SimpleNamespace(**dict(zip(('index','serial','address'),record['actor'])))
            self.mod.scene_command(33,objects=(actor,));self.owned.pop(self.preview_key,None)
        self.preview_key=None
    def thumbnail_names(self,asset):
        if not self.registry_names_ready:
            self.mod.command(35,registry_offset=0);self.registry_names_ready=True
        self.mod.command(47,asset_path=asset)
        package_id,asset_id=struct.unpack_from('<II',self.mod.last_raw,3568)
        return dict(package_id=package_id,asset_id=asset_id)
    def thumbnail_preview(self,asset):
        # Dedicated native-owned mesh/capture scene. It is excluded from scene
        # saves and reused until cancellation, freecam exit, or mod shutdown.
        from expedition33._scope import SessionScope
        from .asset_loader import load_asset
        row=self.known.get(asset)
        if not row or row['kind']!='mesh':raise ValueError('Thumbnail worker requires a catalog mesh')
        started=time.perf_counter();scope=SessionScope(self.mod.session)
        try:
            loaded=load_asset(scope,asset,self.loader_metadata,self.mark,self.thumbnail_names);obj=loaded.return_value
            if obj is None:raise ValueError('Game could not load this registered asset')
            started=self.mark('thumbnail_load',started)
            self.mod.scene_command(46,objects=(obj,));self.mark('thumbnail_swap_capture',started)
        finally:scope.close()
    def preview(self,asset):
        self.clear_preview()
        position=self.mod.last['position'];transform=[0.,0.,0.,1.,position[0],position[1],position[2]+100000.,0.,1.,1.,1.,0.]
        started=time.perf_counter();result=self.spawn(asset,transform);started=self.mark("spawn_total",started);self.preview_key=result['id'];record=self.owned[self.preview_key]
        with reads(self.mod.session.pid):
            c=capture_selected(self.mod.session.pid,[tuple(record['actor'])]);actor=c.by_index[record['actor'][0]]
        started=self.mark("observe_actor",started)
        raw=self.mod.scene_command(34,objects=(actor,));started=self.mark("capture_setup",started);identity=struct.unpack_from('<iiQ',raw,3568)
        with reads(self.mod.session.pid):
            c=capture_selected(self.mod.session.pid,[identity]);texture=c.by_index[identity[0]]
        self.mark("observe_texture",started)
        self.message='Preview: '+self.known[asset]['name']
        return texture,c
