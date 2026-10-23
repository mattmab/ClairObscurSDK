"""Offline geometry inspection; does not connect to or alter the running game."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]/'dist'/'ayane'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='C:/Users/Matt/Downloads/ayane__ninja_gaiden.glb')
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=Vector([min(p[k] for p in points) for k in range(3)])
hi=Vector([max(p[k] for p in points) for k in range(3)])
center=(lo+hi)/2
report={'bounds':[list(lo),list(hi)],'objects':[{'name':o.name,'vertices':len(o.data.vertices),'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box]} for o in objects]}
(OUT/'geometry.json').write_text(json.dumps(report,indent=2))
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
camera=bpy.data.cameras.new('InspectionCamera');obj=bpy.data.objects.new('InspectionCamera',camera);scene.collection.objects.link(obj);scene.camera=obj
camera.type='ORTHO';camera.ortho_scale=max(hi-lo)*1.15
for name,direction in [('front',Vector((0,-1,0))),('side',Vector((1,0,0)))]:
    obj.location=center+direction*max(hi-lo)*3
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ayane-source.blend'))
print(json.dumps({'bounds':report['bounds'],'objects':len(objects)}))
