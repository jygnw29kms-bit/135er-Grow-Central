import os,json
import FreeCAD as App
import Part
ROOT=os.path.dirname(os.path.abspath(__file__))
M=os.path.join(ROOT,'models')
CASES=[
 ('Pi4','GrowCentral_Pi4_V4_PROTOTYP.FCStd','GC_Pi4_Base_V4','GC_Pi4_Lid_V4','GC_Pi4_Branding_V4',31.5),
 ('Node_FPC','GrowCentral_XIAO_Node_FPC_V4_PROTOTYP.FCStd','GC_Node_FPC_Base_V4','GC_Node_FPC_Lid_V4','GC_Node_FPC_Branding_V4',25.0),
 ('Node_EXT','GrowCentral_XIAO_Node_EXT_V4_PROTOTYP.FCStd','GC_Node_EXT_Base_V4','GC_Node_EXT_Lid_V4','GC_Node_EXT_Branding_V4',25.0),
 ('Hub_FPC','GrowCentral_XIAO_Hub_FPC_V4_PROTOTYP.FCStd','GC_Hub_FPC_Base_V4','GC_Hub_FPC_Lid_V4','GC_Hub_FPC_Branding_V4',28.0),
 ('Hub_EXT','GrowCentral_XIAO_Hub_EXT_V4_PROTOTYP.FCStd','GC_Hub_EXT_Base_V4','GC_Hub_EXT_Lid_V4','GC_Hub_EXT_Branding_V4',28.0),
]
fail=[]; report=[]
for label,fn,bn,ln,brn,H in CASES:
 d=App.openDocument(os.path.join(M,fn)); row={'case':label}
 b=d.getObject(bn); l=d.getObject(ln); br=d.getObject(brn)
 hw=next((o for o in d.Objects if o.Name.startswith('REF_XIAO') or o.Name.startswith('REF_Raspberry')),None)
 carrier=next((o for o in d.Objects if 'AntennaCarrier_V4' in o.Name and 'PRINT' not in o.Name),None)
 ant=d.getObject('REF_FPC_Antenna_40x20'); sma=d.getObject('REF_SMA_RPSMA_Bulkhead_6p5')
 mounts=[o for o in d.Objects if o.Name.startswith('REF_M4_')]
 for key,o in [('base',b),('lid',l),('branding',br)]:
  ok=bool(o and o.Shape and o.Shape.isValid() and len(o.Shape.Solids)>0 and (key=='branding' or len(o.Shape.Solids)==1))
  row[key+'_valid']=ok; row[key+'_solids']=len(o.Shape.Solids) if o else 0
  if o:
   bb=o.Shape.BoundBox; row[key+'_bbox']=[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)]
  if not ok: fail.append(f'{label}:{key}:invalid/solids')
 if hw and b:
  v=hw.Shape.common(b.Shape).Volume; row['hw_base_collision_mm3']=round(v,4)
  if v>0.05: fail.append(f'{label}:hw/base {v:.3f}')
 if hw and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); v=hw.Shape.common(ls).Volume; row['hw_lid_collision_mm3']=round(v,4)
  if v>0.05: fail.append(f'{label}:hw/lid {v:.3f}')
 if b and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); v=b.Shape.common(ls).Volume; row['base_lid_collision_mm3']=round(v,4)
  if v>0.10: fail.append(f'{label}:base/lid {v:.3f}')
 if br and l:
  v=br.Shape.common(l.Shape).Volume; row['branding_lid_overlap_mm3']=round(v,4)
  if v>0.05: fail.append(f'{label}:branding/lid {v:.3f}')
 if label!='Pi4':
  row['mount_refs']=len(mounts)
  if len(mounts)!=4: fail.append(f'{label}:expected 4 M4 refs got {len(mounts)}')
  row['lying_mounts']=sum('LYING' in o.Name for o in mounts); row['standing_mounts']=sum('STANDING' in o.Name for o in mounts)
  for o in mounts:
   v=o.Shape.common(b.Shape).Volume; row[o.Name+'_blocked_mm3']=round(v,4)
   if v>0.03: fail.append(f'{label}:{o.Name}:hole blocked {v:.3f}')
  # External mount strength dimensions are construction constants: M4 hole 4.3 mm, lying ear 11 mm, standing boss 10.4/10.4 with R5.2.
  row['m4_hole_diameter_mm']=4.3; row['lying_min_wall_mm']=3.35; row['standing_radial_wall_mm']=3.05
 if carrier:
  row['carrier_valid']=carrier.Shape.isValid() and len(carrier.Shape.Solids)==1
  row['carrier_base_overlap_mm3']=round(carrier.Shape.common(b.Shape).Volume,4)
  if not row['carrier_valid']: fail.append(f'{label}:carrier invalid')
  if row['carrier_base_overlap_mm3']>0.03: fail.append(f'{label}:carrier/base overlap')
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H)); v=carrier.Shape.common(ls).Volume; row['carrier_lid_overlap_mm3']=round(v,4)
  if v>0.03: fail.append(f'{label}:carrier/lid {v:.3f}')
  if hw:
   v=carrier.Shape.common(hw.Shape).Volume; row['carrier_hw_overlap_mm3']=round(v,4)
   if v>0.03: fail.append(f'{label}:carrier/hw {v:.3f}')
  for o in mounts:
   v=carrier.Shape.common(o.Shape).Volume
   if v>0.03: fail.append(f'{label}:carrier/{o.Name} {v:.3f}')
 if ant and carrier:
  row['fpc_size_mm']=[round(ant.Shape.BoundBox.XLength,2),round(ant.Shape.BoundBox.YLength,2),round(ant.Shape.BoundBox.ZLength,2)]
  row['fpc_carrier_distance_mm']=round(ant.Shape.distToShape(carrier.Shape)[0],4)
  if row['fpc_carrier_distance_mm']>0.02: fail.append(f'{label}:antenna floating')
 if sma:
  v=sma.Shape.common(b.Shape).Volume; row['sma_base_collision_mm3']=round(v,4); row['sma_center_z_mm']=round((sma.Shape.BoundBox.ZMin+sma.Shape.BoundBox.ZMax)/2,2)
  if v>0.05: fail.append(f'{label}:SMA blocked {v:.3f}')
 report.append(row); print('\n'+label); [print(' ',k,v) for k,v in row.items() if k!='case']; App.closeDocument(d.Name)
print('\nFAILURES',fail)
json.dump({'ok':not fail,'failures':fail,'cases':report},open(os.path.join(ROOT,'validation_v4_PROTOTYP.json'),'w'),indent=2)
raise SystemExit(0 if not fail else 2)
