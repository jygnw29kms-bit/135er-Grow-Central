# Assemble one-bed two-colour Bambu 3MF from Bambu Studio's own export
import zipfile,copy,json,os,hashlib
from lxml import etree as E
from pathlib import Path
P=Path(r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster")
SRC=P/"SLICE_TEST/bambu_from_generic.3mf"
DST=P/"GrowCentral_Pi4_P2S_CAD_ASSEMBLY_CANDIDATE.3mf"
MODEL="3D/3dmodel.model"; SETTINGS="Metadata/model_settings.config"; PROJECT="Metadata/project_settings.config"
CORE="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
Q=lambda k:f"{{{CORE}}}{k}"
# mesh vertex offsets are normalized to centre; these are desired centre coordinates for build plate
coords={
2:(72.5,65.5,14.275), # base
6:(72.5,61.5,28.71), # seam at base location
4:(191.5,61.5,4.85), # lid
10:(191.5,69.5,5.275), # corner bumpers (actual Y center 37.5 + 24 =61.5, correction below)
12:(191.5,61.669,10.2), # black wordmark
14:(193.,76.,10.125), # green leaf
8:(172.5,157.5,1.3), # feet
}
coords[10]=(191.5,61.5,5.275)
groups={2:[2,6],4:[4,10,12,14],8:[8]}
# part extruder identifiers
inks={2:"1",6:"2",4:"1",10:"2",12:"1",14:"2",8:"2"}
labels={2:"BODEN + GRUENE ZIERFUGE",4:"DECKEL + BRANDING + AKZENTE",8:"VIER GRUENE FUESSE"}
with zipfile.ZipFile(SRC) as z:
 m=E.fromstring(z.read(MODEL))
 cfg=E.fromstring(z.read(SETTINGS))
 proj=json.loads(z.read(PROJECT))
 resources=m.find(Q("resources"));build=m.find(Q("build"))
 objs={int(o.get("id")):o for o in resources.findall(Q("object"))}
 cobj={int(o.get("id")):o for o in cfg.findall("object")}
 for parent,children in groups.items():
  base=objs[parent]
  components=base.find(Q("components"))
  basecenter=coords[parent]
  for sub in children:
   if sub==parent:continue
   comp=copy.deepcopy(objs[sub].find(Q("components"))[0])
   dx,dy,dz=[coords[sub][i]-basecenter[i] for i in range(3)]
   comp.set("transform",f"1 0 0 0 1 0 0 0 1 {dx:.5f} {dy:.5f} {dz:.5f}")
   components.append(comp)
   for part in cobj[sub].findall("part"):
    newpart=copy.deepcopy(part)
    newpart.insert(0,E.Element("metadata",key="extruder",value=inks[sub]))
    cobj[parent].append(newpart)
  for md in cobj[parent].findall("metadata"):
   if md.get("key")=="name":md.set("value",labels[parent])
   elif md.get("key")=="extruder":md.set("value",inks[parent])
  for part in cobj[parent].findall("part"):
   if not any(q.get("key")=="extruder" for q in part.findall("metadata")):
    part.insert(0,E.Element("metadata",key="extruder",value=inks[parent]))
 for oid in list(objs):
  if oid not in groups:
   resources.remove(objs[oid]);cfg.remove(cobj[oid])
 for item in list(build):build.remove(item)
 pns="{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}UUID"
 for oid in groups:
  item=E.SubElement(build,Q("item"),objectid=str(oid),printable="1")
  item.set(pns,f"000000{oid:02x}-b1ec-4553-aec9-835e5b724bb4")
  xyz=coords[oid]
  item.set("transform","1 0 0 0 1 0 0 0 1 "+" ".join(f"{v:.5f}" for v in xyz))
 # Bambu specific slicer metadata for P2S
 ref=json.loads((P.parent/"135er-Grow-Central/hardware/enclosures/prototype_v5/p2s_project_settings_reference_PROTOTYP.json").read_text(encoding="utf-8-sig"))
 # Preserve machine/process settings, but normalize every four-slot filament vector
 # against the PETG reference (slot 4, index 3) BEFORE assigning black/green.
 for key,value in list(ref.items()):
  if isinstance(value,list) and len(value)==4 and key not in ("filament_colour","filament_multi_colour","printable_area","bed_exclude_area"):
   ref[key]=[value[3]]*4
 ref["printer_model"]="Bambu Lab P2S"
 ref["printer_variant"]="0.4"
 ref["printer_settings_id"]="Bambu Lab P2S 0.4 nozzle"
 ref["print_settings_id"]="0.20mm Standard @BBL P2S"
 ref["default_print_profile"]="0.20mm Standard @BBL P2S"
 ref["nozzle_diameter"]=["0.4"]
 ref["curr_bed_type"]="Textured PEI Plate"
 ref["filament_settings_id"]=["Generic PETG @BBL P2S"]*4
 ref["filament_type"]=["PETG"]*4
 ref["filament_colour"]=["#16191C","#45C83B","#FFFFFF","#FFFFFF"]
 ref["default_filament_colour"]=["#16191C","#45C83B"]
 ref["filament_vendor"]=["Generic"]*4
 # avoid invalid carry-over values from old P2S reference
 if str(ref.get("raft_first_layer_expansion"))=="-1":ref["raft_first_layer_expansion"]="0"
 if str(ref.get("tree_support_wall_count"))=="-1":ref["tree_support_wall_count"]="1"
 # plate contents in native model_settings.config
 plates=cfg.findall("plate")
 for plate in plates:
  for mi in plate.findall("model_instance"):plate.remove(mi)
  if plate is not plates[0]:cfg.remove(plate)
 plate=plates[0]
 for idx,oid in enumerate(groups):
  mi=E.SubElement(plate,"model_instance")
  for key,val in (("object_id",str(oid)),("instance_id","0"),("identify_id",str(oid))):
   E.SubElement(mi,"metadata",key=key,value=val)
 repl={
 MODEL:E.tostring(m,encoding="utf-8",xml_declaration=True),
 SETTINGS:E.tostring(cfg,encoding="utf-8",xml_declaration=True),
 PROJECT:json.dumps(ref,indent=2,ensure_ascii=False).encode()
 }
 with zipfile.ZipFile(DST,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
  for info in z.infolist():
   if info.filename in ("Metadata/plate_2.png","Metadata/plate_2_small.png","Metadata/plate_no_light_2.png","Metadata/top_2.png","Metadata/pick_2.png"):continue
   zout.writestr(info,repl.pop(info.filename,z.read(info.filename)))
  for k,v in repl.items():zout.writestr(k,v)
with zipfile.ZipFile(DST) as z:
 assert z.testzip() is None
 doc=E.fromstring(z.read(MODEL))
 assert len(doc.find(Q("build")))==3
 assert [len(o.find(Q("components"))) for o in doc.find(Q("resources")) if o.get("id") in ("2","4","8")]==[2,4,1]
 print("VERIFIED objects 3 components 7; file size",DST.stat().st_size)
 print("SHA256",hashlib.sha256(DST.read_bytes()).hexdigest())
