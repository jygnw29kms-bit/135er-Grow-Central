import os, sys, math
import FreeCAD as App
import Part

HERE=os.path.dirname(os.path.abspath(__file__))
V2=os.path.abspath(os.path.join(HERE,'..','freecad_v2'))
sys.path.insert(0,V2)
import build_v2 as b
from brand_helpers import text_solid

OUT=os.path.join(HERE,'models')
REF=os.path.join(V2,'references')
os.makedirs(OUT,exist_ok=True)
b.OUT=OUT; b.REF=REF

BLACK=(0.10,0.12,0.14); GREEN=(0.18,0.78,0.24)

def add(doc,name,shape,color=BLACK,trans=0): return b.add_obj(doc,name,shape,color,trans)
def export(o,stem): return b.export_obj(o,stem)
def rr(w,d,h,r,z=0): return b._rr(w,d,h,r,z)
def slot(shape,x,y,z,w,d,h,r=1.2): return b.slot(shape,x,y,z,w,d,h,r)
def shell(w,d,h,r,wall,floor): return b.shell(w,d,h,r,wall,floor)
def badge(cx,cy,z,h,scale=1.0): return b.gc_badge(cx,cy,z,h,scale)

def add_family_surface(lid,W,D,rad,z_top):
    # double inset frame + restrained raised corner bars, common visual language
    go=rr(W-8,D-8,0.38,max(1.7,rad-1.8),z_top-0.42); go.translate(App.Vector(4,4,0))
    gi=rr(W-12,D-12,0.48,max(1.1,rad-2.8),z_top-0.48); gi.translate(App.Vector(6,6,0))
    lid=lid.cut(go.cut(gi))
    return lid

def make_pi4():
    doc=App.newDocument('GrowCentral_Pi4_V3')
    hw=Part.read(os.path.join(REF,'RaspberryPi4_PartCAD_rpi4b.step'))
    bb=hw.BoundBox; hw.translate(App.Vector(-bb.XMin+6.5,-bb.YMin+6.0,-bb.ZMin+5.0))
    add(doc,'REF_RaspberryPi4_ModelB',hw,(0.15,0.55,0.20),65)
    W,D,H=101.0,70.0,31.5; wall=2.6; floor=2.8; rad=7.0
    base=shell(W,D,H,rad,wall,floor)
    base=slot(base,7.0,-1,5.0,62,wall+3,16,2.2)
    base=slot(base,W-wall-2,10.0,5.5,wall+4,50,21,2.2)
    base=slot(base,4.0,D-wall-2,0.3,23,wall+4,8,2.0)
    for i in range(7): base=slot(base,34+i*8.2,D-wall-2,9.0,5.2,wall+4,15,2.0)
    ox,oy=6.5,6.0
    for x,y in [(3.5,3.5),(61.5,3.5),(3.5,52.5),(61.5,52.5)]:
        boss=Part.makeCylinder(3.4,3.2,App.Vector(ox+x,oy+y,floor))
        hole=Part.makeCylinder(1.45,4.0,App.Vector(ox+x,oy+y,floor-0.2))
        base=base.fuse(boss.cut(hole))
    for y in (13,48):
        rail=rr(8,14,4,2.2,2.0); rail.translate(App.Vector(-5,y,0)); rail=rail.cut(Part.makeBox(4,8,7,App.Vector(-3,y+3,1))); base=base.fuse(rail)
    lid=rr(W,D,3.0,rad,0)
    tongue=rr(W-2*(wall+0.35),D-2*(wall+0.35),3.0,max(1.0,rad-wall-0.35),-2.8); tongue.translate(App.Vector(wall+0.35,wall+0.35,0)); lid=lid.fuse(tongue)
    lid=slot(lid,7.5,49.0,-3.0,58,12,7,2.2)
    for r in range(3):
        for c in range(6): lid=slot(lid,17+c*11+(r%2)*3.0,15+r*8,-3.0,7.0,3.0,7,1.5)
    lid=add_family_surface(lid,W,D,rad,3.0)
    brand=badge(84,41,3.0,0.90,0.95)
    brand=brand.fuse(text_solid(doc,'GROW CENTRAL',6.4,0.90,8.5,40.0,3.0))
    brand=brand.fuse(text_solid(doc,'PI4',4.4,0.90,10.0,34.0,3.0))
    bo=add(doc,'GC_Pi4_Base_V3',base); lo=add(doc,'GC_Pi4_Lid_V3',lid); br=add(doc,'GC_Pi4_Branding_V3',brand,GREEN)
    export(bo,'GrowCentral_Pi4_Base_V3'); export(lo,'GrowCentral_Pi4_Lid_V3'); export(br,'GrowCentral_Pi4_Branding_V3')
    doc.recompute(); doc.saveAs(os.path.join(OUT,'GrowCentral_Pi4_V3.FCStd')); App.closeDocument(doc.Name)

def xiao_hw():
    hw=b.xiao_reference(True); hw.translate(App.Vector(8.0,7.0,7.0)); return hw

def add_fpc_mount(doc,lid,W,D):
    ant_w,ant_d=42.0,22.0; ant_x=(W-ant_w)/2; ant_y=(D-ant_d)/2
    carrier=Part.makeBox(ant_w,ant_d,0.70,App.Vector(ant_x,ant_y,-3.25)); lid=lid.fuse(carrier)
    rail=0.60; rh=0.65; rz=-3.90
    rim=(Part.makeBox(ant_w,rail,rh,App.Vector(ant_x,ant_y,rz))
         .fuse(Part.makeBox(ant_w,rail,rh,App.Vector(ant_x,ant_y+ant_d-rail,rz)))
         .fuse(Part.makeBox(rail,ant_d-2*rail,rh,App.Vector(ant_x,ant_y+rail,rz)))
         .fuse(Part.makeBox(rail,ant_d-2*rail,rh,App.Vector(ant_x+ant_w-rail,ant_y+rail,rz))))
    notch=Part.makeBox(rail+0.5,2.4,rh+0.3,App.Vector(ant_x+ant_w-rail-0.25,ant_y+ant_d/2-1.2,rz-0.1))
    lid=lid.fuse(rim.cut(notch))
    clip_x=max(3.0,W-10.0); clip_y=3.2
    clip=Part.makeBox(6.0,3.0,1.3,App.Vector(clip_x,clip_y,-3.85)).cut(Part.makeBox(3.8,1.5,1.5,App.Vector(clip_x+1.1,clip_y+0.75,-3.95)))
    lid=lid.fuse(clip)
    ant=Part.makeBox(40,20,0.35,App.Vector(ant_x+1,ant_y+1,-3.60)); add(doc,'REF_FPC_Antenna_40x20',ant,(0.85,0.45,0.08),65)
    return lid

def add_sma_bulkhead(doc,base,W,D,wall,H):
    # Rear-wall horizontal SMA/RP-SMA bulkhead, 6.5 mm through-hole, reinforced flat seat.
    cx=W/2; cz=min(H-8.5,15.5)
    reinforce=Part.makeBox(15.0,3.2,13.0,App.Vector(cx-7.5,D-wall-2.4,cz-6.5))
    base=base.fuse(reinforce)
    hole=Part.makeCylinder(3.25,8.0,App.Vector(cx,D-5.0,cz),App.Vector(0,1,0))
    base=base.cut(hole)
    # generous internal nut / cable clearance without weakening the wall around the seat
    relief=Part.makeCylinder(6.3,2.4,App.Vector(cx,D-wall-2.5,cz),App.Vector(0,1,0))
    base=base.cut(relief)
    ref=Part.makeCylinder(3.0,11.0,App.Vector(cx,D-5.0,cz),App.Vector(0,1,0))
    add(doc,'REF_SMA_RPSMA_Bulkhead_6p5',ref,(0.82,0.72,0.28),65)
    return base

def make_xiao(kind,mode):
    hub=(kind=='Hub'); mode=mode.upper(); tag=f'{kind}_{mode}'
    doc=App.newDocument('GrowCentral_'+tag+'_V3')
    hw=xiao_hw(); add(doc,'REF_XIAO_ESP32C3_With_Headers',hw,(0.15,0.45,0.75),60)
    W,D,H=(66.0,48.0,28.0) if hub else ((48.0,34.0,25.0) if mode=='FPC' else (43.0,34.0,25.0))
    wall=2.2; floor=2.6; rad=5.5
    base=shell(W,D,H,rad,wall,floor)
    base=slot(base,7.0,-1,8.0,14.5,wall+3.0,9.5,2.2)
    base=slot(base,W-wall-2,D-15,7.0,wall+4,11.0,10.0,2.5)
    if hub:
        base=slot(base,W-wall-2,7.0,7.0,wall+4,11.0,10.0,2.5)
        base=slot(base,26.0,D-wall-2,7.0,16.0,wall+4,10.0,2.5)
    base=base.fuse(Part.makeBox(1.3,20.5,3.4,App.Vector(5.4,5.7,floor)))
    base=base.fuse(Part.makeBox(1.3,20.5,3.4,App.Vector(31.0,5.7,floor)))
    if hub:
        base=base.fuse(Part.makeBox(23,31,3.0,App.Vector(38,8,floor)))
        for yy in (12,29):
            bridge=Part.makeBox(18,3,4,App.Vector(40,yy,floor+3)).cut(Part.makeBox(12,1.5,5,App.Vector(43,yy+0.75,floor+2.5))); base=base.fuse(bridge)
    spine=rr(7,22,5,2.2,1.5); spine.translate(App.Vector(-4,(D-22)/2,0)); spine=spine.cut(Part.makeBox(3.5,7,7,App.Vector(-2.5,(D-22)/2+3,1))).cut(Part.makeBox(3.5,7,7,App.Vector(-2.5,(D-22)/2+12,1))); base=base.fuse(spine)
    if mode=='EXT': base=add_sma_bulkhead(doc,base,W,D,wall,H)
    lid=rr(W,D,2.8,rad,0); tongue=rr(W-2*(wall+0.3),D-2*(wall+0.3),2.8,max(1.0,rad-wall-0.3),-2.6); tongue.translate(App.Vector(wall+0.3,wall+0.3,0)); lid=lid.fuse(tongue)
    if mode=='FPC':
        vent_xs=(9,18,27) if not hub else (9,19,29,39,49)
        for vx in vent_xs:
            lid=slot(lid,vx,2.2,-2.9,5.8,2.6,6,1.3); lid=slot(lid,vx,D-4.8,-2.9,5.8,2.6,6,1.3)
        lid=add_fpc_mount(doc,lid,W,D)
    else:
        rows=2 if not hub else 3; cols=3 if not hub else 5
        for r in range(rows):
            for c in range(cols): lid=slot(lid,8+c*9+(r%2)*2,8+r*7,-2.9,5.8,2.6,6,1.3)
    lid=add_family_surface(lid,W,D,rad,2.8)
    brand=badge(W-10,D-10,2.8,0.90,0.72 if hub else 0.62)
    title=('GC HUB' if hub else 'GC NODE') + (' EXT' if mode=='EXT' else '')
    title_size=(3.7 if hub else 3.0) if mode=='EXT' else (4.2 if hub else 3.6)
    brand=brand.fuse(text_solid(doc,title,title_size,0.90,5.0,D-7.6,2.8))
    brand=brand.fuse(text_solid(doc,'HUB' if hub else 'NODE',3.2 if hub else 2.8,0.90,7,4.8,2.8))
    base_name=f'GrowCentral_XIAO_{kind}_{mode}_Base_V3'; lid_name=f'GrowCentral_XIAO_{kind}_{mode}_Lid_V3'; brand_name=f'GrowCentral_XIAO_{kind}_{mode}_Branding_V3'
    bo=add(doc,'GC_'+tag+'_Base_V3',base); lo=add(doc,'GC_'+tag+'_Lid_V3',lid); br=add(doc,'GC_'+tag+'_Branding_V3',brand,GREEN)
    export(bo,base_name); export(lo,lid_name); export(br,brand_name)
    doc.recompute(); doc.saveAs(os.path.join(OUT,f'GrowCentral_XIAO_{kind}_{mode}_V3.FCStd')); App.closeDocument(doc.Name)

if __name__=='__main__':
    make_pi4()
    for k in ('Node','Hub'):
        for m in ('FPC','EXT'): make_xiao(k,m)
    print('V3 generated',OUT)


