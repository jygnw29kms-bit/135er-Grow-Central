import os, struct, zipfile, json, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MODELS=ROOT/'models'
OUT=ROOT/'printplates'
OUT.mkdir(exist_ok=True)
TEMPLATE=Path(r'C:\Users\dezen\Desktop\PRINTBENCH-Studio\LST-Klammer\LST-Klammer-P2S-24x-4mm.3mf')
TARGET=OUT/'GrowCentral_P2S_Pi4Lid_Node_Hub_PLA_Black.3mf'

parts=[
 ('Pi4 Lid',MODELS/'GrowCentral_Pi4_Lid_V2.stl',(18,18),True),
 ('XIAO Hub Base',MODELS/'GrowCentral_XIAO_Hub_Base_V2.stl',(138,18),False),
 ('XIAO Hub Lid',MODELS/'GrowCentral_XIAO_Hub_Lid_V2.stl',(138,82),True),
 ('XIAO Node Base',MODELS/'GrowCentral_XIAO_Node_Base_V2.stl',(18,116),False),
 ('XIAO Node Lid',MODELS/'GrowCentral_XIAO_Node_Lid_V2.stl',(78,116),True),
]

def read_stl(path):
    b=path.read_bytes()
    is_bin=len(b)>=84 and 84+struct.unpack('<I',b[80:84])[0]*50==len(b)
    tris=[]
    if is_bin:
        n=struct.unpack('<I',b[80:84])[0]; off=84
        for _ in range(n):
            vals=struct.unpack('<12fH',b[off:off+50]); off+=50
            tris.append((vals[3:6],vals[6:9],vals[9:12]))
    else:
        verts=[]
        for line in b.decode('utf-8','ignore').splitlines():
            s=line.strip().split()
            if len(s)==4 and s[0].lower()=='vertex':
                verts.append(tuple(map(float,s[1:])))
                if len(verts)==3: tris.append(tuple(verts)); verts=[]
    return tris

def transform(tris,xy,flip):
    pts=[]
    for tri in tris:
        nt=[]
        for x,y,z in tri:
            if flip: y,z=-y,-z
            nt.append((x,y,z)); pts.append((x,y,z))
        tri=tuple(nt)
    xmin=min(p[0] for p in pts); ymin=min(p[1] for p in pts); zmin=min(p[2] for p in pts)
    out=[]
    for tri in tris:
        nt=[]
        for x,y,z in tri:
            if flip: y,z=-y,-z
            nt.append((x-xmin+xy[0],y-ymin+xy[1],z-zmin))
        out.append(tuple(nt))
    return out

def mesh_xml(obj_id,name,tris):
    vmap={}; verts=[]; faces=[]
    for tri in tris:
        ids=[]
        for p in tri:
            key=tuple(round(v,6) for v in p)
            idx=vmap.get(key)
            if idx is None:
                idx=len(verts); vmap[key]=idx; verts.append(key)
            ids.append(idx)
        faces.append(tuple(ids))
    out=[f'<object id="{obj_id}" type="model" name="{name}"><mesh><vertices>']
    out += [f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x,y,z in verts]
    out.append('</vertices><triangles>')
    out += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in faces]
    out.append('</triangles></mesh></object>')
    return ''.join(out),len(faces)

objects=[]; builds=[]; settings=['<?xml version="1.0" encoding="UTF-8"?><config>']
for i,(name,path,xy,flip) in enumerate(parts,1):
    tris=transform(read_stl(path),xy,flip)
    objxml,fc=mesh_xml(i,name,tris); objects.append(objxml); builds.append(f'<item objectid="{i}"/>')
    settings.append(f'<object id="{i}"><metadata key="name" value="{name}"/><metadata key="extruder" value="1"/><metadata face_count="{fc}"/><part id="{i}" subtype="normal_part"><metadata key="name" value="{name}"/><metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/><mesh_stat face_count="{fc}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/></part></object>')
settings.append('<plate><metadata key="plater_id" value="1"/><metadata key="plater_name" value="Grow-Central P2S PLA Black"/></plate></config>')
model='<?xml version="1.0" encoding="UTF-8"?><model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter" xml:lang="en-US"><metadata name="Application">BambuStudio</metadata><metadata name="Title">Grow-Central P2S Pi4 Lid Node Hub</metadata><resources>'+''.join(objects)+'</resources><build>'+''.join(builds)+'</build></model>'

with zipfile.ZipFile(TEMPLATE,'r') as zin:
    project=json.loads(zin.read('Metadata/project_settings.config'))
    project['default_print_profile']='0.20mm Standard @BBL P2S'
    project['default_filament_profile']=['Bambu PLA Basic @BBL P2S']
    project['filament_settings_id']=['Bambu PLA Basic @BBL P2S']
    project['filament_type']=['PLA']
    project['filament_colour']=['#000000']
    project['default_filament_colour']=['#000000']
    project['printer_model']='Bambu Lab P2S'
    project['printer_variant']='0.4'
    project['nozzle_diameter']=['0.4']
    ct=zin.read('[Content_Types].xml'); rels=zin.read('_rels/.rels')
with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('[Content_Types].xml',ct)
    z.writestr('_rels/.rels',rels)
    z.writestr('3D/3dmodel.model',model.encode())
    z.writestr('Metadata/model_settings.config',''.join(settings).encode())
    z.writestr('Metadata/project_settings.config',json.dumps(project,ensure_ascii=False,indent=2).encode())
print(TARGET)
print('parts',len(parts),'profile',project['default_print_profile'],'filament',project['default_filament_profile'][0],project['filament_colour'][0])