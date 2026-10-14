"""Bind an offline prepared, weighted model through the existing native skin ABI."""
import hashlib,json,math,struct
from pathlib import Path
from .skin import reference_world

from .library import package as model_package
DEFAULT_PACKAGE=model_package('ayane')

def checked_package(package):
    package=Path(package).resolve()
    data=json.loads((package/'manifest.json').read_text())
    if data['schema']!='e33-weighted-model/1':raise ValueError('Weighted model schema')
    def checked(name):
        path=(package/name).resolve()
        if not path.is_relative_to(package):raise ValueError('Model path escapes package')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=data['hashes'][name]:raise ValueError('Model file hash')
        return path,raw
    return data,checked

def prepare_custom_skin(output,rows,package=DEFAULT_PACKAGE):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    data,checked=checked_package(package)
    bones=data['bones'];sections=data['sections']
    if not 0<len(bones)<=32 or not 0<len(sections)<=64:raise ValueError('Model rig budget')
    target=reference_world(rows);names={r['name'].lower():r for r in rows}
    raw=bytearray(struct.pack('<8sII',b'E33SKIN2',len(bones),len(sections)))
    for i,b in enumerate(bones):
        row=names[b['name'].lower()];name=row['name'];q,p=target[name]
        if not -1<=b['parent']<i or len(b['point'])!=3 or any(not math.isfinite(x) or abs(x)>500 for x in b['point']):raise ValueError('Model joint')
        raw.extend(struct.pack('<I64si3f7d',row['index'],name.encode('ascii'),b['parent'],*b['point'],*q,*p))
    total=0;result=[]
    for i,s in enumerate(sections):
        mesh,content=checked(s['mesh']);magic,count,indices=struct.unpack_from('<8sII',content)
        total+=count
        if magic!=b'E33MESH1' or count<3 or total>100000 or len(content)!=16+64*count+4*indices:raise ValueError('Model geometry budget')
        _,weights=checked(s['weights'])
        if len(weights)!=count*128:raise ValueError('Model weight count')
        for at in range(0,len(weights),128):
            influences=list(struct.iter_unpack('<If6f',weights[at:at+128]))
            if any(b>=len(bones) or not 0<=w<=1 or not all(math.isfinite(x) for x in values) for b,w,*values in influences):raise ValueError('Invalid skin influence')
            if abs(sum(r[1] for r in influences)-1)>0.0001:raise ValueError('Non-normalized weights')
        raw.extend(struct.pack('<II',i,count));raw.extend(weights)
        texture,_=checked(s['texture'])
        result.append(dict(mesh=str(mesh),texture=str(texture),vertices=count))
    path=output/'ayane.e33skin';path.write_bytes(raw)
    return dict(id=data.get('model','custom-model'),skin=str(path.resolve()),vertices=total,sections=result,
                mode='Authored FBX weights; fingers and cloth follow parent bones')
