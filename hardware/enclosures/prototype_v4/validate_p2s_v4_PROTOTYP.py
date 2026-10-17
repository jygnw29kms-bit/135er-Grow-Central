import json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent; P=ROOT/'printplates'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'; q=lambda x:f'{{{NS}}}{x}'
rows=[]; fail=[]
for path in sorted(P.glob('*_P2S_V4_PROTOTYP.3mf')):
 with zipfile.ZipFile(path) as z:
  needed={'[Content_Types].xml','3D/3dmodel.model','Metadata/model_settings.config','Metadata/project_settings.config'}
  missing=needed-set(z.namelist())
  if missing: fail.append(f'{path.name}:missing {missing}'); continue
  m=ET.fromstring(z.read('3D/3dmodel.model')); s=ET.fromstring(z.read('Metadata/model_settings.config')); d=json.loads(z.read('Metadata/project_settings.config'))
  objs=s.findall('object'); names={o.attrib['id']:next((x.attrib.get('value','') for x in o.findall('metadata') if x.attrib.get('key')=='name'),'') for o in objs}
  ex={o.attrib['id']:next((x.attrib.get('value') for x in o.findall('metadata') if x.attrib.get('key')=='extruder'),None) for o in objs}
  items={x.attrib.get('objectid'):x for x in m.find(q('build')).findall(q('item'))}
  lid=next((i for i,n in names.items() if '_Lid_' in n),None); brand=next((i for i,n in names.items() if '_Branding_' in n),None)
  fpc='FPC' in path.name; expected=4 if fpc else 3
  cfg=(d.get('printer_model')=='Bambu Lab P2S' and d.get('printer_variant')=='0.4' and d.get('printer_settings_id')=='Bambu Lab P2S 0.4 nozzle' and d.get('print_settings_id')=='0.20mm Standard @BBL P2S' and d.get('printable_area')==['0x0','256x0','256x256','0x256'] and d.get('printable_height')=='256')
  aligned=bool(lid and brand and items[lid].attrib.get('transform')==items[brand].attrib.get('transform'))
  named=all('_V4_PROTOTYP' in n for n in names.values()) and not any('_V3_' in n for n in names.values())
  carrier_count=sum('AntennaCarrier_PRINT' in n for n in names.values())
  extr=bool(brand and ex.get(brand)=='2' and all(ex[i]=='1' for i,n in names.items() if '_Branding_' not in n))
  ok=(len(objs)==expected and cfg and aligned and named and extr and (carrier_count==1 if fpc else carrier_count==0))
  row={'file':path.name,'ok':ok,'objects':list(names.values()),'object_count':len(objs),'expected':expected,'carrier_count':carrier_count,'p2s_config':cfg,'lid_brand_aligned':aligned,'prototype_names':named,'extruders':ex}
  rows.append(row)
  if not ok: fail.append(path.name)
  print(('OK' if ok else 'FAIL'),path.name,'objects',len(objs),'carrier',carrier_count,'aligned',aligned,'cfg',cfg,'names',named)
(ROOT/'p2s_validation_v4_PROTOTYP.json').write_text(json.dumps({'ok':not fail,'failures':fail,'plates':rows},indent=2),encoding='utf-8')
print('FAILURES',fail)
raise SystemExit(0 if not fail else 2)
