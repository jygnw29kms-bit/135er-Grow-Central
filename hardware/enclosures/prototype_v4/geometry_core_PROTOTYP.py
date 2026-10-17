import os, math
import FreeCAD as App
import Part
ROOT=os.path.dirname(os.path.abspath(__file__))
REF=os.path.join(ROOT,'references'); OUT=os.path.join(ROOT,'models')
def _rr(w,d,h,r,z=0):
    r=min(r,max(0.1,w/2-0.05),max(0.1,d/2-0.05))
    s=Part.makeBox(max(0.1,w-2*r),d,h,App.Vector(r,0,z)).fuse(Part.makeBox(w,max(0.1,d-2*r),h,App.Vector(0,r,z)))
    for x,y in [(r,r),(w-r,r),(r,d-r),(w-r,d-r)]: s=s.fuse(Part.makeCylinder(r,h,App.Vector(x,y,z)))
    return s
def shell(w,d,h,r,wall,floor):
    outer=_rr(w,d,h,r,0); inner=_rr(w-2*wall,d-2*wall,h-floor+0.2,max(0.8,r-wall),floor); inner.translate(App.Vector(wall,wall,0)); return outer.cut(inner)
def add_obj(doc,name,shape,color=None,trans=0):
    o=doc.addObject('PartDesign::Feature',name); o.Shape=shape; o.Label=name
    if getattr(o,'ViewObject',None) is not None and color: o.ViewObject.ShapeColor=color; o.ViewObject.Transparency=trans
    return o
def export_obj(o,stem):
    os.makedirs(OUT,exist_ok=True); Part.export([o],os.path.join(OUT,stem+'.step')); o.Shape.exportStl(os.path.join(OUT,stem+'.stl'))
def gc_badge(cx,cy,z,h,scale=1.0):
    pts=[]
    for i in range(6):
        a=math.radians(30+60*i); pts.append(App.Vector(cx+7*scale*math.cos(a),cy+7*scale*math.sin(a),z))
    pts.append(pts[0]); outer=Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0,0,h))
    pts2=[]
    for i in range(6):
        a=math.radians(30+60*i); pts2.append(App.Vector(cx+5*scale*math.cos(a),cy+5*scale*math.sin(a),z))
    pts2.append(pts2[0]); inner=Part.Face(Part.makePolygon(pts2)).extrude(App.Vector(0,0,h))
    ring=outer.cut(inner); stem=Part.makeBox(1.3*scale,7*scale,h,App.Vector(cx-0.65*scale,cy-3*scale,z))
    leaf1=Part.makeCylinder(2.3*scale,h,App.Vector(cx-2.0*scale,cy+1.2*scale,z)).cut(Part.makeCylinder(1.2*scale,h,App.Vector(cx-1.3*scale,cy+1.2*scale,z)))
    leaf2=Part.makeCylinder(2.3*scale,h,App.Vector(cx+2.0*scale,cy+1.2*scale,z)).cut(Part.makeCylinder(1.2*scale,h,App.Vector(cx+1.3*scale,cy+1.2*scale,z)))
    return ring.fuse(stem).fuse(leaf1).fuse(leaf2)
def slot(shape,x,y,z,w,d,h,r=1.2):
    cutter=_rr(w,d,h,r,z); cutter.translate(App.Vector(x,y,0)); return shape.cut(cutter)
def xiao_reference(with_headers=True):
    hw=Part.read(os.path.join(REF,'XIAO_ESP32C3_hansrune_simple_PROTOTYP.step')); bb=hw.BoundBox; hw.translate(App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
    if with_headers:
        for side_x in (2.16,19.70):
            for i in range(7):
                y=1.25+i*2.54; hw=hw.fuse(Part.makeBox(0.64,0.64,11.5,App.Vector(side_x-0.32,y-0.32,-3.5)))
            hw=hw.fuse(Part.makeBox(2.5,17.0,2.5,App.Vector(side_x-1.25,0.4,-0.1)))
    return hw
