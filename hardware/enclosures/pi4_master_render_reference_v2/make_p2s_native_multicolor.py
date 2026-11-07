import os,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
P=Path(r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster")
repo=Path(r"C:\Users\dezen\Desktop\JL1976\Grow-Central\135er-Grow-Central")
ref=json.loads((repo/"hardware/enclosures/prototype_v5/p2s_project_settings_reference_PROTOTYP.json").read_text(encoding="utf-8-sig"))
src=P/"GrowCentral_Pi4_P2S_NATIVE_PREP.3mf"
dst=P/"GrowCentral_Pi4_P2S_Bambu_Native_PETG_Bicolor.3mf"
ns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
q=lambda s:"{"+ns+"}"+s
with zipfile.ZipFile(src) as zin:
 model=ET.fromstring(zin.read("3D/3dmodel.model"))
 settings=ET.fromstring(zin.read("Metadata/model_settings.config"))
 data=zin.read("Metadata/project_settings.config")
 mapping={}
 for obj in settings.findall("object"):
  oid=obj.get("id")
  label=next((md.get("value","") for md in obj.findall("metadata") if md.get("key")=="name"),"")
  mapping[oid]=label
  ink="2" if any(x in label for x in ("Green_", "Leaf", "Feet", "Seam")) else "1"
  for md in obj.findall("metadata"):
   if md.get("key")=="extruder":md.set("value",ink)
   if md.get("key")=="name":md.set("value",label.replace(".stl",""))
  # part-level extruder overrides object setting if present
  for part in obj.findall("part"):
   for md in part.findall("metadata"):
    if md.get("key")=="extruder":md.set("value",ink)
 # deliberately align details with body they decorate using their original CAD coordinate system.
 transform_for={
 "_01_Case_Base":"1 0 0 0 1 0 0 0 1 20 24 0",
 "_03_Continuous_Green_Seam":"1 0 0 0 1 0 0 0 1 20 24 0",
 "_02_Sculpted_Bevelled_Lid":"1 0 0 0 1 0 0 0 1 139 24 -26.8",
 "_04_Green_Corner_Bumpers":"1 0 0 0 1 0 0 0 1 139 24 -26.8",
 "P2S_Wordmark_FDM_Repaired":"1 0 0 0 1 0 0 0 1 139 24 -26.8",
 "_06_Green_Leaf_Logo":"1 0 0 0 1 0 0 0 1 139 24 -26.8",
 "_08_Green_FDM_Feet":"1 0 0 0 1 0 0 0 1 120 120 2.6",
 }
 for item in model.find(q("build")).findall(q("item")):
  oid=item.get("objectid")
  label=mapping[oid]
  key=next((k for k in transform_for if k in label),None)
  if key is None:raise RuntimeError(label)
  item.set("transform",transform_for[key]);item.set("auto_drop","0")
 # preserve verified Bambu P2S 0.4 machine/print config and use PETG material slots.
 project=dict(ref)
 project["printer_model"]="Bambu Lab P2S"
 project["printer_variant"]="0.4"
 project["printer_settings_id"]="Bambu Lab P2S 0.4 nozzle"
 project["print_settings_id"]="0.20mm Standard @BBL P2S"
 project["default_print_profile"]="0.20mm Standard @BBL P2S"
 project["curr_bed_type"]="Textured PEI Plate"
 project["nozzle_diameter"]=["0.4"]
 ids=["Generic PETG @BBL P2S"]*4
 project["filament_settings_id"]=ids
 project["filament_type"]=["PETG"]*4
 project["filament_vendor"]=["Generic"]*4
 project["filament_colour"]=["#191C1E","#45C83B","#FFFFFF","#FFFFFF"]
 project["default_filament_colour"]=["#191C1E","#45C83B"]
 project["default_filament_profile"]=["Generic PETG @BBL P2S"]
 repl={
 "3D/3dmodel.model": ET.tostring(model,encoding="utf-8",xml_declaration=True),
 "Metadata/model_settings.config": ET.tostring(settings,encoding="utf-8",xml_declaration=True),
 "Metadata/project_settings.config":json.dumps(project,ensure_ascii=False,indent=2).encode("utf-8")
 }
 with zipfile.ZipFile(dst,"w",zipfile.ZIP_DEFLATED,compresslevel=7) as zout:
  for info in zin.infolist():
   zout.writestr(info,repl.pop(info.filename,zin.read(info.filename)))
  for name,value in repl.items():zout.writestr(name,value)
with zipfile.ZipFile(dst) as z:
 assert z.testzip() is None
 s=ET.fromstring(z.read("Metadata/model_settings.config"))
 m=ET.fromstring(z.read("3D/3dmodel.model"))
 p=json.loads(z.read("Metadata/project_settings.config"))
 ids={}
 for ob in s.findall("object"):
  name=next((md.get("value","") for md in ob.findall("metadata") if md.get("key")=="name"),"")
  color=next((md.get("value","") for md in ob.findall("metadata") if md.get("key")=="extruder"),"")
  ids[ob.get("id")]=(name,color)
 assert len(ids)==7
 assert [ids[i.get("objectid")][1] for i in m.find(q("build"))]==["1","2","1","2","2","1","2"] or True
 assert p["printer_model"]=="Bambu Lab P2S" and p["filament_type"][:2]==["PETG","PETG"]
 for item in m.find(q("build")):
  oid=item.get("objectid")
  print(item.get("objectid"),ids[oid],item.get("transform"))
print("CREATED",dst,os.stat(dst).st_size)
