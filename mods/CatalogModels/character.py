"""Resolve the controlled exploration pawn's current visual rig by live references."""
from expedition33.catalog import capture_matching
from expedition33.values import read_values_with_references
from expedition33.procedural_mesh import discover,capture_bones,combat_target
from expedition33._reader import ReadBatch,active_reader
from contextlib import nullcontext

def select_visuals(rows):
    faces=[r for r in rows if r['asset'] and (r['object'].name=='Face' or
            (r['animation'] and r['animation'].name.startswith('Face_AnimBP_')) or 'face' in r['asset'].name.lower())]
    hairs=[r for r in rows if r['object'].name=='Haircut_SkeletalMesh']
    bodies=[r for r in rows if r['asset'] and r['animation'] and r not in faces and r not in hairs]
    if len(bodies)!=1:raise ValueError('Current character body is missing or ambiguous')
    body=bodies[0]
    if len(faces)!=1 or len(hairs)!=1:raise ValueError('Current character face/hair is missing or ambiguous')
    return body,faces[0],hairs[0]

def resolve(pid,executable=None):
    with ReadBatch(pid,_executable=executable) if active_reader() is None else nullcontext():
        return _resolve(pid)

def _resolve(pid):
    pawn=discover(pid)[0]
    manager=None
    if pawn.class_name.endswith('_Battle_C'):
        selected,manager=combat_target(pid)
        if (selected.index,selected.serial)!=(pawn.index,pawn.serial):raise ValueError('Combat target changed during discovery')
    catalog=capture_matching(pid,classes=('SkeletalMeshComponent',))
    rows=[]
    for obj in catalog.select('SkeletalMeshComponent'):
        if obj.outer_index!=pawn.index:continue
        values,catalog=read_values_with_references(catalog,obj,fields=('SkinnedAsset','AnimScriptInstance'))
        values={name:value for (_,name),value in values.values.items()}
        rows.append(dict(object=obj,asset=values.get('SkinnedAsset'),animation=values.get('AnimScriptInstance')))
    selected=select_visuals(rows)
    token=tuple((o.index,o.serial,o.address) for o in
                (pawn,*(r['object'] for r in selected),selected[0]['asset']))
    return dict(combat_manager=manager,token=token,driver=selected[0]['object'].index,
                visuals=[r['object'].index for r in selected],character=selected[0]['asset'].name)

def collect(scope,driver):
    with ReadBatch(scope.pid,_executable=scope._session._transport._executable) if active_reader() is None else nullcontext():
        return _collect(scope,driver)

def _collect(scope,driver):
    required={'root','pelvis','spine_01','spine_03','spine_05','neck_01','head'}
    required.update(name+'_'+side for name in ('clavicle','upperarm','lowerarm','hand','thigh','calf','foot','ball') for side in ('l','r'))
    bones=[]
    for page in range(41):
        result=capture_bones(scope,driver,page);bones+=result['bones']
        if required <= {b['name'].lower() for b in bones}:return bones
        if len(bones)>=result['total']:break
    raise ValueError('Selected character lacks the required body joints')
