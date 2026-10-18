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
BODY=mat('Body',(.075,.09,.115),.30); GREEN=mat('Brand',(.04,.92,.28)); BLUE=mat('Liegend',(.03,.28,1.0),.22); CYAN=mat('Stehend',(0,.85,1.0),.22); ORANGE=mat('FPC',(1.0,.30,.01),.24); GOLD=mat('SMA',(1.0,.62,.06),.20,.55); GREY=mat('Carrier',(.20,.24,.29),.34); GROUND=mat('Ground',(.62,.66,.70),.76)
def reset(): bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def imp(path,name,ma,shift=(0,0,0)):
 bpy.ops.wm.stl_import(filepath=str(path)); o=bpy.context.selected_objects[0]; o.name=name; o.location=shift; o.data.materials.append(ma); bev=o.modifiers.new('edge','BEVEL'); bev.width=.12; bev.segments=2; return o
def cyl(loc,r,depth,axis,ma):
 rot=(0,0,0) if axis=='z' else (0,math.radians(90),0)
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth,location=loc,rotation=rot); o=bpy.context.object; o.data.materials.append(ma); return o
def cube(loc,scale,ma): bpy.ops.mesh.primitive_cube_add(location=loc,scale=scale); o=bpy.context.object; o.data.materials.append(ma); return o
def look(o,t): o.rotation_euler=(t-o.location).to_track_quat('-Z','Y').to_euler()
def setup(W,D,H):
 sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1500; sc.render.resolution_y=900; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.world.use_nodes=True; sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.86,.87,.89,1); sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.75; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=.35
 cube((W/2,D/2,-2.5),(max(62,W),max(58,D),2.5),GROUND)
 target=Vector((W/2,D/2,H/2+6)); bpy.ops.object.camera_add(location=(-78,D+92,H+76)); cam=bpy.context.object; cam.data.type='ORTHO'; cam.data.ortho_scale=max(92,W+46); look(cam,target); sc.camera=cam
 for loc,en,size in [((-55,D+12,H+95),3600,105),((W+75,-25,H+75),2800,95),((W/2,D+90,H+38),1800,80)]: bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.data.energy=en; l.data.shape='DISK'; l.data.size=size; look(l,target)
def render(case,c):
 reset(); W,D,H=c['W'],c['D'],c['H']; kind,mode=c['kind'],c['mode']; prefix=f'GrowCentral_XIAO_{kind}_{mode}'
 imp(M/f'{prefix}_Base_V5_PROTOTYP.stl','Base',BODY)
 lidshift=(0,0,H+13); imp(M/f'{prefix}_Lid_V5_PROTOTYP.stl','Lid',BODY,lidshift); imp(M/f'{prefix}_Branding_V5_PROTOTYP.stl','Brand',GREEN,lidshift)
 for x in (11,W-11): cyl((x,-2,3.25),2.15,10.5,'z',BLUE)
 for y in (10,D-10): cyl((-1.5,y,H*.56),2.15,13,'x',CYAN)
 if mode=='FPC':
  shift=(0,18,0); imp(M/f'{prefix}_AntennaCarrier_V5_PROTOTYP.stl','Carrier',GREY,shift)
  px=(W-44)/2; pz=max(.6,(H-24)/2); cube((px+22,D+7.775+18,pz+12),(20,.175,10),ORANGE)
 else:
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=3.25,depth=15,location=(W/2,D+2,H/2),rotation=(math.radians(90),0,0)); bpy.context.object.data.materials.append(GOLD)
 setup(W,D,H); out=P/f'GrowCentral_{case}_V5_PROTOTYP_Montage.png'; bpy.context.scene.render.filepath=str(out); bpy.ops.render.render(write_still=True); print('RENDERED',out)
 cam=bpy.context.scene.camera; cam.location=(-78,-72,H+74); look(cam,Vector((W/2,D/2,H/2+5))); out2=P/f'GrowCentral_{case}_V5_PROTOTYP_Montage_MountingZones.png'; bpy.context.scene.render.filepath=str(out2); bpy.ops.render.render(write_still=True); print('RENDERED',out2)
for case,c in CASES.items(): render(case,c)


