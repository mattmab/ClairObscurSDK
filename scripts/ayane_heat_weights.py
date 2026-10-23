"""Generate body weights on a welded anatomical proxy, then surface-transfer."""
import bpy,bmesh
import numpy as np
from scipy.spatial import cKDTree
from mathutils import Vector

def body_weights(objects,fitted,end,names,parents):
    positions=[];faces=[]
    for obj in objects:
        if not obj.name.startswith('Genesis8Female_') and obj.name!='Genesis8Female_37_0':continue
        start=len(positions)
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co;positions.append((p.x,-p.y+.25,p.z))
        for polygon in obj.data.polygons:faces.append(tuple(start+i for i in polygon.vertices))
    mesh=bpy.data.meshes.new('WeightTransferBody');mesh.from_pydata(positions,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    body=bpy.data.objects.new('WeightTransferBody',mesh);bpy.context.collection.objects.link(body)
    arm=bpy.data.armatures.new('FittedWeightRig');rig=bpy.data.objects.new('FittedWeightRig',arm);bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for i,name in enumerate(names):
        bone=arm.edit_bones.new(name);bone.head=Vector(fitted[i]/100);bone.tail=Vector(end[i]/100)
        if (bone.tail-bone.head).length<.001:bone.tail.z+=.01
        if parents[i]>=0:bone.parent=arm.edit_bones[names[parents[i]]]
        bone.use_deform=i!=0
    bpy.ops.object.mode_set(mode='OBJECT');body.select_set(True)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    values=np.zeros((len(mesh.vertices),len(names)))
    group_names={g.index:g.name for g in body.vertex_groups}
    for v in mesh.vertices:
        for g in v.groups:
            if group_names[g.group] in names:values[v.index,names.index(group_names[g.group])]=g.weight
    sums=values.sum(axis=1)
    valid=sums>1e-6
    points=np.array([v.co[:] for v in mesh.vertices])*100
    detached_head=(~valid)&(points[:,2]>fitted[names.index('neck_01'),2])&(np.linalg.norm(points-fitted[names.index('Head')],axis=1)<25)
    values[detached_head,names.index('Head')]=1
    sums=values.sum(axis=1);valid=sums>1e-6
    if valid.mean()<.98:
        missing=np.array([v.co[:] for v in mesh.vertices])[~valid]
        raise ValueError(f'Automatic body weighting coverage {valid.mean():.1%}; unweighted bounds {missing.min(0).tolist()} .. {missing.max(0).tolist()}')
    values[valid]/=sums[valid,None]
    tree=cKDTree(points[valid]);values=values[valid]
    report={'method':'Blender bone heat on welded body, nearest-surface-vertex weight transfer','body_vertices':len(points),'weighted_vertices':int(valid.sum()),'detached_head_vertices':int(detached_head.sum())}
    bpy.ops.object.select_all(action='DESELECT');body.hide_render=True;body.hide_set(True);rig.hide_render=True;rig.hide_set(True)
    def transfer(p,label):
        dist,indices=tree.query(p,k=4)
        proximity=1/np.maximum(dist,.0001)**2;proximity/=proximity.sum(axis=1)[:,None]
        w=np.einsum('vk,vkb->vb',proximity,values[indices])
        if any(s in label.lower() for s in ('hair','eyebrow','eyelash')):
            w[:]=0;w[:,names.index('Head')]=1
        # These are sheathed hip/thigh accessories in this source, not held
        # weapons. Moving them with the hands stretches them across the body.
        if 'dagger' in label.lower():
            center=p.mean(axis=0);thigh=names.index('thigh_l' if center[0]>0 else 'thigh_r')
            w[:]=0;w[:,thigh]=1
        order=np.argsort(w,axis=1)[:,-4:][:,::-1];weights=np.take_along_axis(w,order,axis=1)
        weights/=weights.sum(axis=1)[:,None]
        return order,weights
    return transfer,report
