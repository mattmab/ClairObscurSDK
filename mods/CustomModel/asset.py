"""Bounded static OBJ reader. No source execution or material-file traversal."""
from pathlib import Path
import math

def load_obj(path):
    path=Path(path)
    if path.stat().st_size>256000:raise ValueError('OBJ size limit')
    positions=[];uv=[];normals=[];vertices=[];indices=[];seen={}
    for line in path.read_text(encoding='utf8').splitlines():
        words=line.split('#',1)[0].split()
        if not words:continue
        kind,*args=words
        if kind in ('v','vt','vn'):
            width=2 if kind=='vt' else 3
            values=tuple(map(float,args))
            if len(values)!=width or any(not math.isfinite(v) for v in values):raise ValueError('OBJ attribute')
            table={'v':positions,'vt':uv,'vn':normals}[kind];table.append(values)
            if len(table)>256:raise ValueError('OBJ attribute limit')
        elif kind=='f':
            if len(args) not in (3,4):raise ValueError('Only triangles/quads supported')
            face=[]
            for item in args:
                key=tuple(map(int,item.split('/')))
                if len(key)!=3 or any(i<=0 for i in key):raise ValueError('OBJ requires positive position/UV/normal indices')
                if key not in seen:
                    try:p,t,n=positions[key[0]-1],uv[key[1]-1],normals[key[2]-1]
                    except IndexError:raise ValueError('OBJ index outside attributes') from None
                    length=math.sqrt(sum(v*v for v in n))
                    if length<1e-8:raise ValueError('Zero normal')
                    seen[key]=len(vertices);vertices.append((*p,*(v/length for v in n),t[0],1-t[1]))
                face.append(seen[key])
            # OBJ outward faces are counterclockwise; this target PMC uses
            # clockwise front faces. Preserve the outward normals and UVs.
            indices.extend((face[0],face[2],face[1]))
            if len(face)==4:indices.extend((face[0],face[3],face[2]))
            if len(vertices)>256 or len(indices)>768:raise ValueError('Mesh limit')
        elif kind not in ('o','g','s','usemtl','mtllib'):
            raise ValueError('Unsupported OBJ record: '+kind)
    if len(vertices)<3 or not indices:raise ValueError('Empty model')
    return vertices,indices
