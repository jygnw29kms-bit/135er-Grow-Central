import os, glob
import FreeCAD as App
base=os.path.dirname(os.path.abspath(__file__))
for path in glob.glob(os.path.join(base,'*.FCStd')):
    doc=App.openDocument(path)
    print(os.path.basename(path))
    for o in doc.Objects:
        if hasattr(o,'Shape'):
            s=o.Shape
            bb=s.BoundBox
            print(' ',o.Name,'valid=',s.isValid(),'solids=',len(s.Solids),'volume=',round(s.Volume,2),'bbox=',round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2))
    App.closeDocument(doc.Name)
