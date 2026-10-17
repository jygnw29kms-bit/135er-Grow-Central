import bpy, os, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
MODELS=os.path.join(ROOT,'models')
OUT=os.path.join(ROOT,'previews','GrowCentral_P2S_plate_dualcolor_CAD.png')
os.makedirs(os.path.dirname(OUT),exist_ok=True)

# reset
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# materials
def material(name, color, rough=0.36, metallic=0.0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    bs.inputs['Metallic'].default_value=metallic
    return m

BLACK=material('PLA Black',(0.045,0.052,0.058),0.38,0.0)
GREEN=material('GrowCentral Green',(0.055,0.62,0.20),0.32,0.0)
PLATE=material('P2S Plate',(0.18,0.19,0.20),0.48,0.12)
GRID=material('Grid',(0.22,0.24,0.25),0.55,0.0)


def import_stl(fn,name,mat):
    bpy.ops.wm.stl_import(filepath=os.path.join(MODELS,fn))
    o=bpy.context.selected_objects[0]
    o.name=name
    o.data.materials.append(mat)
    bev=o.modifiers.new('edge soften','BEVEL'); bev.width=0.18; bev.segments=2
    bpy.context.view_layer.objects.active=o
    try: bpy.ops.object.shade_smooth_by_angle()
    except: pass
    return o


def group_bounds(objs):
    pts=[]
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx


def place_group(objs,x,y):
    mn,mx=group_bounds(objs)
    dx=x-mn.x; dy=y-mn.y; dz=1.2-mn.z
    for o in objs:
        o.location += Vector((dx,dy,dz))

# Actual productive CAD STL geometry. Branding STL shares original CAD coordinates with lid STL.
pi_lid=import_stl('GrowCentral_Pi4_Lid_V2.stl','Pi4 Lid',BLACK)
pi_brand=import_stl('GrowCentral_Pi4_Branding_V2.stl','Pi4 Branding',GREEN)
place_group([pi_lid,pi_brand],14,15)

hub_base=import_stl('GrowCentral_XIAO_Hub_Base_V2.stl','Hub Base',BLACK)
place_group([hub_base],150,15)

hub_lid=import_stl('GrowCentral_XIAO_Hub_Lid_V2.stl','Hub Lid',BLACK)
hub_brand=import_stl('GrowCentral_XIAO_Hub_Branding_V2.stl','Hub Branding',GREEN)
place_group([hub_lid,hub_brand],145,88)

node_base=import_stl('GrowCentral_XIAO_Node_Base_V2.stl','Node Base',BLACK)
place_group([node_base],22,132)

node_lid=import_stl('GrowCentral_XIAO_Node_Lid_V2.stl','Node Lid',BLACK)
node_brand=import_stl('GrowCentral_XIAO_Node_Branding_V2.stl','Node Branding',GREEN)
place_group([node_lid,node_brand],88,136)

parts=[pi_lid,pi_brand,hub_base,hub_lid,hub_brand,node_base,node_lid,node_brand]

# 256 x 256 build plate, actual P2S-style working area representation
bpy.ops.mesh.primitive_cube_add(location=(128,128,-1.0), scale=(128,128,1.0))
plate=bpy.context.object; plate.name='P2S Build Plate'; plate.data.materials.append(PLATE)
bev=plate.modifiers.new('plate edge','BEVEL'); bev.width=3.0; bev.segments=5

# subtle 20 mm grid, geometry only for rendering
for v in range(20,256,20):
    bpy.ops.mesh.primitive_cube_add(location=(v,128,0.08), scale=(0.12,128,0.06))
    g=bpy.context.object; g.data.materials.append(GRID)
    bpy.ops.mesh.primitive_cube_add(location=(128,v,0.08), scale=(128,0.12,0.06))
    g=bpy.context.object; g.data.materials.append(GRID)

# camera + lighting
def look_at(obj,target):
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=OUT
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(0.10,0.11,0.12,1); bg.inputs['Strength'].default_value=0.95
scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=2.15

bpy.ops.object.camera_add(location=(310,-225,340))
cam=bpy.context.object; cam.data.type='ORTHO'; cam.data.ortho_scale=360; look_at(cam,Vector((128,128,5)))
scene.camera=cam

def area(loc,energy,size):
    bpy.ops.object.light_add(type='AREA',location=loc)
    l=bpy.context.object; l.data.energy=energy; l.data.shape='DISK'; l.data.size=size; look_at(l,Vector((128,128,5)))
area((20,-30,310),5000,170)
area((320,130,220),3600,150)
area((80,340,170),3000,140)

bpy.ops.render.render(write_still=True)
print('RENDERED',OUT)

