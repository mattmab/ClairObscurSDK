"""Ten bounded material comparison cubes; no change to catalog defaults."""
from pathlib import Path
import json
import struct
from .catalog import prepare

def prepare_samples(root, output):
    output=Path(output)
    original=prepare(root,'2b',output/'source')
    texture=next(row['texture'] for row in original['sections'] if row['texture'])
    # Non-overlapping faces, outward normals, identical UVs on every candidate.
    faces=(
        ((1,0,0),((1,0,0),(1,1,0),(1,1,1),(1,0,1))),
        ((-1,0,0),((0,1,0),(0,0,0),(0,0,1),(0,1,1))),
        ((0,1,0),((1,1,0),(0,1,0),(0,1,1),(1,1,1))),
        ((0,-1,0),((0,0,0),(1,0,0),(1,0,1),(0,0,1))),
        ((0,0,1),((0,0,1),(1,0,1),(1,1,1),(0,1,1))),
        ((0,0,-1),((0,1,0),(1,1,0),(1,0,0),(0,0,0))))
    rows=[]
    profiles=(2,)*10
    gains=(1,2,4,8,12,16,24,32,48,64)
    for ordinal,profile in enumerate(profiles):
        vertices=[];indices=[]
        x=(ordinal%5-2)*130;y=(ordinal//5)*160
        for normal,corners in faces:
            base=len(vertices)
            for point,uv in zip(corners,((0,1),(1,1),(1,0),(0,0))):
                vertices.append((x+point[0]*80,y+point[1]*80,180+point[2]*80,*normal,*uv))
            indices.extend(base+i for i in (0,2,1,0,3,2))
        raw=struct.pack('<8sII',b'E33MESH1',len(vertices),len(indices))
        raw+=b''.join(struct.pack('<8d',*v) for v in vertices)
        raw+=struct.pack('<36i',*indices)
        mesh=output/f'sample-{ordinal+1:02}.e33mesh';mesh.write_bytes(raw)
        rows.append(dict(mesh=str(mesh.resolve()),texture=texture,profile=profile,sample=ordinal+1,tint_gain=gains[ordinal]))
    result=dict(id='shader-comparison',sections=rows,vertices=240,material_profiles=[],mapping=[dict(sample=i+1,profile=p,gain=gains[i],row=i//5+1,column=i%5+1) for i,p in enumerate(profiles)])
    (output/'comparison.json').write_text(json.dumps(result,indent=2))
    return result
