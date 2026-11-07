# GrowCentral Raspberry Pi4: Bambu P2S 256x256 single build plate in standard 3MF
# Source: FreeCAD actual CAD STLs. 3MF is geometry plate, not pre-sliced gcode.
import os,glob,zipfile,traceback
import trimesh,numpy as np
import xml.etree.ElementTree as etree
P=r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster"
OUT=os.path.join(P,"GrowCentral_Pi4_P2S_FinalMaster_Plate.3mf")
LOG=os.path.join(P,"p2s_3mf_validation.txt")
scene=trimesh.Scene()
def mesh(number):
 path=os.path.join(P,"P2S_Wordmark_FDM_Repaired.stl") if number==5 else next(x for x in glob.glob(os.path.join(P,f"_{number:02d}_*.stl")))
 return trimesh.load_mesh(path,process=True)
def add(index,tx,ty,tz,label,color):
 m=mesh(index)
 m.apply_translation([tx,ty,tz])
 m.visual.vertex_colors=np.array([color[0],color[1],color[2],255],dtype=np.uint8)
 scene.add_geometry(m,geom_name=label,node_name=label)
 return m
# Plate layout 256mm x 256mm: separate positions for base and lid
# base Y max 83 due to rear mounting ears, total extent 16..99.
parts=[]
parts.append(add(1,16,16,0,"01_BASE_PETG_BLACK",(40,42,44)))
parts.append(add(3,16,16,0,"02_GREEN_SEAM_ON_BASE",(58,196,58)))
# Lid orientation: locating lip facing plate, ornamental top remains visible.
# 26.8 is bottom lip datum, so Z=0 on bed.
parts.append(add(2,137,16,-26.8,"03_LID_PETG_BLACK",(40,42,44)))
parts.append(add(4,137,16,-26.8,"04_GREEN_CORNER_DETAILS",(58,196,58)))
parts.append(add(5,137,16,-26.8,"05_GROWCENTRAL_EMBOSSED_BLACK",(20,22,23)))
parts.append(add(6,137,16,-26.8,"06_GREEN_LEAF",(58,196,58)))
# Four green foot pads grouped as one independent printable multibody mesh
parts.append(add(8,123,116,2.6,"07_GREEN_FOUR_FEET",(58,196,58)))
# Export standard 3MF
scene.export(OUT,file_type="3mf")
# Verify actual resulting 3MF zip, import geometry, bed coordinate extents, count
with zipfile.ZipFile(OUT) as z:
 bad=z.testzip()
 assert bad is None, f"ZIP integrity error: {bad}"
 names=z.namelist()
 assert "3D/3dmodel.model" in names, names
 root=etree.fromstring(z.read("3D/3dmodel.model"))
 ns={"m":"http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
 build=root.findall(".//m:build/m:item",ns)
 objs=root.findall(".//m:resources/m:object",ns)
 assert len(build)==7,(len(build),len(objs))
imported=trimesh.load(OUT,force="scene")
mn,mx=imported.bounds
assert mn[0]>=0 and mn[1]>=0 and mn[2]>-0.01, (mn,mx)
assert mx[0]<=256 and mx[1]<=256 and mx[2]<=256,(mn,mx)
with open(LOG,"w",encoding="utf8") as f:
 f.write("FILE: "+OUT+"\n")
 f.write("Size: "+str(os.path.getsize(OUT))+" bytes\n")
 f.write(f"ZIP OK, resources {len(objs)}, build objects {len(build)}\n")
 f.write("Plate extents mm min="+str(mn.round(2))+" max="+str(mx.round(2))+"\n")
 for x in parts:f.write(f"{len(x.faces)} faces, watertight={x.is_watertight}, box={x.bounds.round(2).tolist()}\n")
 f.write("Bambu P2S: geometry prepared for 256x256 bed. Set printer P2S / PETG / 0.4 mm nozzle / AMS material assignments in Bambu Studio. Slice and inspect supports BEFORE printing.\n")
print("CREATED",OUT,os.path.getsize(OUT),"bytes; scene bounds",mn,mx)
