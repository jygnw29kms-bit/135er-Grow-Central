import os
import FreeCAD as App
root=os.path.join(os.path.dirname(__file__),'models')
files=['GrowCentral_Pi4_V2.FCStd','GrowCentral_XIAO_Node_V2.FCStd','GrowCentral_XIAO_Hub_V2.FCStd']
for fn in files:
    doc=App.openDocument(os.path.join(root,fn))
    print('\n'+fn)
    objs=[o for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull()]
    for o in objs:
        s=o.Shape; bb=s.BoundBox
        print(o.Name,'valid',s.isValid(),'solids',len(s.Solids),'vol',round(s.Volume,2),'bbox',round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2))
    ref=next((o for o in objs if o.Name.startswith('REF_')),None)
    base=next((o for o in objs if '_Base_' in o.Name),None)
    lid=next((o for o in objs if '_Lid_' in o.Name),None)
    if ref and base:
        c=ref.Shape.common(base.Shape)
        print('COLLISION ref/base volume',round(c.Volume,4),'solids',len(c.Solids))
    if ref and lid:
        c=ref.Shape.common(lid.Shape)
        print('COLLISION ref/lid volume',round(c.Volume,4),'solids',len(c.Solids))
    App.closeDocument(doc.Name)
