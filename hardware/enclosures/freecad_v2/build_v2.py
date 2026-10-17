import os, math
import FreeCAD as App
import Part
from brand_helpers import text_solid, engrave_text

ROOT=os.path.dirname(os.path.abspath(__file__))
REF=os.path.join(ROOT,'references')
OUT=os.path.join(ROOT,'models')
os.makedirs(OUT,exist_ok=True)

def rr2d(w,d,r,z=0):
    x0=y0=0
    s=Part.makeBox(w-2*r,d,1,App.Vector(r,0,z)).fuse(Part.makeBox(w,d-2*r,1,App.Vector(0,r,z)))
    for x,y in [(r,r),(w-r,r),(r,d-r),(w-r,d-r)]:
        s=s.fuse(Part.makeCylinder(r,1,App.Vector(x,y,z)))
    return s

def rr_prism(w,d,h,r,z=0):
    face=rr2d(w,d,r,z)
    return face.common(Part.makeBox(w,d,1,App.Vector(0,0,z))).extrude(App.Vector(0,0,h)) if False else _rr(w,d,h,r,z)

def _rr(w,d,h,r,z=0):
    r=min(r, max(0.1,w/2-0.05), max(0.1,d/2-0.05))
    s=Part.makeBox(max(0.1,w-2*r),d,h,App.Vector(r,0,z)).fuse(Part.makeBox(w,max(0.1,d-2*r),h,App.Vector(0,r,z)))
    for x,y in [(r,r),(w-r,r),(r,d-r),(w-r,d-r)]:
        s=s.fuse(Part.makeCylinder(r,h,App.Vector(x,y,z)))
    return s

def shell(w,d,h,r,wall,floor):
    outer=_rr(w,d,h,r,0)
    inner=_rr(w-2*wall,d-2*wall,h-floor+0.2,max(0.8,r-wall),floor)
    inner.translate(App.Vector(wall,wall,0))
    return outer.cut(inner)

def add_obj(doc,name,shape,color=None,trans=0):
    o=doc.addObject('PartDesign::Feature',name); o.Shape=shape; o.Label=name
    if getattr(o,'ViewObject',None) is not None and color:
        o.ViewObject.ShapeColor=color; o.ViewObject.Transparency=trans
    return o

def export_obj(o,stem):
    Part.export([o],os.path.join(OUT,stem+'.step'))
    o.Shape.exportStl(os.path.join(OUT,stem+'.stl'))

def gc_badge(cx,cy,z,h,scale=1.0):
    # hex + leaf/stem family mark, intentionally printable at 0.4 mm nozzle
    pts=[]
    for i in range(6):
        a=math.radians(30+60*i); pts.append(App.Vector(cx+7*scale*math.cos(a),cy+7*scale*math.sin(a),z))
    pts.append(pts[0]); outer=Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0,0,h))
    pts2=[]
    for i in range(6):
        a=math.radians(30+60*i); pts2.append(App.Vector(cx+5*scale*math.cos(a),cy+5*scale*math.sin(a),z))
    pts2.append(pts2[0]); inner=Part.Face(Part.makePolygon(pts2)).extrude(App.Vector(0,0,h))
    ring=outer.cut(inner)
    stem=Part.makeBox(1.3*scale,7*scale,h,App.Vector(cx-0.65*scale,cy-3*scale,z))
    leaf1=Part.makeCylinder(2.3*scale,h,App.Vector(cx-2.0*scale,cy+1.2*scale,z)).cut(Part.makeCylinder(1.2*scale,h,App.Vector(cx-1.3*scale,cy+1.2*scale,z)))
    leaf2=Part.makeCylinder(2.3*scale,h,App.Vector(cx+2.0*scale,cy+1.2*scale,z)).cut(Part.makeCylinder(1.2*scale,h,App.Vector(cx+1.3*scale,cy+1.2*scale,z)))
    return ring.fuse(stem).fuse(leaf1).fuse(leaf2)

def slot(shape,x,y,z,w,d,h,r=1.2):
    cutter=_rr(w,d,h,r,z); cutter.translate(App.Vector(x,y,0)); return shape.cut(cutter)

def make_pi4():
    doc=App.newDocument('GrowCentral_Pi4_V2')
    hw=Part.read(os.path.join(REF,'RaspberryPi4_PartCAD_rpi4b.step'))
    # normalize reference to positive coords and lift PCB/connector assembly above floor
    bb=hw.BoundBox; hw.translate(App.Vector(-bb.XMin+6.5,-bb.YMin+6.0,-bb.ZMin+5.0))
    ref=add_obj(doc,'REF_RaspberryPi4_ModelB',hw,(0.15,0.55,0.20),65)
    W,D,H=101.0,70.0,31.5; wall=2.6; floor=2.8; rad=7.0
    base=shell(W,D,H,rad,wall,floor)
    # openings based on real reference envelope plus service margin
    # long I/O edge: USB-C, dual HDMI, audio
    base=slot(base,7.0,-1,5.0,62,wall+3,16,2.2)
    # USB + ethernet stack side
    base=slot(base,W-wall-2,10.0,5.5,wall+4,50,21,2.2)
    # SD card finger access
    base=slot(base,4.0,D-wall-2,0.3,23,wall+4,8,2.0)
    # rear crossflow vent bank
    for i in range(7): base=slot(base,34+i*8.2,D-wall-2,9.0,5.2,wall+4,15,2.0)
    # board standoffs from official 58 x 49 hole pattern, relative to PCB origin
    ox,oy=6.5,6.0
    for x,y in [(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]:
        boss=Part.makeCylinder(3.4,3.2,App.Vector(ox+x,oy+y,floor))
        hole=Part.makeCylinder(1.45,4.0,App.Vector(ox+x,oy+y,floor-0.2))
        base=base.fuse(boss.cut(hole))
    # integrated vertical/tent mounting rails, not floppy tabs
    for y in (13,48):
        rail=_rr(8,14,4,2.2,2.0); rail.translate(App.Vector(-5,y,0)); rail=rail.cut(Part.makeBox(4,8,7,App.Vector(-3,y+3,1)))
        base=base.fuse(rail)
    # lid with inset tongue, GPIO hatch, diagonal vent signature and badge
    lid=_rr(W,D,3.0,rad,0)
    tongue=_rr(W-2*(wall+0.35),D-2*(wall+0.35),3.0,max(1.0,rad-wall-0.35),-2.8); tongue.translate(App.Vector(wall+0.35,wall+0.35,0)); lid=lid.fuse(tongue)
    # full GPIO access window with 2 mm margin around 40-pin header zone
    lid=slot(lid,7.5,49.0,-3.0,58,12,7,2.2)
    # angled-ish repeated vents using staggered rows
    for r in range(3):
        for c in range(6):
            lid=slot(lid,17+c*11+(r%2)*3.0,15+r*8,-3.0,7.0,3.0,7,1.5)
    # recessed perimeter detail gives the lid a deliberate product-family surface
    groove_outer=_rr(W-10,D-10,0.45,max(2.0,rad-2.0),2.58); groove_outer.translate(App.Vector(5,5,0))
    groove_inner=_rr(W-15,D-15,0.55,max(1.5,rad-3.0),2.52); groove_inner.translate(App.Vector(7.5,7.5,0))
    lid=lid.cut(groove_outer.cut(groove_inner))
    lid=lid.fuse(gc_badge(82,51,3.0,1.2,1.0))
    lid=engrave_text(lid,text_solid(doc,'GROW CENTRAL',6.4,0.78,9,56.2,2.42))
    lid=engrave_text(lid,text_solid(doc,'PI4',4.2,0.72,11,50.7,2.42))
    # raised product family bar
    lid=lid.fuse(_rr(42,3.2,0.9,1.4,3.0).translated(App.Vector(8,7,0)) if False else Part.makeBox(42,3.2,0.9,App.Vector(8,7,3.0)))
    b=add_obj(doc,'GC_Pi4_Base_V2',base,(0.12,0.14,0.16),0); l=add_obj(doc,'GC_Pi4_Lid_V2',lid,(0.12,0.14,0.16),0)
    export_obj(b,'GrowCentral_Pi4_Base_V2'); export_obj(l,'GrowCentral_Pi4_Lid_V2')
    doc.recompute(); doc.saveAs(os.path.join(OUT,'GrowCentral_Pi4_V2.FCStd')); App.closeDocument(doc.Name)

def xiao_reference(with_headers=True):
    hw=Part.read(os.path.join(REF,'XIAO_ESP32C3_hansrune_simple.step'))
    bb=hw.BoundBox; hw.translate(App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
    if with_headers:
        # 2.54 mm pitch, 7 pins each side. Plastic body + pins above/below PCB.
        for side_x in (2.16,19.70):
            for i in range(7):
                y=1.25+i*2.54
                pin=Part.makeBox(0.64,0.64,11.5,App.Vector(side_x-0.32,y-0.32,-3.5))
                hw=hw.fuse(pin)
            body=Part.makeBox(2.5,17.0,2.5,App.Vector(side_x-1.25,0.4,-0.1))
            hw=hw.fuse(body)
    return hw

def make_xiao(kind):
    hub=kind=='Hub'; doc=App.newDocument('GrowCentral_XIAO_'+kind+'_V2')
    hw=xiao_reference(True); hw.translate(App.Vector(8.0,7.0,7.0))
    ref=add_obj(doc,'REF_XIAO_ESP32C3_With_Headers',hw,(0.15,0.45,0.75),60)
    if hub: W,D,H=66.0,48.0,28.0
    else: W,D,H=43.0,34.0,25.0
    wall=2.2; floor=2.6; rad=5.5
    base=shell(W,D,H,rad,wall,floor)
    # USB-C opening, aligned to board short edge and generously serviceable
    base=slot(base,7.0,-1,8.0,14.5,wall+3.0,9.5,2.2)
    # sensor cable exit on opposite side, radiused to avoid cable damage
    base=slot(base,W-wall-2,D-15,7.0,wall+4,11.0,10.0,2.5)
    if hub:
        base=slot(base,W-wall-2,7.0,7.0,wall+4,11.0,10.0,2.5)
        base=slot(base,26.0,D-wall-2,7.0,16.0,wall+4,10.0,2.5)
    # PCB guide rails deliberately outside the actual XIAO/header envelope.
    # Underside remains fully open for soldered 2.54 mm header pins.
    base=base.fuse(Part.makeBox(1.3,20.5,3.4,App.Vector(5.4,5.7,floor)))
    base=base.fuse(Part.makeBox(1.3,20.5,3.4,App.Vector(31.0,5.7,floor)))
    if hub:
        # integrated wiring shelf and tie-down bridges; connected to floor
        base=base.fuse(_rr(23,31,3.0,3.0,floor).translated(App.Vector(38,8,0)) if False else Part.makeBox(23,31,3.0,App.Vector(38,8,floor)))
        for yy in (12,29):
            bridge=Part.makeBox(18,3,4,App.Vector(40,yy,floor+3)); bridge=bridge.cut(Part.makeBox(12,1.5,5,App.Vector(43,yy+0.75,floor+2.5))); base=base.fuse(bridge)
    # rear integrated mounting spine with two zip-tie channels
    spine=_rr(7,22,5,2.2,1.5); spine.translate(App.Vector(-4,(D-22)/2,0)); spine=spine.cut(Part.makeBox(3.5,7,7,App.Vector(-2.5,(D-22)/2+3,1))); spine=spine.cut(Part.makeBox(3.5,7,7,App.Vector(-2.5,(D-22)/2+12,1))); base=base.fuse(spine)
    # lid
    lid=_rr(W,D,2.8,rad,0); tongue=_rr(W-2*(wall+0.3),D-2*(wall+0.3),2.8,max(1.0,rad-wall-0.3),-2.6); tongue.translate(App.Vector(wall+0.3,wall+0.3,0)); lid=lid.fuse(tongue)
    rows=2 if not hub else 3; cols=3 if not hub else 5
    for r in range(rows):
        for c in range(cols): lid=slot(lid,8+c*9+(r%2)*2,8+r*7,-2.9,5.8,2.6,6,1.3)
    # shallow inset perimeter motif shared with Pi enclosure
    go=_rr(W-8,D-8,0.42,max(1.8,rad-1.8),2.40); go.translate(App.Vector(4,4,0))
    gi=_rr(W-12,D-12,0.52,max(1.2,rad-2.8),2.35); gi.translate(App.Vector(6,6,0))
    lid=lid.cut(go.cut(gi))
    lid=lid.fuse(gc_badge(W-10,D-10,2.8,1.1,0.72 if hub else 0.62))
    title_size=4.2 if hub else 3.6
    lid=engrave_text(lid,text_solid(doc,'GC HUB' if hub else 'GC NODE',title_size,0.72,6,D-7.6,2.26))
    tag='HUB' if hub else 'NODE'
    lid=engrave_text(lid,text_solid(doc,tag,3.2 if hub else 2.8,0.68,7,4.8,2.26))
    b=add_obj(doc,'GC_XIAO_'+kind+'_Base_V2',base,(0.12,0.14,0.16),0); l=add_obj(doc,'GC_XIAO_'+kind+'_Lid_V2',lid,(0.12,0.14,0.16),0)
    export_obj(b,'GrowCentral_XIAO_'+kind+'_Base_V2'); export_obj(l,'GrowCentral_XIAO_'+kind+'_Lid_V2')
    doc.recompute(); doc.saveAs(os.path.join(OUT,'GrowCentral_XIAO_'+kind+'_V2.FCStd')); App.closeDocument(doc.Name)

if __name__=='__main__':
    make_pi4(); make_xiao('Node'); make_xiao('Hub'); print('V2 generated:',OUT)
