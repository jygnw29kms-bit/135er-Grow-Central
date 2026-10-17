import os
import FreeCAD as App
import Draft
FONT_CANDIDATES=[r'C:\Windows\Fonts\bahnschrift.ttf',r'C:\Windows\Fonts\arialbd.ttf']
FONT=next((p for p in FONT_CANDIDATES if os.path.exists(p)),FONT_CANDIDATES[-1])
def text_solid(doc,text,size,height,x,y,z,angle=0):
    obj=Draft.makeShapeString(String=text,FontFile=FONT,Size=size,Tracking=0)
    doc.recompute(); shp=obj.Shape.extrude(App.Vector(0,0,height)); doc.removeObject(obj.Name)
    if angle: shp.rotate(App.Vector(0,0,0),App.Vector(0,0,1),angle)
    shp.translate(App.Vector(x,y,z)); return shp
