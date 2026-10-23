"""Draw orthographic point projections of the supplied GLB for rig fitting."""
import json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

source=Path('C:/Users/Matt/Downloads/ayane__ninja_gaiden.glb')
raw=source.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
d=json.loads(raw[20:20+length]);binary=raw[28+length:]
def accessor(i):
    a=d['accessors'][i];v=d['bufferViews'][a['bufferView']]
    dtype={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]
    width={'VEC3':3,'VEC2':2,'VEC4':4,'SCALAR':1}[a['type']]
    return np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dtype).itemsize*width),np.dtype(dtype).itemsize)).copy()
parts=[]
def visit(i,parent):
    node=d['nodes'][i]
    if any(k in node for k in ('translation','rotation','scale')):raise ValueError('TRS requires explicit handling')
    m=parent@np.array(node.get('matrix',np.eye(4).T.flatten())).reshape(4,4).T
    if 'mesh'in node:
        for primitive in d['meshes'][node['mesh']]['primitives']:
            p=accessor(primitive['attributes']['POSITION']);p=np.c_[p,np.ones(len(p))]@m.T
            parts.append((node['name'],p[:,:3]))
    for c in node.get('children',[]):visit(c,m)
for i in d['scenes'][d.get('scene',0)]['nodes']:visit(i,np.eye(4))
out=Path(__file__).resolve().parents[1]/'dist'/'ayane';out.mkdir(parents=True,exist_ok=True)
p=np.concatenate([p for _,p in parts]);print('bounds',p.min(0),p.max(0))
for name,axes in [('xy',(0,1)),('xz',(0,2)),('zy',(2,1))]:
    q=p[:,axes];lo=q.min(0);size=np.ptp(q,axis=0);scale=850/max(size)
    im=Image.new('RGB',(1000,1000),(32,32,32));draw=ImageDraw.Draw(im)
    for j,(label,points) in enumerate(parts):
        q=(points[:,axes]-lo)*scale+60
        color=((j*73)%160+90,(j*43)%160+90,(j*97)%160+90)
        for x,y in q:draw.point((int(x),1000-int(y)),fill=color)
    im.save(out/f'projection-{name}.png')
np.savez_compressed(out/'source-points.npz',points=p)
