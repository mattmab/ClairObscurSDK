"""Fit a bounded body rig to Ayane; export existing E33MESH1/skin influences.

Artist landmarks are in the supplied GLB's world coordinates (metres). This is
an approximate body rig, not recovered author skinning. Run offline with bpy.
"""
from pathlib import Path
import hashlib,json,struct,io
import bpy
import numpy as np
from PIL import Image
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/ayane/runtime'
SOURCE=Path('C:/Users/Matt/Downloads/ayane__ninja_gaiden.glb')
RIG=Path('C:/Program Files (x86)/Steam/steamapps/common/Borderlands 4/sdk_mods/NormalizedLibrary/assets/BLEND_2B_ANIMATION_INSPECTOR-v1/manifest.json')

def rotation(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);c=np.dot(a,b)
    if c<-.999:raise ValueError('Opposite joint direction')
    k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+k+k@k/(1+c)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    bpy.ops.object.select_all(action='DESELECT')
    glb=SOURCE.read_bytes();json_size=struct.unpack_from('<I',glb,12)[0]
    gltf=json.loads(glb[20:20+json_size]);binary=glb[28+json_size:]
    materials={m['name']:m for m in gltf['materials']}
    # The working 2B bind skeleton supplies direction conventions only.
    skeleton=json.loads(RIG.read_text())['asset']['skeleton']
    names=['Root','Pelvis','spine_01','spine_03','spine_05','neck_01','Head','clavicle_l','upperarm_l','lowerarm_l','Hand_L','clavicle_r','upperarm_r','lowerarm_r','Hand_R','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','Foot_R','ball_r']
    parents=[-1,0,1,2,3,4,5,4,7,8,9,4,11,12,13,1,15,16,17,1,19,20,21];nb=len(names)
    template=[]
    for index in [1,2,3,4,5,6,7,34,35,36,37,61,62,63,64,90,91,92,93,94,95,96,97]:
        matrix=np.array(skeleton[index]['inverse_bind']).reshape(4,4)
        p=-matrix[:3,:3].T@matrix[:3,3];template.append((-p[0]*100,-p[2]*100,p[1]*100))
    template=np.array(template)
    # Fitted positions, explicit rather than guessed from numeric bone names.
    landmarks=[(0,0,-.25),(0,1.03,-.25),(0,1.08,-.25),(0,1.22,-.26),(0,1.42,-.28),(0,1.56,-.28),(0,1.64,-.27),
        (.05,1.47,-.28),(.18,1.45,-.28),(.32,1.24,-.29),(.28,.98,-.34),
        (-.05,1.47,-.28),(-.17,1.45,-.28),(-.235,1.22,-.30),(-.27,.94,-.34),
        (.115,1.0,-.25),(.235,.57,-.26),(.34,.13,-.26),(.37,.055,-.14),
        (-.115,1.0,-.25),(-.235,.57,-.26),(-.34,.13,-.26),(-.37,.055,-.14)]
    if len(names)!=len(landmarks):raise ValueError('Unexpected reference rig')
    fitted=np.array([(x*100,(z+.25)*100,y*100) for x,y,z in landmarks])
    neutral=fitted.copy();neutral[0]=0
    for i in range(1,nb):
        parent=parents[i];direction=template[i]-template[parent]
        if np.linalg.norm(direction)<.001:direction=fitted[i]-fitted[parent]
        neutral[i]=neutral[parent]+direction/np.linalg.norm(direction)*np.linalg.norm(fitted[i]-fitted[parent])
    tails={i:next((j for j,p in enumerate(parents) if p==i),None) for i in range(nb)}
    # Spine continues upwards rather than into a limb branch.
    tails.update({1:2,4:5,6:None,10:None,14:None,18:None,22:None})
    end=[];rot=[]
    for i in range(nb):
        child=tails[i]
        a=fitted[child]-fitted[i] if child is not None else fitted[i]-fitted[parents[i]]
        b=neutral[child]-neutral[i] if child is not None else neutral[i]-neutral[parents[i]]
        if i==0:a=b=np.array([0.,0.,1.])
        end.append(fitted[i]+a if child is not None else fitted[i]+a/np.linalg.norm(a)*8)
        rot.append(rotation(a,b))
    end=np.array(end);rot=np.array(rot)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];sections=[];hashes={};total=0
    from ayane_heat_weights import body_weights
    weights,weight_report=body_weights(objects,fitted,end,names,parents)
    # Keep an editable armature and weighted Blender file as a review artifact.
    arm=bpy.data.armatures.new('AyaneBodyRig');rig=bpy.data.objects.new('AyaneBodyRig',arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for i,name in enumerate(names):
        bone=arm.edit_bones.new(name);bone.head=Vector(neutral[i]/100);child=tails[i]
        tail=neutral[child] if child is not None else neutral[i]+rot[i]@(end[i]-fitted[i])
        bone.tail=Vector(tail/100)
        if (bone.tail-bone.head).length<.001:bone.tail.z+=.01
        if parents[i]>=0:bone.parent=arm.edit_bones[names[parents[i]]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for obj in objects:
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        # Apply the full imported node hierarchy before reduction and rigging.
        matrix=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=matrix
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        if len(obj.data.vertices)>300 and 'eyebrow' in obj.name.lower():
            mod=obj.modifiers.new('Bounded prototype reduction','DECIMATE')
            mod.ratio=.04
            bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh=obj.data;mesh.calc_loop_triangles()
        p=np.array([(v.co.x*100,(-v.co.y+.25)*100,v.co.z*100) for v in mesh.vertices])
        ids,w=weights(p,obj.name)
        baked=np.zeros_like(p)
        for k in range(4):baked+=(np.einsum('vij,vj->vi',rot[ids[:,k]],p-fitted[ids[:,k]])+neutral[ids[:,k]])*w[:,k,None]
        # Mesh normals follow the same fitted-to-neutral conversion.
        normals=np.array([(v.normal.x,-v.normal.y,v.normal.z) for v in mesh.vertices]);newn=np.zeros_like(normals)
        for k in range(4):newn+=np.einsum('vij,vj->vi',rot[ids[:,k]],normals)*w[:,k,None]
        newn/=np.maximum(np.linalg.norm(newn,axis=1)[:,None],1e-12)
        for triangle in mesh.loop_triangles:
            a,b,c=triangle.vertices;face=np.cross(baked[c]-baked[a],baked[b]-baked[a]);length=np.linalg.norm(face)
            if length>1e-10:
                for vi in (a,b,c):
                    if np.linalg.norm(newn[vi])<.5:newn[vi]=face/length
        uv=mesh.uv_layers.active
        if uv is None:raise ValueError('Missing UVs')
        groups={}
        for triangle in mesh.loop_triangles:
            if all(np.linalg.norm(newn[vi])>.5 for vi in triangle.vertices):groups.setdefault(triangle.material_index,[]).append(triangle)
        for material_index,triangles in groups.items():
            lookup={};vertices=[];indices=[];weights_raw=bytearray()
            for triangle in triangles:
                face=[]
                for vi,li in zip(triangle.vertices,triangle.loops):
                    tex=tuple(uv.data[li].uv);key=(vi,*tex)
                    if key not in lookup:
                        lookup[key]=len(vertices);vertices.append((*baked[vi],*newn[vi],tex[0],1-tex[1]))
                        for bi,weight in zip(ids[vi],w[vi]):weights_raw.extend(struct.pack('<If6f',int(bi),float(weight),*(baked[vi]-neutral[bi]),*newn[vi]))
                    face.append(lookup[key])
                # Coordinate reflection already changes Blender CCW to the
                # clockwise front faces expected by our Unreal PMC path.
                indices.extend(face)
            index=len(sections);total+=len(vertices)
            material=obj.material_slots[material_index].material
            source_material=materials[material.name];pbr=source_material.get('pbrMetallicRoughness',{})
            factor=np.array(pbr.get('baseColorFactor',[1,1,1,1]))
            if 'baseColorTexture' in pbr:
                texture=gltf['textures'][pbr['baseColorTexture']['index']]
                view=gltf['bufferViews'][gltf['images'][texture['source']]['bufferView']]
                start=view.get('byteOffset',0)
                image=Image.open(io.BytesIO(binary[start:start+view['byteLength']])).convert('RGBA')
            else:image=Image.new('RGBA',(4,4),(255,255,255,255))
            if not np.all(factor==1):
                pixels=np.array(image,dtype=np.float32)/255
                rgb=pixels[:,:,:3];linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)*factor[:3]
                pixels[:,:,:3]=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
                pixels[:,:,3]*=factor[3]
                image=Image.fromarray(np.clip(np.rint(pixels*255),0,255).astype('uint8'))
            # Native owner budgets pixels across sections, including repeated
            # images. 52 sections at <=1K stay below the existing64M-pixel cap.
            image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
            image.save(OUT/f'{index:02}.png')
            body=struct.pack('<8sII',b'E33MESH1',len(vertices),len(indices))+b''.join(struct.pack('<8d',*v) for v in vertices)+struct.pack('<'+str(len(indices))+'i',*indices)
            (OUT/f'{index:02}.e33mesh').write_bytes(body);(OUT/f'{index:02}.weights').write_bytes(weights_raw)
            row=dict(mesh=f'{index:02}.e33mesh',weights=f'{index:02}.weights',texture=f'{index:02}.png',source=obj.name)
            for filename in (row['mesh'],row['weights'],row['texture']):hashes[filename]=hashlib.sha256((OUT/filename).read_bytes()).hexdigest()
            sections.append(row)
        for v,co in zip(mesh.vertices,baked):v.co=Vector(co/100)
        vertex_groups=[obj.vertex_groups.new(name=n) for n in names]
        for vi in range(len(p)):
            for bi,weight in zip(ids[vi],w[vi]):vertex_groups[int(bi)].add([vi],float(weight),'REPLACE')
        modifier=obj.modifiers.new('AyaneBodyRig','ARMATURE');modifier.object=rig;obj.select_set(False)
    if total>100000 or len(sections)>64:raise ValueError(f'Native budget exceeded: {total} vertices, {len(sections)} sections')
    texture_pixels=sum(Image.open(OUT/s['texture']).width*Image.open(OUT/s['texture']).height for s in sections)
    if texture_pixels>67108864:raise ValueError('Native texture pixel budget exceeded')
    manifest=dict(schema='e33-weighted-model/1',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        attribution='Ayane | Ninja Gaiden by Casttelan2. CC-BY-4.0. Modified: reduced geometry, fitted body rig, generated weights and neutral pose.',
        source_url='https://sketchfab.com/3d-models/ayane-ninja-gaiden-12bfd990644e467cadae75b798f253ee',
        license_url='https://creativecommons.org/licenses/by/4.0/',vertices=total,weight_report=weight_report,
        bones=[dict(name=n,parent=parents[i],point=neutral[i].tolist()) for i,n in enumerate(names)],sections=sections,hashes=hashes)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT.parent/'ayane-rigged.blend'))
    print(json.dumps({'vertices':total,'sections':len(sections),'output':str(OUT)}))

if __name__=='__main__':main()
