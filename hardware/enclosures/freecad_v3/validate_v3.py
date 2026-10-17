import os, json, math
import FreeCAD as App
import Part

ROOT=os.path.dirname(os.path.abspath(__file__))
MODELS=os.path.join(ROOT,'models')
CASES=[
 ('Pi4','GrowCentral_Pi4_V3.FCStd','GC_Pi4_Base_V3','GC_Pi4_Lid_V3','GC_Pi4_Branding_V3',31.5),
 ('Node_FPC','GrowCentral_XIAO_Node_FPC_V3.FCStd','GC_Node_FPC_Base_V3','GC_Node_FPC_Lid_V3','GC_Node_FPC_Branding_V3',25.0),
 ('Node_EXT','GrowCentral_XIAO_Node_EXT_V3.FCStd','GC_Node_EXT_Base_V3','GC_Node_EXT_Lid_V3','GC_Node_EXT_Branding_V3',25.0),
 ('Hub_FPC','GrowCentral_XIAO_Hub_FPC_V3.FCStd','GC_Hub_FPC_Base_V3','GC_Hub_FPC_Lid_V3','GC_Hub_FPC_Branding_V3',28.0),
 ('Hub_EXT','GrowCentral_XIAO_Hub_EXT_V3.FCStd','GC_Hub_EXT_Base_V3','GC_Hub_EXT_Lid_V3','GC_Hub_EXT_Branding_V3',28.0),
]
fail=[]
report=[]
for label,fn,bn,ln,brn,H in CASES:
 d=App.openDocument(os.path.join(MODELS,fn))
 b=d.getObject(bn); l=d.getObject(ln); br=d.getObject(brn)
 hw=next((o for o in d.Objects if o.Name.startswith('REF_XIAO') or o.Name.startswith('REF_Raspberry')),None)
 ant=d.getObject('REF_FPC_Antenna_40x20')
 sma=d.getObject('REF_SMA_RPSMA_Bulkhead_6p5')
 row={'case':label}
 for key,o in [('base',b),('lid',l),('branding',br)]:
  ok=bool(o and o.Shape and o.Shape.isValid() and len(o.Shape.Solids)>0)
  row[key+'_valid']=ok
  if not ok: fail.append(f'{label}:{key}:invalid')
  if o:
   bb=o.Shape.BoundBox; row[key+'_bbox']=[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)]; row[key+'_solids']=len(o.Shape.Solids)
 if hw and b:
  c=hw.Shape.common(b.Shape); row['hw_base_collision_mm3']=round(c.Volume,4)
  if c.Volume>0.05: fail.append(f'{label}:hw/base {c.Volume:.3f}')
 if hw and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H))
  c=hw.Shape.common(ls); row['hw_lid_collision_mm3']=round(c.Volume,4)
  if c.Volume>0.05: fail.append(f'{label}:hw/lid {c.Volume:.3f}')
 if b and l:
  ls=l.Shape.copy(); ls.translate(App.Vector(0,0,H))
  c=b.Shape.common(ls); row['base_lid_collision_mm3']=round(c.Volume,4)
  # tongue contact should be zero-volume clearance, any significant volume means bad fit
  if c.Volume>0.10: fail.append(f'{label}:base/lid {c.Volume:.3f}')
 if br and l:
  c=br.Shape.common(l.Shape); row['branding_lid_overlap_mm3']=round(c.Volume,4)
  if c.Volume>0.05: fail.append(f'{label}:branding/lid overlap {c.Volume:.3f}')
  row['branding_z']=[round(br.Shape.BoundBox.ZMin,2),round(br.Shape.BoundBox.ZMax,2)]
 if ant:
  row['fpc_ref_bbox']=[round(ant.Shape.BoundBox.XLength,2),round(ant.Shape.BoundBox.YLength,2),round(ant.Shape.BoundBox.ZLength,2)]
  ls=l.Shape.copy(); c=ant.Shape.common(ls); row['fpc_lid_collision_mm3']=round(c.Volume,4)
  if c.Volume>0.02: fail.append(f'{label}:FPC/lid {c.Volume:.3f}')
 if sma:
  row['sma_ref_diameter_mm']=round(sma.Shape.BoundBox.XLength,2)
  c=sma.Shape.common(b.Shape); row['sma_base_collision_mm3']=round(c.Volume,4)
  if c.Volume>0.05: fail.append(f'{label}:SMA/base {c.Volume:.3f}')
 report.append(row)
 print('\n'+label)
 for k,v in row.items():
  if k!='case': print(' ',k,v)
 App.closeDocument(d.Name)
print('\nFAILURES',fail)
json.dump({'ok':not fail,'failures':fail,'cases':report},open(os.path.join(ROOT,'validation_v3.json'),'w'),indent=2)
raise SystemExit(0 if not fail else 2)
