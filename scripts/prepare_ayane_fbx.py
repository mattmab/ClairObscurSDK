"""Convert the user supplied authored FBX rig to the bounded SDK skin format."""
from pathlib import Path
import json,struct,hashlib
import bpy
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/ayane-fbx/runtime'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'dist/ayane-fbx/imported.blend'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    pairs=[('SklRootNode','Root'),('SK_Hips','Pelvis'),('SK_Spine01','spine_03'),('SK_Spine02','spine_05'),('SK_Neck','neck_01'),('SK_Head','Head')]
    for side in ('L','R'):
        pairs += [(f'SK_{side}_{a}',b) for a,b in zip(['Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot','Toes'],[f'clavicle_{side.lower()}',f'upperarm_{side.lower()}',f'lowerarm_{side.lower()}',f'Hand_{side}',f'thigh_{side.lower()}',f'calf_{side.lower()}',f'foot_{side.lower()}',f'ball_{side.lower()}'])]
    slots={s:i for i,(s,t) in enumerate(pairs)}
    def mapped(name):
        b=rig.data.bones.get(name)
        while b and b.name not in slots:b=b.parent
        if b is None:raise ValueError('Unmapped weighted bone '+name)
        return slots[b.name]
    def engine(v):return np.array([v.x,-v.y,v.z])*100
    points=np.array([engine(rig.matrix_world@rig.data.bones[s].head_local) for s,t in pairs])
    # SklRootNode is colocated with the hips in this FBX. The runtime Root
    # follows the game's ground-level root; keep the authored pelvis height.
    points[0]=0
    bones=[dict(name=t,parent=mapped(rig.data.bones[s].parent.name) if i else -1,point=points[i].tolist()) for i,(s,t) in enumerate(pairs)]
    source=next(p for p in (ROOT/'dist/ayane-fbx/source').rglob('*.fbx') if '2 Outfit' in str(p))
    folder=source.parent.parent
    sections=[];hashes={};total=0
    for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        bpy.context.view_layer.objects.active=obj
        # Keep original authored vertex groups; Blender interpolates these
        # during bounded geometry reduction instead of generating new weights.
        for mod in list(obj.modifiers):obj.modifiers.remove(mod)
        if len(obj.data.vertices)>70000:
            mod=obj.modifiers.new('SDK vertex budget','DECIMATE');mod.ratio=.35
            bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh=obj.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
        if uv is None:raise ValueError('Missing UV')
        groupmap={g.index:mapped(g.name) for g in obj.vertex_groups}
        weights=[]
        for v in mesh.vertices:
            combined={}
            for g in v.groups:combined[groupmap[g.group]]=combined.get(groupmap[g.group],0)+g.weight
            top=sorted(combined.items(),key=lambda x:-x[1])[:4];s=sum(w for b,w in top)
            if s<1e-6:raise ValueError('Unweighted vertex')
            weights.append([(b,w/s) for b,w in top]+[(0,0)]*(4-len(top)))
        groups={}
        for tri in mesh.loop_triangles:groups.setdefault(tri.material_index,[]).append(tri)
        for mi,triangles in groups.items():
            material=obj.material_slots[mi].material.name.split('.')[0]
            # Transparent eye shells require a different blend mode; leaving
            # them out preserves the actual eyeballs with our opaque shader.
            if any(x in material for x in ('Occlusion','meniscus')) or material.startswith('SIM') or material in ('MI_AYA_eb','MI_AYA_el'):continue
            metadata=folder/'Materials'/f'{material}.json'
            materialdata=json.loads(metadata.read_text());tex=materialdata['Textures']
            name=(tex.get('Albedo') or tex.get('PM_Diffuse') or next((v for k,v in tex.items() if k.endswith('_alb')),None))
            if name:image=Image.open(folder/'Textures'/(name.split('.')[-1]+'.png')).convert('RGBA')
            else:
                colors=materialdata['Parameters']['Colors'];color=colors.get('MidColor')
                if not color:raise ValueError('Missing diffuse '+material)
                image=Image.new('RGBA',(4,4),tuple(bytes.fromhex(color['Hex']))+(255,))
            image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
            verts=[];indices=[];lookup={};raw=bytearray()
            normalmatrix=obj.matrix_world.to_3x3().inverted().transposed()
            for tri in triangles:
                for vi,li in zip(tri.vertices,tri.loops):
                    u,v=uv.data[li].uv;key=(vi,float(u),float(v))
                    if key not in lookup:
                        lookup[key]=len(verts);p=engine(obj.matrix_world@mesh.vertices[vi].co)
                        n=engine(normalmatrix@mesh.vertices[vi].normal);n/=max(np.linalg.norm(n),1e-12)
                        if np.linalg.norm(n)<.9:raise ValueError('Invalid normal')
                        verts.append((*p,*n,u,1-v))
                        for b,w in weights[vi]:raw.extend(struct.pack('<If6f',b,w,*(p-points[b]),*n))
                    indices.append(lookup[key])
            i=len(sections);total+=len(verts)
            row=dict(mesh=f'{i:02}.e33mesh',weights=f'{i:02}.weights',texture=f'{i:02}.png',source=material)
            (OUT/row['mesh']).write_bytes(struct.pack('<8sII',b'E33MESH1',len(verts),len(indices))+b''.join(struct.pack('<8d',*v) for v in verts)+struct.pack(f'<{len(indices)}i',*indices))
            (OUT/row['weights']).write_bytes(raw);image.save(OUT/row['texture'])
            for key in ('mesh','weights','texture'):hashes[row[key]]=hashlib.sha256((OUT/row[key]).read_bytes()).hexdigest()
            sections.append(row)
    if total>100000 or len(sections)>64:raise ValueError((total,len(sections)))
    manifest=dict(schema='e33-weighted-model/1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),vertices=total,bones=bones,sections=sections,hashes=hashes,attribution='User supplied Ninja Gaiden 2 Black Ayane FBX archive; redistribution permission unverified. Authored weights retained and reduced to body bones.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(dict(vertices=total,sections=len(sections),bones=len(bones))))

if __name__=='__main__':main()
