import zipfile,json,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
P=Path(r"C:\Users\dezen\Desktop\JL1976\Grow-Central\Pi4-FinalMaster")
SRC=P/"SLICE_TEST/bambu_grouped_slice_PETG_v2.3mf"
TARGET=P/"GrowCentral_Pi4_P2S_PETG_BICOLOR_SLICED.3mf"
REPORT=P/"GrowCentral_Pi4_P2S_PETG_BICOLOR_VALIDATION.txt"
with zipfile.ZipFile(SRC) as z:
 assert z.testzip() is None
 names=z.namelist()
 assert "Metadata/plate_1.gcode" in names
 gc=z.read("Metadata/plate_1.gcode").decode("utf-8",errors="replace")
 assert len(gc)>1000000
 proj=json.loads(z.read("Metadata/project_settings.config"))
 assert proj["printer_model"]=="Bambu Lab P2S"
 assert proj["printer_variant"]=="0.4"
 assert proj["filament_type"][:2]==["PETG","PETG"]
 assert proj["filament_density"][:2]==["1.27","1.27"]
 assert proj["textured_plate_temp"][:2]==["70","70"]
 assert proj["printable_area"]==["0x0","256x0","256x256","0x256"]
 ns={"m":"http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
 model=ET.fromstring(z.read("3D/3dmodel.model"))
 objs=model.find("m:resources",ns)
 build=model.find("m:build",ns)
 assert len(build)==3
 assert sorted(len(x.find("m:components",ns)) for x in objs.findall("m:object",ns))==[1,2,4]
 materials=re.search(r"(?m)^; filament: ([0-9,]+)",gc)
 assert materials and materials.group(1)=="1,2"
 n0=len(re.findall(r"(?m)^T0(?=\s|$)",gc))
 n1=len(re.findall(r"(?m)^T1(?=\s|$)",gc))
 assert n0>0 and n1>0
 assert "CONFIG_BLOCK_END" in gc and "EXECUTABLE_BLOCK_END" in gc
 plate=json.loads(z.read("Metadata/plate_1.json"))
 bounds=plate.get("bbox_all")
 assert bounds and 0<=min(bounds) and bounds[2]<=256 and bounds[3]<=256
 summary=[
 "Bambu Studio P2S FINAL FILE / automated slice verification",
 f"Source: {SRC}",
 f"Bytes: {SRC.stat().st_size}",
 f"SHA256: {hashlib.sha256(SRC.read_bytes()).hexdigest()}",
 f"Build objects: {len(build)}",
 "Component meshes: 7",
 "Printer: "+proj["printer_model"]+" 0.4 mm",
 "Material slots 1/2: PETG, PETG",
 "PETG density slots 1/2: "+str(proj["filament_density"][:2]),
 "Textured PEI bed temperature slots 1/2: "+str(proj["textured_plate_temp"][:2]),
 "Filament colours: "+str(proj["filament_colour"][:2]),
 f"G-code bytes: {len(gc.encode())}",
 "G-code distinct filament numbers: "+materials.group(1),
 f"Tool commands T0: {n0}, T1: {n1}",
 "G-code layers: "+str(re.findall(r"(?m)^; total layer number: .*",gc)[:1]),
 "Slicer plate bounds: "+str(bounds),
 "Slicing success: output from Bambu Studio with embedded plate_1.gcode",
 "WARNING: physical fit, print, supports and surface quality still require real P2S test"
 ]
 TARGET.write_bytes(SRC.read_bytes())
 REPORT.write_text("\n".join(summary)+"\n",encoding="utf8")
 print("\n".join(summary))
