import os, sys, json, zipfile, shutil, subprocess, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MODELS=ROOT/'models'; OUT=ROOT/'printplates'; OUT.mkdir(exist_ok=True)
ORCA=Path(r'C:\Program Files\OrcaSlicer\orca-slicer.exe')
P2S_REF=json.loads((ROOT/'p2s_project_settings_reference_PROTOTYP.json').read_text(encoding='utf-8'))
CASES={
 'Pi4':[
  'GrowCentral_Pi4_Base_V4_PROTOTYP.stl','GrowCentral_Pi4_Lid_V4_PROTOTYP.stl','GrowCentral_Pi4_Branding_V4_PROTOTYP.stl'],
 'Node_FPC':[
  'GrowCentral_XIAO_Node_FPC_Base_V4_PROTOTYP.stl','GrowCentral_XIAO_Node_FPC_Lid_V4_PROTOTYP.stl','GrowCentral_XIAO_Node_FPC_Branding_V4_PROTOTYP.stl','GrowCentral_XIAO_Node_FPC_AntennaCarrier_PRINT_V4_PROTOTYP.stl'],
 'Node_EXT':[
  'GrowCentral_XIAO_Node_EXT_Base_V4_PROTOTYP.stl','GrowCentral_XIAO_Node_EXT_Lid_V4_PROTOTYP.stl','GrowCentral_XIAO_Node_EXT_Branding_V4_PROTOTYP.stl'],
 'Hub_FPC':[
  'GrowCentral_XIAO_Hub_FPC_Base_V4_PROTOTYP.stl','GrowCentral_XIAO_Hub_FPC_Lid_V4_PROTOTYP.stl','GrowCentral_XIAO_Hub_FPC_Branding_V4_PROTOTYP.stl','GrowCentral_XIAO_Hub_FPC_AntennaCarrier_PRINT_V4_PROTOTYP.stl'],
 'Hub_EXT':[
  'GrowCentral_XIAO_Hub_EXT_Base_V4_PROTOTYP.stl','GrowCentral_XIAO_Hub_EXT_Lid_V4_PROTOTYP.stl','GrowCentral_XIAO_Hub_EXT_Branding_V4_PROTOTYP.stl'],
}
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('',NS)
q=lambda x:f'{{{NS}}}{x}'

def patch_project(d):
    # Use a project-settings snapshot from a Bambu Studio P2S 0.4 / 0.20 Standard project.
    d=dict(P2S_REF)
    d['printer_model']='Bambu Lab P2S'
    d['printer_variant']='0.4'
    d['printer_settings_id']='Bambu Lab P2S 0.4 nozzle'
    d['nozzle_diameter']=['0.4']
    d['default_print_profile']='0.20mm Standard @BBL P2S'
    d['print_settings_id']='0.20mm Standard @BBL P2S'
    d['print_compatible_printers']=['Bambu Lab P2S 0.4 nozzle']
    d['default_filament_profile']=['Bambu PLA Basic @BBL P2S']
    # Keep four material slots compatible with the native Bambu project schema; only 1/2 are used.
    old_ids=list(d.get('filament_settings_id',[]))
    while len(old_ids)<4: old_ids.append('Bambu PLA Basic @BBL P2S')
    old_ids[0]=old_ids[1]='Bambu PLA Basic @BBL P2S'
    d['filament_settings_id']=old_ids
    colors=list(d.get('filament_colour',[]))
    while len(colors)<4: colors.append('#FFFFFF')
    colors[0]='#111111'; colors[1]='#36C95F'; d['filament_colour']=colors
    types=list(d.get('filament_type',[]))
    while len(types)<4: types.append('PLA')
    types[0]=types[1]='PLA'; d['filament_type']=types
    d['default_filament_colour']=['#111111','#36C95F']
    d['curr_bed_type']='Textured PEI Plate'
    return d

def patch_3mf(path):
    with zipfile.ZipFile(path,'r') as zin:
        names=zin.namelist()
        model=ET.fromstring(zin.read('3D/3dmodel.model'))
        settings=ET.fromstring(zin.read('Metadata/model_settings.config'))
        project=json.loads(zin.read('Metadata/project_settings.config'))
        # map object id -> filename/name from model settings
        id_name={}
        for o in settings.findall('object'):
            name=''
            for md in o.findall('metadata'):
                if md.attrib.get('key')=='name': name=md.attrib.get('value','')
                if md.attrib.get('key')=='extruder':
                    md.attrib['value']='2' if 'Branding' in name else '1'
            # second pass because name can appear after extruder
            id_name[o.attrib.get('id')]=name
        for o in settings.findall('object'):
            name=id_name.get(o.attrib.get('id'),'')
            for md in o.findall('metadata'):
                if md.attrib.get('key')=='extruder': md.attrib['value']='2' if 'Branding' in name else '1'
        build=model.find(q('build'))
        items={x.attrib.get('objectid'):x for x in build.findall(q('item'))}
        lid_id=next((oid for oid,n in id_name.items() if '_Lid_' in n),None)
        brand_id=next((oid for oid,n in id_name.items() if '_Branding_' in n),None)
        if not lid_id or not brand_id: raise RuntimeError(f'missing lid/branding in {path.name}: {id_name}')
        # Brand STL shares CAD coordinate system with the lid. Same transform aligns it exactly.
        items[brand_id].attrib['transform']=items[lid_id].attrib['transform']
        items[brand_id].attrib['auto_drop']='0'
        project=patch_project(project)
        replacements={
            '3D/3dmodel.model':ET.tostring(model,encoding='utf-8',xml_declaration=True),
            'Metadata/model_settings.config':ET.tostring(settings,encoding='utf-8',xml_declaration=True),
            'Metadata/project_settings.config':json.dumps(project,ensure_ascii=False,indent=2).encode('utf-8'),
        }
        tmp=path.with_suffix('.tmp.3mf')
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            for info in zin.infolist():
                data=replacements.pop(info.filename,zin.read(info.filename))
                zout.writestr(info,data)
            for n,d in replacements.items(): zout.writestr(n,d)
    tmp.replace(path)

def validate(path):
    with zipfile.ZipFile(path) as z:
        m=ET.fromstring(z.read('3D/3dmodel.model'))
        s=ET.fromstring(z.read('Metadata/model_settings.config'))
        p=json.loads(z.read('Metadata/project_settings.config'))
        ids={o.attrib.get('id'):next((md.attrib.get('value','') for md in o.findall('metadata') if md.attrib.get('key')=='name'),'') for o in s.findall('object')}
        items={x.attrib.get('objectid'):x for x in m.find(q('build')).findall(q('item'))}
        lid=next(oid for oid,n in ids.items() if '_Lid_' in n); brand=next(oid for oid,n in ids.items() if '_Branding_' in n)
        assert items[lid].attrib.get('transform')==items[brand].attrib.get('transform')
        ex={o.attrib.get('id'):next((md.attrib.get('value') for md in o.findall('metadata') if md.attrib.get('key')=='extruder'),None) for o in s.findall('object')}
        assert ex[brand]=='2' and all(ex[i]=='1' for i,n in ids.items() if '_Branding_' not in n)
        assert p.get('printer_model')=='Bambu Lab P2S' and p.get('printer_variant')=='0.4'
        assert p.get('default_print_profile')=='0.20mm Standard @BBL P2S'
        assert p.get('filament_colour')[:2]==['#111111','#36C95F']
        return ids,items

def main():
    if not ORCA.exists(): raise SystemExit('OrcaSlicer missing')
    for case,files in CASES.items():
        dst=OUT/f'GrowCentral_{case}_P2S_V4_PROTOTYP.3mf'
        if dst.exists(): dst.unlink()
        cmd=[str(ORCA),'--export-3mf',str(dst)]+[str(MODELS/f) for f in files]
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        if not dst.exists(): raise RuntimeError(f'{case} export failed rc={r.returncode}: {r.stdout[-2000:]}')
        patch_3mf(dst)
        validate(dst)
        print('OK',case,dst.name,dst.stat().st_size)
    print('P2S V4 PROTOTYP complete')
if __name__=='__main__': main()
