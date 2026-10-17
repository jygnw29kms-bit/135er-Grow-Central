import bpy, os, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
MODELS=os.path.join(ROOT,'models')
PREV=os.path.join(ROOT,'previews')
HERO=os.path.join(PREV,'hero')
os.makedirs(PREV,exist_ok=True); os.makedirs(HERO,exist_ok=True)

PARTS=[
('GrowCentral_Pi4_Base_V2.stl','Pi4 Base'),('GrowCentral_Pi4_Lid_V2.stl','Pi4 Lid'),
('GrowCentral_XIAO_Node_Base_V2.stl','XIAO Node Base'),('GrowCentral_XIAO_Node_Lid_V2.stl','XIAO Node Lid'),
('GrowCentral_XIAO_Hub_Base_V2.stl','XIAO Hub Base'),('GrowCentral_XIAO_Hub_Lid_V2.stl','XIAO Hub Lid')]
PRODUCTS=[
('Pi4','GrowCentral_Pi4_Base_V2.stl','GrowCentral_Pi4_Lid_V2.stl'),
('XIAO_Node','GrowCentral_XIAO_Node_Base_V2.stl','GrowCentral_XIAO_Node_Lid_V2.stl'),
('XIAO_Hub','GrowCentral_XIAO_Hub_Base_V2.stl','GrowCentral_XIAO_Hub_Lid_V2.stl')]

def reset():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for d in (bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.cameras,bpy.data.lights):
        pass

def mat(name,color,metal=0.0,rough=.34):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal; bs.inputs['Roughness'].default_value=rough
    return m

def import_stl(path,name,material):
    bpy.ops.wm.stl_import(filepath=path)
    o=bpy.context.selected_objects[0]; o.name=name
    o.data.materials.append(material)
    bev=o.modifiers.new('micro_edge','BEVEL'); bev.width=.35; bev.segments=3
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.shade_smooth_by_angle()
    return o

def bounds(objs):
    pts=[]
    for o in objs:
        for c in o.bound_box: pts.append(o.matrix_world @ Vector(c))
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx,(mn+mx)/2,mx-mn

def look_at(obj,target):
    direction=target-obj.location
    obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

def setup_scene(objs,out,title,accent=False):
    sc=bpy.context.scene
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1400; sc.render.resolution_y=1000; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False
    sc.render.filepath=out
    sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(0.12,0.14,0.15,1); bg.inputs['Strength'].default_value=0.65
    sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=1.2
    mn,mx,ctr,size=bounds(objs); span=max(size.x,size.y,size.z)
    # floor
    bpy.ops.mesh.primitive_plane_add(size=span*5, location=(ctr.x,ctr.y,mn.z-1.2))
    floor=bpy.context.object; floor.data.materials.append(mat('Floor',(0.14,0.15,0.16),0,.52))
    # accent strip behind model
    if accent:
        bpy.ops.mesh.primitive_cube_add(location=(ctr.x,ctr.y+span*.78,mn.z+span*.025),scale=(span*.8,span*.035,span*.025))
        strip=bpy.context.object; strip.data.materials.append(mat('GC Accent',(0.10,0.48,0.22),0,.28))
    # camera
    bpy.ops.object.camera_add(location=(ctr.x+span*1.45,ctr.y-span*1.65,ctr.z+span*1.25))
    cam=bpy.context.object; look_at(cam,ctr); cam.data.type='ORTHO'; cam.data.ortho_scale=span*1.72; sc.camera=cam
    # lights
    def area(loc,energy,sizev):
        bpy.ops.object.light_add(type='AREA', location=loc)
        l=bpy.context.object; l.data.energy=energy; l.data.shape='DISK'; l.data.size=sizev; look_at(l,ctr)
    area((ctr.x-span*.9,ctr.y-span*.7,ctr.z+span*1.5),2600,span*.75)
    area((ctr.x+span*1.25,ctr.y+span*.45,ctr.z+span*.55),1800,span*.65)
    area((ctr.x-span*.3,ctr.y+span*1.5,ctr.z+span*.8),2200,span*.55)
    sc.render.image_settings.color_mode='RGBA'
    bpy.ops.render.render(write_still=True)

def individual():
    material=mat('GC Anthracite',(0.38,0.42,0.44),0.08,.34)
    for fn,label in PARTS:
        reset(); material=mat('GC Anthracite',(0.38,0.42,0.44),0.08,.34)
        o=import_stl(os.path.join(MODELS,fn),label,material)
        out=os.path.join(PREV,fn.replace('.stl','_render.png'))
        setup_scene([o],out,label,accent=True)
        print('rendered',out)

def heroes():
    for tag,bfn,lfn in PRODUCTS:
        reset(); dark=mat('GC Anthracite',(0.34,0.38,0.40),0.08,.34); lidmat=mat('GC Lid',(0.46,0.50,0.52),0.06,.30)
        base=import_stl(os.path.join(MODELS,bfn),tag+' Base',dark)
        lid=import_stl(os.path.join(MODELS,lfn),tag+' Lid',lidmat)
        bmn,bmx,bctr,bsize=bounds([base]); lmn,lmx,lctr,lsize=bounds([lid])
        # Exploded product view: lid behind/right and raised, still same real geometry.
        lid.location.x += max(bsize.x,lsize.x)*0.28
        lid.location.y += max(bsize.y,lsize.y)*0.18
        lid.location.z += bsize.z + max(8.0,bsize.z*.18)
        lid.rotation_euler[2]=math.radians(-8)
        out=os.path.join(HERO,'GrowCentral_'+tag+'_hero.png')
        setup_scene([base,lid],out,tag,accent=True)
        print('hero',out)

individual(); heroes(); print('ALL RENDERS DONE')
