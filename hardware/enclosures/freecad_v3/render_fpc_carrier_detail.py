import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent; M=ROOT/'models'; P=ROOT/'previews'; P.mkdir(exist_ok=True)
def mat(name,color,rough=.35):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=rough; return m
CARRIER=mat('Carrier',(0.13,0.15,0.17),.34); ORANGE=mat('Antenna',(0.95,0.33,0.04),.28); FLOOR=mat('Floor',(0.18,0.19,0.20),.5); RED=mat('Prototype',(0.75,0.03,0.03),.3); WHITE=mat('Text',(0.9,0.92,0.94),.3)
def reset(): bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def look(o,t): o.rotation_euler=(t-o.location).to_track_quat('-Z','Y').to_euler()
def text(body,loc,size,matl):
 bpy.ops.object.text_add(location=loc,rotation=(0,0,0)); o=bpy.context.object; o.data.body=body; o.data.align_x='CENTER'; o.data.size=size; o.data.extrude=.08; o.data.bevel_depth=.015; o.data.materials.append(matl); return o
def render(kind):
 reset()
 bpy.ops.wm.stl_import(filepath=str(M/f'GrowCentral_XIAO_{kind}_FPC_AntennaCarrier_PRINT_V3.stl')); c=bpy.context.selected_objects[0]; c.data.materials.append(CARRIER); c.rotation_euler.x=math.pi; c.location.z=6.7
 bev=c.modifiers.new('soft','BEVEL'); bev.width=.15; bev.segments=2
 bpy.ops.mesh.primitive_cube_add(location=(22,12,6.875),scale=(20,10,.175)); a=bpy.context.object; a.data.materials.append(ORANGE)
 bev=a.modifiers.new('soft','BEVEL'); bev.width=.20; bev.segments=3
 bpy.ops.mesh.primitive_cube_add(location=(22,12,-1.5),scale=(40,32,1.5)); bpy.context.object.data.materials.append(FLOOR)
 target=Vector((22,12,4.0)); sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1400; sc.render.resolution_y=1050; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.world.use_nodes=True
 bg=sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(.07,.075,.08,1); bg.inputs['Strength'].default_value=.9; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=2.0
 bpy.ops.object.camera_add(location=(78,-68,72)); cam=bpy.context.object; cam.data.type='ORTHO'; cam.data.ortho_scale=76; look(cam,target); sc.camera=cam
 for loc,en,size in [((-20,-30,90),3500,80),((85,25,70),2400,70),((20,80,45),1600,60)]:
  bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.data.energy=en; l.data.size=size; look(l,target)
 # 3D labels on floor behind carrier
 text('PROTOTYP',(22,38,0.2),7.5,RED)
 text('40 x 20 mm ORIGINAL KLEBEANTENNE',(22,31,0.2),2.8,WHITE)
 text('2 mm SCHUTZRAND RUNDUM',(22,-12,0.2),2.5,WHITE)
 out=P/f'GrowCentral_{kind}_FPC_V3_PROTOTYP_Antennenhalter_Detail.png'; sc.render.filepath=str(out); bpy.ops.render.render(write_still=True); print('RENDERED',out)
for k in ('Node','Hub'): render(k)
