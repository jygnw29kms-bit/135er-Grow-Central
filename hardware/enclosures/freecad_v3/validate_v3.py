import os, json
import FreeCAD as App

ROOT=os.path.dirname(os.path.abspath(__file__))
MODELS=os.path.join(ROOT,'models')
CASES=[
 ('Pi4','GrowCentral_Pi4_V3.FCStd','GC_Pi4_Base_V3','GC_Pi4_Lid_V3','GC_Pi4_Branding_V3',31.5,None),
 ('Node_FPC','GrowCentral_XIAO_Node_FPC_V3.FCStd','GC_Node_FPC_Base_V3','GC_Node_FPC_Lid_V3','GC_Node_FPC_Branding_V3',25.0,'GC_Node_FPC_AntennaCarrier_V3'),
 ('Node_EXT','GrowCentral_XIAO_Node_EXT_V3.FCStd','GC_Node_EXT_Base_V3','GC_Node_EXT_Lid_V3','GC_Node_EXT_Branding_V3',25.0,None),
 ('Hub_FPC','GrowCentral_XIAO_Hub_FPC_V3.FCStd','GC_Hub_FPC_Base_V3','GC_Hub_FPC_Lid_V3','GC_Hub_FPC_Branding_V3',28.0,'GC_Hub_FPC_AntennaCarrier_V3'),
 ('Hub_EXT','GrowCentral_XIAO_Hub_EXT_V3.FCStd','GC_Hub_EXT_Base_V3','GC_Hub_EXT_Lid_V3','GC_Hub_EXT_Branding_V3',28.0,None),
]
fail=[]; report=[]
for label,fn,bn,ln,brn,H,cn in CASES:
 d=App.openDocument(os.path.join(MODELS,fn))
 b=d.getObject(bn); l=d.getObject(ln); br=d.getObject(brn); car=d.getObject(cn) if cn else None
 hw=next((o for o in d.Objects if o.Name.startswith('REF_XIAO') or o.Name.startswith('REF_Raspberry')),None)
 ant=d.getObject('REF_FPC_Antenna_40x20'); sma=d.getObject('REF_SMA_RPSMA_Bulkhead_6p5')
 row={'case':label}
 for key,o in [('base',b),('lid',l),('branding',br)]+([('antenna_carrier',car)] if car else []):
  ok=bool(o and o.Shape and o.Shape.isValid() and len(o.Shape.Solids)>0 and (key=='branding' or len(o.Shape.Solids)==1))
  row[key+'_valid']=ok
  if not ok: fail.append(f'{label}:{key}:invalid')
  if o:
   bb=o.Shape.BoundBox; row[key+'_bbox']=[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)]; row[key+'_solids']=len(o.Shape.Solids)
 if hw and b:
  vol=hw.Shape.common(b.Shape).Volume; row['hw_base_collision_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:hw/base {vol:.3f}')
 if hw and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); vol=hw.Shape.common(ls).Volume; row['hw_lid_collision_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:hw/lid {vol:.3f}')
 if b and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); vol=b.Shape.common(ls).Volume; row['base_lid_collision_mm3']=round(vol,4)
  if vol>0.10: fail.append(f'{label}:base/lid {vol:.3f}')
 if br and l:
  vol=br.Shape.common(l.Shape).Volume; row['branding_lid_overlap_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:branding/lid {vol:.3f}')
  row['branding_z']=[round(br.Shape.BoundBox.ZMin,2),round(br.Shape.BoundBox.ZMax,2)]
 if car:
  vol=b.Shape.common(car.Shape).Volume; row['base_carrier_overlap_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:base/carrier {vol:.3f}')
  dist=b.Shape.distToShape(car.Shape)[0]; row['base_carrier_min_distance_mm']=round(dist,4)
  if dist>0.05: fail.append(f'{label}:carrier not retained/contacting stop {dist:.3f}')
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); vol=car.Shape.common(ls).Volume; row['carrier_lid_overlap_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:carrier/lid {vol:.3f}')
  if hw:
   vol=car.Shape.common(hw.Shape).Volume; row['carrier_hw_overlap_mm3']=round(vol,4)
   if vol>0.05: fail.append(f'{label}:carrier/hw {vol:.3f}')
 if ant:
  ab=ant.Shape.BoundBox; row['fpc_ref_bbox']=[round(ab.XLength,2),round(ab.YLength,2),round(ab.ZLength,2)]
  if car:
   vol=ant.Shape.common(car.Shape).Volume; row['fpc_carrier_overlap_mm3']=round(vol,4)
   dist=ant.Shape.distToShape(car.Shape)[0]; row['fpc_carrier_distance_mm']=round(dist,4)
   cb=car.Shape.BoundBox
   margins=[ab.XMin-cb.XMin,cb.XMax-ab.XMax,ab.ZMin-cb.ZMin,cb.ZMax-ab.ZMax]
   row['fpc_protected_margins_mm']=[round(x,2) for x in margins]
   if vol>0.02 or dist>0.02: fail.append(f'{label}:FPC seating invalid')
   if min(margins)<1.9: fail.append(f'{label}:FPC edge protection too small {min(margins):.2f}')
 if sma:
  row['sma_ref_diameter_mm']=round(sma.Shape.BoundBox.XLength,2)
  vol=sma.Shape.common(b.Shape).Volume; row['sma_base_collision_mm3']=round(vol,4)
  if vol>0.05: fail.append(f'{label}:SMA/base {vol:.3f}')
 report.append(row)
 print('\n'+label)
 for k,v in row.items():
  if k!='case': print(' ',k,v)
 App.closeDocument(d.Name)
print('\nFAILURES',fail)
json.dump({'ok':not fail,'failures':fail,'cases':report},open(os.path.join(ROOT,'validation_v3.json'),'w'),indent=2)
raise SystemExit(0 if not fail else 2)
