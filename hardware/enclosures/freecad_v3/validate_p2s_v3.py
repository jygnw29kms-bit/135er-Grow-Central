import json, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent; P=ROOT/'printplates'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'; q=lambda x:f'{{{NS}}}{x}'
rows=[]; fail=[]
for path in sorted(P.glob('*_P2S_V3.3mf')):
 with zipfile.ZipFile(path) as z:
  needed={'[Content_Types].xml','3D/3dmodel.model','Metadata/model_settings.config','Metadata/project_settings.config'}
  missing=needed-set(z.namelist())
  if missing: fail.append(f'{path.name}:missing {missing}'); continue
  m=ET.fromstring(z.read('3D/3dmodel.model')); s=ET.fromstring(z.read('Metadata/model_settings.config')); d=json.loads(z.read('Metadata/project_settings.config'))
  objs=s.findall('object'); names={o.attrib['id']:next((x.attrib.get('value','') for x in o.findall('metadata') if x.attrib.get('key')=='name'),'') for o in objs}
  ex={o.attrib['id']:next((x.attrib.get('value') for x in o.findall('metadata') if x.attrib.get('key')=='extruder'),None) for o in objs}
  items={x.attrib.get('objectid'):x for x in m.find(q('build')).findall(q('item'))}
  lid=next((i for i,n in names.items() if '_Lid_' in n),None); brand=next((i for i,n in names.items() if '_Branding_' in n),None)
  expected=4 if any('AntennaCarrier' in n for n in names.values()) else 3
  ok=(len(objs)==expected and lid and brand and ex.get(brand)=='2' and items[lid].attrib.get('transform')==items[brand].attrib.get('transform') and d.get('printer_model')=='Bambu Lab P2S' and d.get('printer_variant')=='0.4' and d.get('printer_settings_id')=='Bambu Lab P2S 0.4 nozzle' and d.get('print_settings_id')=='0.20mm Standard @BBL P2S' and d.get('printable_area')==['0x0','256x0','256x256','0x256'] and d.get('printable_height')=='256')
  row={'file':path.name,'ok':bool(ok),'size':path.stat().st_size,'printer':d.get('printer_settings_id'),'process':d.get('print_settings_id'),'objects':list(names.values()),'expected_objects':expected,'extruders':ex,'lid_brand_aligned':items[lid].attrib.get('transform')==items[brand].attrib.get('transform')}
  rows.append(row)
  if not ok: fail.append(path.name)
  print(('OK' if ok else 'FAIL'),path.name,d.get('printer_settings_id'),d.get('print_settings_id'),'objects',len(objs),'aligned',row['lid_brand_aligned'])
(ROOT/'p2s_validation_v3.json').write_text(json.dumps({'ok':not fail,'failures':fail,'plates':rows},indent=2),encoding='utf-8')
print('FAILURES',fail)
raise SystemExit(0 if not fail else 2)
