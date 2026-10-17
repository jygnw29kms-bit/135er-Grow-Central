import os
import FreeCAD as App
root=os.path.join(os.path.dirname(__file__),'models')
for fn in ['GrowCentral_Pi4_V2.FCStd','GrowCentral_XIAO_Node_V2.FCStd','GrowCentral_XIAO_Hub_V2.FCStd']:
    doc=App.openDocument(os.path.join(root,fn))
    objs=[o for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull()]
    ref=next(o for o in objs if o.Name.startswith('REF_'))
    base=next(o for o in objs if '_Base_' in o.Name)
    c=ref.Shape.common(base.Shape)
    print('\n',fn,'total',c.Volume)
    for i,s in enumerate(c.Solids):
        bb=s.BoundBox
        print(i,'vol',round(s.Volume,4),'bbox',round(bb.XMin,3),round(bb.YMin,3),round(bb.ZMin,3),'->',round(bb.XMax,3),round(bb.YMax,3),round(bb.ZMax,3))
    App.closeDocument(doc.Name)
