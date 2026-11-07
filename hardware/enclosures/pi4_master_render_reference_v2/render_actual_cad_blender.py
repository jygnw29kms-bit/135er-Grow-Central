# Blender 4.5: render actual FreeCAD STL exports (not generative imagery)
import bpy, math, os
from mathutils import Vector
ROOT=r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster"
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,rgb,rough=.55,metal=.04):
 m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1)
 m.use_nodes=True
 pr=m.node_tree.nodes.get("Principled BSDF")
 pr.inputs["Base Color"].default_value=(*rgb,1)
 pr.inputs["Roughness"].default_value=rough
 pr.inputs["Metallic"].default_value=metal
 return m
char=mat("Charcoal_PETG",(.072,.085,.093),.61)
green=mat("GrowCentral_Lime",(.12,.62,.08),.38)
ink=mat("Embossed_Black",(.024,.03,.032),.5)
metal=mat("Recessed_Metal_Screws",(.12,.13,.14),.38,.58)
floor=mat("Dark_studio",(.066,.074,.08),.78)
palette=[char,char,green,green,ink,green,char,green,metal]
objects=[]
for i in range(1,10):
 pfx=f"_{i:02d}_"
 fname=next((f for f in os.listdir(ROOT) if f.startswith(pfx) and f.endswith(".stl")),None)
 if not fname:continue
 bpy.ops.wm.stl_import(filepath=os.path.join(ROOT,fname))
 obj=bpy.context.object
 obj.name=os.path.splitext(fname)[0]
 obj.data.materials.clear();obj.data.materials.append(palette[i-1])
 if i==7:obj.hide_render=True
 bevel=obj.modifiers.new("Subtle FDM edge highlights","WEIGHTED_NORMAL")
 objects.append((i,obj))
bpy.ops.mesh.primitive_plane_add(size=500,location=(52,37,-2.8))
plane=bpy.context.object;plane.name="Studio_floor";plane.data.materials.append(floor)
def area(name,loc,power,size,color):
 bpy.ops.object.light_add(type="AREA",location=loc)
 a=bpy.context.object;a.name=name
 a.data.energy=power;a.data.shape='DISK';a.data.size=size;a.data.color=color
 a.rotation_euler=(Vector((52,37,14))-a.location).to_track_quat("-Z","Y").to_euler()
area("Softbox_left",(18,-80,150),95000,190,(.88,.95,1))
area("Softbox_green",(170,80,110),65000,140,(.68,1,.68))
area("Rim_top",(52,130,170),115000,140,(.9,.95,1))
bpy.ops.object.camera_add(location=(190,-170,138))
camera=bpy.context.object
target=Vector((53,37,17))
camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=158
bpy.context.scene.camera=camera
sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=24
sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
sc.world.color=(.14,.14,.14)
sc.view_settings.view_transform='AgX'
sc.render.filepath=os.path.join(ROOT,"GrowCentral_Pi4_ActualCAD_Studio.png")
bpy.ops.render.render(write_still=True)
# Second render: real STL lid geometry separated in Z, same meshes, not redesign
for i,obj in objects:
 if i in (2,4,5,6,9):
  obj.location.z+=21
 if i==3:obj.location.z+=8
camera.location=(200,-175,153)
target=Vector((53,37,28))
camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=173
sc.render.filepath=os.path.join(ROOT,"GrowCentral_Pi4_ActualCAD_Exploded.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,"GrowCentral_Pi4_RenderScene.blend"))
print("RENDER_COMPLETE")
