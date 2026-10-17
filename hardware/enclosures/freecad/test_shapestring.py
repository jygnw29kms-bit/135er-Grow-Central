import FreeCAD as App
import Draft, Part, os
font=r'C:\Windows\Fonts\arialbd.ttf'
doc=App.newDocument('T')
o=Draft.makeShapeString(String='GROW CENTRAL', FontFile=font, Size=6.0, Tracking=0)
doc.recompute()
print('shape null', o.Shape.isNull(), 'bbox', o.Shape.BoundBox.XLength, o.Shape.BoundBox.YLength)
ex=o.Shape.extrude(App.Vector(0,0,1.0))
print('extrude valid', ex.isValid(), 'solids', len(ex.Solids), 'vol', ex.Volume)
App.closeDocument(doc.Name)
