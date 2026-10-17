import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent; M=ROOT/'models'; P=ROOT/'previews'; P.mkdir(exist_ok=True)
CASES={
 'Node_FPC':dict(W=48,D=34,H=25,kind='Node',mode='FPC'),
 'Node_EXT':dict(W=43,D=34,H=25,kind='Node',mode='EXT'),
 'Hub_FPC':dict(W=66,D=48,H=28,kind='Hub',mode='FPC'),
 'Hub_EXT':dict(W=66,D=48,H=28,kind='Hub',mode='EXT'),
}
def mat(name,c,rough=.36,metal=.0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1); bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal; return m
BLACK=mat('Body',(.12,.14,.16)); GREEN=mat('Brand',(.03,.85,.24)); BLUE=mat('Liegend',(.02,.32,1.0),.25); CYAN=mat('Stehend',(0,.95,1.0),.25); ORANGE=mat('FPC',(1.0,.36,.015),.28); GOLD=mat('SMA',(.95,.62,.08),.22,.5); GREY=mat('Carrier',(.24,.27,.30)); GROUND=mat('Ground',(.13,.14,.15),.6)
def reset(): bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def imp(path,name,ma,shift=(0,0,0)):
 bpy.ops.wm.stl_import(filepath=str(path)); o=bpy.context.selected_objects[0]; o.name=name; o.location=shift; o.data.materials.append(ma); bev=o.modifiers.new('edge','BEVEL'); bev.width=.12; bev.segments=2; return o
def cyl(loc,r,depth,axis,ma):
 rot=(0,0,0) if axis=='z' else (0,math.radians(90),0)
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth,location=loc,rotation=rot); o=bpy.context.object; o.data.materials.append(ma); return o
def cube(loc,scale,ma): bpy.ops.mesh.primitive_cube_add(location=loc,scale=scale); o=bpy.context.object; o.data.materials.append(ma); return o
def look(o,t): o.rotation_euler=(t-o.location).to_track_quat('-Z','Y').to_euler()
def setup(W,D,H):
 sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1500; sc.render.resolution_y=1050; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.world.use_nodes=True; sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.075,.08,1); sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=1.0; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=2.35
 cube((W/2,D/2,-2),(max(60,W),max(55,D),2),GROUND)
 target=Vector((W/2,D/2,H/2+8)); bpy.ops.object.camera_add(location=(-75,D+90,H+80)); cam=bpy.context.object; cam.data.type='ORTHO'; cam.data.ortho_scale=max(105,W+65); look(cam,target); sc.camera=cam
 for loc,en,size in [((-50,D+20,H+100),4800,115),((W+80,-20,H+85),3400,105),((W/2,D+100,H+45),2500,95)]: bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.data.energy=en; l.data.shape='DISK'; l.data.size=size; look(l,target)
def render(case,c):
 reset(); W,D,H=c['W'],c['D'],c['H']; kind,mode=c['kind'],c['mode']; prefix=f'GrowCentral_XIAO_{kind}_{mode}'
 imp(M/f'{prefix}_Base_V4_PROTOTYP.stl','Base',BLACK)
 lidshift=(0,0,H+13); imp(M/f'{prefix}_Lid_V4_PROTOTYP.stl','Lid',BLACK,lidshift); imp(M/f'{prefix}_Branding_V4_PROTOTYP.stl','Brand',GREEN,lidshift)
 for y in (8,D-8): cyl((-2,y,3.5),2.15,11,'z',BLUE); cyl((-2,y,H*.52),2.15,13,'x',CYAN)
 if mode=='FPC':
  shift=(0,18,0); imp(M/f'{prefix}_AntennaCarrier_V4_PROTOTYP.stl','Carrier',GREY,shift)
  px=(W-44)/2; pz=max(.6,(H-24)/2); cube((px+22,D+7.775+18,pz+12),(20,.175,10),ORANGE)
 else:
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=3.25,depth=15,location=(W/2,D+2,H/2),rotation=(math.radians(90),0,0)); bpy.context.object.data.materials.append(GOLD)
 setup(W,D,H); out=P/f'GrowCentral_{case}_V4_PROTOTYP_Montage.png'; bpy.context.scene.render.filepath=str(out); bpy.ops.render.render(write_still=True); print('RENDERED',out)
for case,c in CASES.items(): render(case,c)
