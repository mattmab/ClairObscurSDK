"""Reproduce the native skin calculation offline from recorded SDK bone data."""
import json,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from mods.CatalogModels.skin import reference_world
p=ROOT/'dist/ayane';m=json.loads((p/'runtime/manifest.json').read_text());rows=json.loads((p/'live-bones.json').read_text())
refs=reference_world(rows);lookup={r['name'].lower():r for r in rows};qs=[];positions=[];root=None
for i,b in enumerate(m['bones']):
    row=lookup[b['name'].lower()];refq,refp=refs[row['name']];world=np.array(row['world']);q=Rotation.from_quat(world[:4])*Rotation.from_quat(refq).inv();qs.append(q)
    parent=b['parent'];position=world[4:7].copy()
    if parent>=0:
        offset=(np.array(b['point'])-np.array(m['bones'][parent]['point']))*world[8:11]
        offset=qs[parent].apply(offset);bob=np.zeros(3)
        if parent==0:
            parentrow=lookup[m['bones'][parent]['name'].lower()];pref=refs[parentrow['name']][1]
            bob=world[4:7]-positions[parent]-qs[parent].apply((np.array(refp)-pref)*world[8:11])
        position=positions[parent]+offset+bob
    positions.append(position)
bpy.ops.wm.read_factory_settings(use_empty=True)
for i,s in enumerate(m['sections']):
    b=(p/'runtime'/s['mesh']).read_bytes();_,n,k=struct.unpack_from('<8sII',b);v=np.frombuffer(b,dtype='<f8',count=n*8,offset=16).reshape(n,8);indices=np.frombuffer(b,dtype='<i4',count=k,offset=16+n*64).reshape(-1,3)
    raw=(p/'runtime'/s['weights']).read_bytes();weights=np.frombuffer(raw,dtype=np.dtype([('bone','<u4'),('w','<f4'),('pos','<f4',(3,)),('normal','<f4',(3,))])).reshape(n,4)
    out=np.zeros((n,3))
    for slot in range(4):
        for bi in np.unique(weights[:,slot]['bone']):
            mask=weights[:,slot]['bone']==bi
            out[mask]+=(qs[bi].apply(weights[mask,slot]['pos'])+positions[bi])*weights[mask,slot]['w'][:,None]
    out=qs[0].inv().apply(out-positions[0])/100
    mesh=bpy.data.meshes.new(s['source']);mesh.from_pydata(out.tolist(),[],indices[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(s['source'],mesh);bpy.context.collection.objects.link(obj)
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='SINGLE';s.display.shading.single_color=(.6,.6,.6);s.display.shading.show_cavity=True
cam=bpy.data.cameras.new('Inspect');obj=bpy.data.objects.new('Inspect',cam);s.collection.objects.link(obj);s.camera=obj;cam.type='ORTHO';cam.ortho_scale=2.35
s.render.resolution_x=800;s.render.resolution_y=1000;s.render.resolution_percentage=100
for name,loc in [('front',(0,5,1)),('side',(5,0,1))]:
    obj.location=loc;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(p/f'pose-{name}.png');bpy.ops.render.render(write_still=True)
