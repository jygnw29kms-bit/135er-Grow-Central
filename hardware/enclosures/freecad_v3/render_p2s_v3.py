import bpy, os, zipfile, xml.etree.ElementTree as ET, json, math
from pathlib import Path
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parent; MODELS=ROOT/'models'; PLATES=ROOT/'printplates'; PREV=ROOT/'previews'; PREV.mkdir(exist_ok=True)
CASES=['Pi4','Node_FPC','Node_EXT','Hub_FPC','Hub_EXT']
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'; q=lambda x:f'{{{NS}}}{x}'

def mat(name,color,rough=.38):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=rough; return m
BLACK=mat('PLA Black',(0.075,0.085,0.095),.34); GREEN=mat('Brand Green',(0.04,0.72,0.20),.30); PLATE=mat('P2S Plate',(0.14,0.15,0.16),.5); GRID=mat('Grid',(0.25,0.27,0.29),.55)

def parse_3mf(path):
 with zipfile.ZipFile(path) as z:
  m=ET.fromstring(z.read('3D/3dmodel.model')); s=ET.fromstring(z.read('Metadata/model_settings.config'))
  names={}
  for o in s.findall('object'):
   names[o.attrib['id']]=next((md.attrib.get('value','') for md in o.findall('metadata') if md.attrib.get('key')=='name'),'')
  items=[]
  for x in m.find(q('build')).findall(q('item')):
   vals=[float(v) for v in x.attrib['transform'].split()]
   items.append((names.get(x.attrib['objectid'],''),vals))
  return items

def matrix_3mf(v):
 # 3MF affine values: m00 m01 m02 m10 m11 m12 m20 m21 m22 tx ty tz
 return Matrix(((v[0],v[3],v[6],v[9]),(v[1],v[4],v[7],v[10]),(v[2],v[5],v[8],v[11]),(0,0,0,1)))

def reset():
 bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def add_plate():
 bpy.ops.mesh.primitive_cube_add(location=(128,128,-1),scale=(128,128,1)); o=bpy.context.object; o.data.materials.append(PLATE)
 bev=o.modifiers.new('edge','BEVEL'); bev.width=3; bev.segments=4
 for a in range(20,256,20):
  bpy.ops.mesh.primitive_cube_add(location=(a,128,.05),scale=(.10,128,.05)); bpy.context.object.data.materials.append(GRID)
  bpy.ops.mesh.primitive_cube_add(location=(128,a,.05),scale=(128,.10,.05)); bpy.context.object.data.materials.append(GRID)

def look(o,t): o.rotation_euler=(t-o.location).to_track_quat('-Z','Y').to_euler()
def setup():
 sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE_NEXT'; sc.render.resolution_x=1400; sc.render.resolution_y=1050; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.world.use_nodes=True
 bg=sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(.07,.075,.08,1); bg.inputs['Strength'].default_value=.8; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=2.1
 bpy.ops.object.camera_add(location=(315,-210,330)); cam=bpy.context.object; cam.data.type='ORTHO'; cam.data.ortho_scale=345; look(cam,Vector((128,128,5))); sc.camera=cam
 for loc,en,size in [((15,-30,310),4300,170),((320,110,240),3000,150),((70,330,180),2200,140)]:
  bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.data.energy=en; l.data.shape='DISK'; l.data.size=size; look(l,Vector((128,128,5)))

def render(case):
 reset(); add_plate()
 plate=PLATES/f'GrowCentral_{case}_P2S_V3.3mf'; items=parse_3mf(plate)
 for name,tr in items:
  src=MODELS/name
  if not src.exists(): raise RuntimeError(f'missing {src}')
  bpy.ops.wm.stl_import(filepath=str(src)); o=bpy.context.selected_objects[0]; o.name=name; o.matrix_world=matrix_3mf(tr); o.data.materials.append(GREEN if 'Branding' in name else BLACK)
  bev=o.modifiers.new('soft','BEVEL'); bev.width=.12; bev.segments=2
 setup(); out=PREV/f'GrowCentral_{case}_P2S_V3_plate.png'; bpy.context.scene.render.filepath=str(out); bpy.ops.render.render(write_still=True); print('RENDERED',out)
for c in CASES: render(c)

