"""Registry-indexed native mesh batches; no per-prop reflection or subprocess."""
import struct,time,uuid
from .scenes import pose,validate,FORMAT

CUBE='/Engine/BasicShapes/Cube.Cube'
SCENE_LIMIT=6000


def prepare(library):
    if not library.mod.active:library.mod.toggle()
    if not library.rows:library.refresh(force=False)
    if not library.registry_names_ready:
        library.mod.command(35,registry_offset=0)
        total=struct.unpack_from('<I',library.mod.last_raw,3560)[0]
        if total!=len(library.registry_paths or []):library.refresh(force=True)
        library.registry_names_ready=True
    library.bulk_indices={path:i for i,path in enumerate(library.registry_paths)}
    _,_,_,world=library.context()
    if library.owned and any(row['world']!=world for row in library.owned.values()):raise ValueError('Clear the previous level scene first')
    return world


def register(library,asset,actor,component,transform=None):
    key=uuid.uuid4().hex
    library.owned[key]=dict(id=key,kind='mesh',asset=asset,actor=actor,component=component,world=library.world)
    library.selected=key
    return dict(id=key,asset=asset,actor_index=actor[0],component_index=component[0],transform=transform)


def spawn_batch(library,requests,*,gallery=False,prepared=False):
    if not prepared:prepare(library)
    if not 1<=len(requests)<=64:raise ValueError('Batch must contain 1–64 meshes')
    if len(library.owned)+len(requests)>SCENE_LIMIT-16:raise ValueError('Scene capacity reached; save or clear objects first')
    rows=[]
    for asset,transform in requests:
        index=0xffffffff if asset==CUBE else library.bulk_indices.get(asset)
        if index is None:raise ValueError('Asset is not in the native static-mesh registry: '+asset)
        rows.append((index,int(gallery),pose(transform)))
    start=time.perf_counter();library.mod.command(50,bulk=rows);library.mark('bulk_dispatch',start)
    raw=library.mod.last_raw;count,successes=struct.unpack_from('<II',raw,3560)
    if not 1<=count<=len(rows) or successes>count:raise RuntimeError('Invalid bulk progress; outcome uncertain')
    results=[]
    for i in range(count):
        at=4096+192*i;error=struct.unpack_from('<I',raw,at)[0];asset=requests[i][0]
        if error:results.append(dict(asset=asset,error=f'Native spawn error {error}'));continue
        actor=struct.unpack_from('<iiQ',raw,at+8);component=struct.unpack_from('<iiQ',raw,at+24)
        if not actor[2] or not component[2]:raise RuntimeError('Missing spawned identity; outcome uncertain')
        result=register(library,asset,actor,component,list(struct.unpack_from('<12d',raw,at+40)))
        result.update(center=list(struct.unpack_from('<3d',raw,at+136)),extent=list(struct.unpack_from('<3d',raw,at+160)))
        results.append(result)
    library.bulk_stats=dict(processed=count,successes=successes,game_ms=struct.unpack_from('<d',raw,3568)[0])
    return results


def delete_many(library,keys):
    pending=[key for key in keys if key in library.owned]
    while pending:
        batch=pending[:128]
        library.mod.command(53,bulk=[library.owned[key]['actor'] for key in batch])
        count=struct.unpack_from('<I',library.mod.last_raw,3560)[0]
        if not 1<=count<=len(batch):raise RuntimeError('Invalid deletion progress')
        for key in batch[:count]:library.owned.pop(key,None)
        del pending[:count]


def floor(library,origin,spacing,tight,columns):
    library.mod.command(52,values=[*origin,spacing,int(tight),columns,0,0])
    raw=library.mod.last_raw
    return register(library,CUBE,struct.unpack_from('<iiQ',raw,3568),struct.unpack_from('<iiQ',raw,3584))


def snapshot(library,name):
    from expedition33.catalog import capture_selected
    from expedition33.values import read_values_with_references
    c,_,_,world=library.context();offset=0;total=None;entries=[]
    while True:
        library.mod.command(51,registry_offset=offset);raw=library.mod.last_raw
        count,current,next_offset=struct.unpack_from('<III',raw,3560)
        if count>128 or current>SCENE_LIMIT or next_offset>current or (total is not None and total!=current):raise RuntimeError('Scene changed during save; try again')
        for i in range(count):
            at=4096+128*i
            entries.append((struct.unpack_from('<iiQ',raw,at),list(struct.unpack_from('<12d',raw,at+16)),struct.unpack_from('<I',raw,at+112)[0]))
        total=current
        if next_offset==total:break
        if next_offset<=offset:raise RuntimeError('Scene export made no progress')
        offset=next_offset
    by_component={tuple(r['component']):r for r in library.owned.values()}
    by_actor={tuple(r['actor']):r for r in library.owned.values()}
    # Owned rows already carry a serial-checked transform from the game thread.
    # Only edits to existing scenery need external property/path introspection.
    external=[identity for identity,_,owned in entries if not owned]
    if external:c=c.with_observations(capture_selected(library.mod.session.pid,external))
    rows=[];saved_owned={};children=[]
    for identity,transform,owned in entries:
        if owned:
            tracked=by_component.get(identity)
            if tracked is None:raise RuntimeError('Native owned asset has no scene record')
            if tracked['id']==library.preview_key or tracked.get('duplication_preview'):continue
            saved={k:tracked[k] for k in ('id','kind','asset')}|dict(transform=transform)
            rows.append(saved);saved_owned[tracked['id']]=saved;continue
        component=c.by_index[identity[0]]
        if (component.serial,component.address)!=identity[1:]:raise RuntimeError('Tracked component changed during save')
        parent=c.by_index[component.outer_index];tracked=by_actor.get((parent.index,parent.serial,parent.address))
        values,c=read_values_with_references(c,component,fields=('StaticMesh',));mesh=next(v for k,v in values.values.items() if k[1]=='StaticMesh')
        if tracked:
            if tracked['id']!=library.preview_key and not tracked.get('duplication_preview'):children.append((tracked['id'],dict(component=c.path_name(component)[len(c.path_name(parent)):],asset=c.path_name(mesh),transform=transform)))
        else:rows.append(dict(id=uuid.uuid5(uuid.NAMESPACE_URL,world+'|'+c.path_name(component)).hex,kind='world_edit',asset=c.path_name(mesh),component=c.path_name(component),transform=transform))
    for key,child in children:saved_owned[key].setdefault('component_edits',[]).append(child)
    assets={r['asset'] for r in rows}|{child['asset'] for _,child in children}
    return validate(dict(format=FORMAT,version=1,name=name,world=world,objects=rows,assets=sorted(assets)))


def place_existing(library,key):
    from types import SimpleNamespace
    actor=SimpleNamespace(**dict(zip(('index','serial','address'),library.owned[key]['actor'])))
    library.mod.command(54,ids=(actor,));raw=library.mod.last_raw;at=4096
    return dict(id=key,transform=list(struct.unpack_from('<12d',raw,at+40)),center=list(struct.unpack_from('<3d',raw,at+136)),extent=list(struct.unpack_from('<3d',raw,at+160)))
