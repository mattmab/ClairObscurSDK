"""One-file AI context export and additive, bounded scene import. No executable input."""
import json
import math
import uuid
from pathlib import Path

from .scenes import FORMAT, pose, validate
from .templates import rotate_point


def read_json(path, limit=32*1024*1024):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    with Path(path).open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('JSON file exceeds size limit')
    def invalid(value):raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=invalid)


def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=True,allow_nan=False,separators=(',',':')),encoding='utf8')
    temp.replace(path)


def fields(value,allowed,required=()):
    if type(value) is not dict or set(value)-set(allowed) or set(required)-set(value):
        raise ValueError('Missing or unsupported fields; expected '+', '.join(allowed))


def vector(value,limit=1e7,scale=False):
    if type(value) is not list or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>limit for v in value):
        raise ValueError('Expected three finite numbers within coordinate limits')
    if scale and any(v<.001 or v>10000 for v in value):raise ValueError('Scale must be positive, between .001 and 10000')
    return value


def quaternion(rotation):
    # Unreal FRotator: positive pitch looks up, positive yaw turns +X toward +Y.
    pitch,yaw,roll=[math.radians(v)/2 for v in vector(rotation,360000)]
    sp,cp,sy,cy,sr,cr=math.sin(pitch),math.cos(pitch),math.sin(yaw),math.cos(yaw),math.sin(roll),math.cos(roll)
    return [cr*sp*sy-sr*cp*cy,-cr*sp*cy-sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy]


def multiply(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return [w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]


INSTRUCTIONS = '''Return ONE complete JSON file, no scripts or extra requests. Format e33.ai-scene, version 1. Copy export_id and world exactly. Set name (1-80 characters), objects (array). Each object uses exactly one of asset (catalog ID) or template (template ID), position [x,y,z] in cm relative to origin_cm, optional rotation [pitch,yaw,roll] in degrees (default [0,0,0]), optional scale [x,y,z] (default [1,1,1], positive). Optional repeat {count: integer >=1, step:[x,y,z]} places count copies including the first; step is in export axes, not rotated axes. Templates require uniform scale and expand to their object_count. Total expanded objects must fit remaining_capacity. Use only listed spawnable assets/templates. No edits, deletes, scripts, expressions, or invented IDs. Existing-object rows use quaternion XYZW, NOT Euler angles. Origin is a coordinate reference, NOT an inferred ground surface. Bounds select loaded mesh origins; they are not collision or terrain geometry. Unknown dimensions are null. Inspect existing positions for useful placement heights. All paths refer to installed assets; no game assets are attached. Return valid finite JSON with no ellipses or truncated lists.'''


def export_packet(world,origin,region,paths,context,templates,capacity,names=None):
    names=names or {};all_paths=sorted(set(paths)|{r['asset'] for r in context})
    ids={p:'a'+str(i) for i,p in enumerate(all_paths)};supported=set(paths)
    catalog=[[ids[p],p,names.get(p,{}).get('name',p.rsplit('.',1)[-1]),names.get(p,{}).get('dimensions_cm'),p in supported] for p in all_paths]
    rows=[]
    for row in context:
        p=pose(row['transform']);rows.append([ids[row['asset']],[p[4+i]-origin[i] for i in range(3)],p[:4],p[8:11]])
    descriptions={}
    for key,data in templates.items():
        poses=[r['transform'] for r in data['objects']]
        descriptions[key]={'name':data['name'],'object_count':len(poses),'origin_bounds_cm':[
            [min(p[4+i] for p in poses) for i in range(3)],[max(p[4+i] for p in poses) for i in range(3)]],
            'bounds_note':'Bounds of prop origins only; mesh dimensions may be unknown.'}
    return dict(format='e33.ai-export',version=1,export_id=uuid.uuid4().hex,world=world,
        origin_cm=origin,coordinates={'units':'cm','axes':'Unreal: X forward, Y right, Z up; left-handed','output_rotation':'pitch,yaw,roll degrees','existing_rotation':'quaternion x,y,z,w'},
        region=region,coverage={'scope':'Currently loaded ordinary StaticMeshComponents, including instances'+(' inside selected region' if region.get('mode')=='selected oriented region' else ''),'streamed_out_objects_included':False,'limitations':'Streamed-out objects are not included; terrain and non-static-mesh actors are not described','objects':len(rows),'catalog_assets':len(supported),'catalog_omitted_for_size':0},
        catalog_columns=['id','path','name','dimensions_cm','spawnable'],catalog_class='/Script/Engine.StaticMesh',catalog=catalog,
        object_columns=['asset','position_cm','quaternion_xyzw','scale'],objects=rows,templates=descriptions,
        remaining_capacity=capacity,instructions=INSTRUCTIONS)


def compile_scene(document,packet,templates,world,capacity):
    fields(document,('format','version','export_id','world','name','objects'),('format','version','export_id','world','name','objects'))
    if document['format']!='e33.ai-scene' or type(document['version']) is not int or document['version']!=1:raise ValueError('Unsupported AI scene format/version')
    if document['export_id']!=packet['export_id']:raise ValueError('Incorrect export ID')
    if world!=packet['world'] or document['world']!=world:raise ValueError('AI scene belongs to another game map')
    if type(document['objects']) is not list or len(document['objects'])>6000:raise ValueError('Expected at most 6000 placement instructions')
    assets={r[0]:r[1] for r in packet['catalog'] if r[4]}
    origin=vector(packet['origin_cm']);out=[];sources=[]
    limit=min(capacity,packet['remaining_capacity'],5984)
    for n,row in enumerate(document['objects']):
        fields(row,('asset','template','position','rotation','scale','repeat'),('position',))
        if ('asset' in row)==('template' in row):raise ValueError(f'Object {n}: choose exactly one asset or template')
        position=vector(row['position']);q=quaternion(row.get('rotation',[0,0,0]));scale=vector(row.get('scale',[1,1,1]),10000,True)
        repeat=row.get('repeat',{'count':1,'step':[0,0,0]});fields(repeat,('count','step'),('count','step'))
        count=repeat['count'];step=vector(repeat['step'])
        if type(count) is not int or not 1<=count<=5984:raise ValueError('Repeat count must be 1–5984')
        if 'asset' in row:
            key=row['asset']
            if type(key) is not str or key not in assets:raise ValueError(f'Object {n}: unknown or unsupported asset ID')
            source=[dict(asset=assets[key],transform=[0,0,0,1,0,0,0,0,1,1,1,0])]
        else:
            key=row['template']
            if type(key) is not str or key not in packet['templates'] or key not in templates:raise ValueError('Unknown template ID')
            if not scale[0]==scale[1]==scale[2]:raise ValueError('Templates require uniform scale')
            source=validate(templates[key])['objects']
            if not source or any(r['kind']!='mesh' or r.get('component_edits') or r['asset'] not in assets.values() for r in source):raise ValueError('Template contains unsupported assets')
        if len(out)+count*len(source)>limit:raise ValueError('Expanded scene exceeds remaining object capacity')
        for repeat_index in range(count):
            base=vector([origin[i]+position[i]+repeat_index*step[i] for i in range(3)])
            for child_index,child in enumerate(source):
                p=pose(child['transform']);local=rotate_point([p[4+i]*scale[i] for i in range(3)],[0,0,0],q)
                final=pose([*multiply(q,p[:4]),*[base[i]+local[i] for i in range(3)],0,*[scale[i]*p[8+i] for i in range(3)],0])
                out.append(dict(id=uuid.uuid4().hex,kind='mesh',asset=child['asset'],transform=final))
                sources.append([n,repeat_index,child_index])
    result=validate(dict(format=FORMAT,version=1,name=document['name'],world=world,objects=out,assets=sorted({r['asset'] for r in out})))
    return result,sources


class AIWorkflow:
    def __init__(self,library):
        from .templates import Templates
        self.library=library;self.mod=library.mod;self.root=library.store.root.parent/'ai'
        self.scanner=Templates(library);self.queue=[];self.report=None;self.picker=None;self.worker=None;self.last_export=None

    def status(self):
        report=None if self.report is None else dict(total=self.report['total'],succeeded=len(self.report['succeeded']),failed=len(self.report['failed']),unattempted=len(self.report['unattempted']),uncertain=self.report['uncertain'],path=str(self.report_path))
        return dict(exporting=bool(self.scanner.job),pending=len(self.queue),last_export=self.last_export,report=report,message=self.library.message)

    def export(self,reveal=False):
        from .bulk import prepare,SCENE_LIMIT,CUBE
        if self.scanner.job or self.queue:raise ValueError('Wait for the current AI operation')
        world=prepare(self.library);self.mod.command(26)
        selection=self.mod.templates
        if selection.world==world and all(p is not None for p in selection.points):
            points=[list(p) for p in selection.points];angles=list(selection.angles);mode='selected oriented region'
        else:
            points=None;angles=[0,0,0];mode='all loaded map objects'
        all_loaded=points is None
        low=[min(a,b) for a,b in zip(*points)] if points else [0.,0.,0.]
        high=[max(a,b) for a,b in zip(*points)] if points else None
        origin=list(self.mod.last['position']) if all_loaded else [(a+b)/2 for a,b in zip(low,high)]
        paths=sorted(set(self.library.registry_paths or [])|{CUBE})
        shipped=read_json(Path(__file__).with_name('ai_asset_catalog.json'))
        names={p:dict(name=name,dimensions_cm=dimensions) for p,name,dimensions in shipped['assets']}
        for p,metadata in self.library.known.items():names.setdefault(p,{}).update(metadata)
        snapshots={};omitted=[]
        for entry in selection.store.list():
            data=selection.store.read(entry['id'])
            if data['objects'] and all(r['kind']=='mesh' and r['asset'] in paths and not r.get('component_edits') for r in data['objects']):snapshots['t'+str(len(snapshots))]=data
            else:omitted.append(entry['name'])
        self.scanner.points=points or [None,None];self.scanner.angles=angles;self.scanner.world=world
        def complete(data):
            if self.library.context()[3]!=world:raise ValueError('World changed during export; export again')
            # Template scanner returns positions relative to its unrotated low corner.
            for row in data['objects']:
                row['transform'][4:7]=[row['transform'][4+i]+low[i] for i in range(3)]
            region=dict(mode=mode,selection_rule='all loaded supported mesh origins') if all_loaded else dict(mode=mode,min_cm=[v-o for v,o in zip(low,origin)],max_cm=[v-o for v,o in zip(high,origin)],rotation_roll_pitch_yaw=angles,selection_rule='mesh origin inside oriented box')
            packet=export_packet(world,origin,region,paths,data['objects'],snapshots,max(0,SCENE_LIMIT-16-len(self.library.owned)),names)
            packet['coverage']['unsupported_templates']=omitted
            packet['coverage'].update(data.get('scan_stats',{}))
            key=packet['export_id'];path=self.root/'exports'/(key+'.json')
            write_json(self.root/'retained'/(key+'.json'),dict(packet=packet,templates=snapshots))
            write_json(path,packet);self.last_export=str(path)
            self.library.message=f"AI export: {len(data['objects'])} objects, {len(paths)} assets, {path.stat().st_size:,} bytes. Streamed-out objects are not included. {path}"
            if reveal:
                import os
                os.startfile(str(path.parent))
        self.scanner.save('AI context',on_complete=complete,max_rows=250000,all_loaded=all_loaded)
        return self.status()

    def import_file(self,path):
        from .bulk import prepare,SCENE_LIMIT
        if self.queue or self.scanner.job:raise ValueError('Wait for the current AI operation')
        data=read_json(path);key=data.get('export_id') if type(data) is dict else None
        if type(key) is not str or len(key)!=32 or any(c not in '0123456789abcdef' for c in key):raise ValueError('Expected an export ID from this installation')
        retained=read_json(self.root/'retained'/(key+'.json'),128*1024*1024)
        world=self.library.context()[3]
        scene,sources=compile_scene(data,retained['packet'],retained['templates'],world,SCENE_LIMIT-16-len(self.library.owned))
        prepare(self.library)
        if any(p not in self.library.bulk_indices and p!='/Engine/BasicShapes/Cube.Cube' for p in scene['assets']):raise ValueError('Export contains assets no longer available in this game build')
        self.queue=list(zip(scene['objects'],sources));self.world=world
        self.report=dict(export_id=key,name=scene['name'],total=len(self.queue),succeeded=[],failed=[],unattempted=[],uncertain=False)
        self.report_path=self.root/'imports'/(uuid.uuid4().hex+'.json')
        self.library.message=f'Importing AI scene: 0/{len(self.queue)}'
        if not self.queue:self.finish()
        return self.status()

    def finish(self):
        try:write_json(self.report_path,self.report)
        except OSError as exc:
            self.library.message='AI import stopped; props remain tracked, but report could not be saved: '+str(exc)
            return
        self.library.message=f"AI import: {len(self.report['succeeded'])} placed, {len(self.report['failed'])} failed, {len(self.report['unattempted'])} unattempted. "+('UNCERTAIN batch; do not retry blindly. ' if self.report['uncertain'] else '')+f'Report: {self.report_path}'

    def poll(self):
        self.scanner.poll()
        if self.picker and self.picker.done():
            future=self.picker;self.picker=None
            try:
                path=future.result()
                if path:self.import_file(path)
            except Exception as exc:self.library.message='AI import rejected: '+str(exc)
        if not self.queue:return
        from .bulk import spawn_batch
        try:
            if self.library.context()[3]!=self.world:raise ValueError('World changed; import stopped')
            batch=self.queue[:64];before=set(self.library.owned)
            try:results=spawn_batch(self.library,[(r['asset'],r['transform']) for r,_ in batch],prepared=True)
            except Exception:
                self.report['uncertain']=True
                self.report['succeeded'].extend(dict(id=key,source=None) for key in set(self.library.owned)-before)
                raise
            if not 1<=len(results)<=len(batch):raise RuntimeError('Invalid spawn progress')
            for result,(_,source) in zip(results,batch):
                if 'error' in result:self.report['failed'].append(dict(source=source,asset=result['asset'],error=result['error']))
                else:self.report['succeeded'].append(dict(id=result['id'],source=source))
            del self.queue[:len(results)]
            self.library.message=f"AI import: {len(self.report['succeeded'])} placed, {len(self.report['failed'])} failed, {len(self.queue)} remaining"
            if not self.queue:self.finish()
        except Exception as exc:
            self.report['error']=str(exc)
            # An unacknowledged batch may have spawned objects: never label it
            # failed or retry it automatically.
            if self.report['uncertain']:
                self.report['uncertain_sources']=[source for _,source in self.queue[:64]]
                self.report['unattempted']=[source for _,source in self.queue[64:]]
            else:self.report['unattempted']=[source for _,source in self.queue]
            self.queue=[];self.finish()

    def choose_import(self):
        if self.picker:raise ValueError('File picker already open')
        from concurrent.futures import ThreadPoolExecutor
        from .ai_picker import choose_json
        if self.worker is None:self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='ai-file-picker')
        self.picker=self.worker.submit(choose_json,str(self.root))
        self.library.message='Choose the generated AI scene JSON file'

    def close(self):
        if self.queue:
            self.report['unattempted']=[source for _,source in self.queue];self.queue=[];self.finish()
        self.scanner.close()
        if self.worker:self.worker.shutdown(wait=False,cancel_futures=True)
