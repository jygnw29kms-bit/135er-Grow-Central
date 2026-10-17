import os, sys, math
import os,sys,math
import FreeCAD as App
import Part

HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
import geometry_core_PROTOTYP as b
from brand_helpers_PROTOTYP import text_solid

OUT=os.path.join(HERE,'models')
REF=os.path.join(HERE,'references')
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

def add_dual_orientation_mounts(doc,base,W,D,H):
    # Two robust M4 points for horizontal/base-down installation.
    # Two additional M4 points on the left side for upright/side-to-wall installation.
    # Antenna interfaces remain on the rear face, so neither mounting mode blocks RF hardware.
    m4_r=2.15
    mount_ys=(8.0,D-8.0)
    # Lying: broad floor ears, vertical screw axis.
    for i,y in enumerate(mount_ys,1):
        ear=rr(11.0,11.0,4.0,3.2,0.0); ear.translate(App.Vector(-7.5,y-5.5,0))
        hole=Part.makeCylinder(m4_r,6.0,App.Vector(-2.0,y,-1.0),App.Vector(0,0,1))
        base=base.fuse(ear).cut(hole)
        ref=Part.makeCylinder(m4_r,6.0,App.Vector(-2.0,y,-1.0),App.Vector(0,0,1))
        add(doc,f'REF_M4_LYING_{i}',ref,(0.72,0.72,0.72),70)
    # Standing: chunky side bosses, horizontal screw axis.
    zc=H*0.52
    for i,y in enumerate(mount_ys,1):
        boss=Part.makeCylinder(5.2,6.5,App.Vector(-5.0,y,zc),App.Vector(1,0,0))
        web=Part.makeBox(5.4,10.4,10.4,App.Vector(-4.6,y-5.2,zc-5.2))
        hole=Part.makeCylinder(m4_r,9.0,App.Vector(-6.0,y,zc),App.Vector(1,0,0))
        base=base.fuse(web).fuse(boss).cut(hole)
        ref=Part.makeCylinder(m4_r,9.0,App.Vector(-6.0,y,zc),App.Vector(1,0,0))
        add(doc,f'REF_M4_STANDING_{i}',ref,(0.72,0.72,0.72),70)
    return base

def make_pi4():
    doc=App.newDocument('GrowCentral_Pi4_V4_PROTOTYP')
    hw=Part.read(os.path.join(REF,'RaspberryPi4_PartCAD_rpi4b_PROTOTYP.step'))
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
    bo=add(doc,'GC_Pi4_Base_V4',base); lo=add(doc,'GC_Pi4_Lid_V4',lid); br=add(doc,'GC_Pi4_Branding_V4',brand,GREEN)
    export(bo,'GrowCentral_Pi4_Base_V4_PROTOTYP'); export(lo,'GrowCentral_Pi4_Lid_V4_PROTOTYP'); export(br,'GrowCentral_Pi4_Branding_V4_PROTOTYP')
    doc.recompute(); doc.saveAs(os.path.join(OUT,'GrowCentral_Pi4_V4_PROTOTYP.FCStd')); App.closeDocument(doc.Name)

def xiao_hw():
    hw=b.xiao_reference(True); hw.translate(App.Vector(8.0,7.0,7.0)); return hw

def add_fpc_base_system(doc,base,W,D,H):
    # Robust removable rear antenna carrier for the supplied 40 x 20 mm adhesive FPC antenna.
    # The lid stays completely independent so servicing the enclosure never loads the U.FL lead.
    # Carrier is a separate printable part that slides/clips onto two chunky rear-wall rails.
    plate_w,plate_h,plate_t=44.0,24.0,2.6
    px=(W-plate_w)/2.0
    py=D+5.0
    pz=max(0.6,(H-plate_h)/2.0)

    # Full, uninterrupted adhesive face. The 40 x 20 antenna centres with a robust 2 mm border.
    carrier=Part.makeBox(plate_w,plate_t,plate_h,App.Vector(px,py,pz))

    # Twin broad T-rails on the base. They are intentionally overbuilt for FDM, not springy jewelry.
    rail_z=pz+4.0
    rail_h=plate_h-8.0
    rail_centres=(W/2.0-12.0,W/2.0+12.0)
    for cx in rail_centres:
        stem=Part.makeBox(4.8,2.0,rail_h,App.Vector(cx-2.4,D-0.2,rail_z))
        head=Part.makeBox(8.2,2.0,rail_h,App.Vector(cx-4.1,D+1.6,rail_z))
        # Lower lead-in and top stop give a positive push-on / slide-on feel without thin flexures.
        base=base.fuse(stem).fuse(head)

        outer=Part.makeBox(10.0,4.6,rail_h+1.4,App.Vector(cx-5.0,D+0.9,rail_z-0.7))
        cavity=Part.makeBox(8.7,3.80,rail_h+0.8,App.Vector(cx-4.35,D+0.55,rail_z-0.8))
        clip=outer.cut(cavity)
        # Back wall of clip overlaps the carrier plate and makes one stout body.
        carrier=carrier.fuse(clip)

    # Cable entry for the U.FL pigtail: enough for the tiny connector, with rounded stress relief.
    # Positioned off-centre so it does not clash with the XIAO or the two mounting rails.
    cable_x=11.0 if W>55 else W/2.0
    cable_z=H/2.0
    cable_cut=Part.makeCylinder(2.7,6.0,App.Vector(cable_x,D-2.5,cable_z),App.Vector(0,1,0))
    base=base.cut(cable_cut)

    # Broad inside strain-relief bridge, sized for ~1.13 mm coax with generous hand-assembly clearance.
    bridge=Part.makeBox(10.0,4.2,2.8,App.Vector(cable_x-5.0,D-5.6,cable_z-1.4))
    tunnel=Part.makeBox(6.0,4.5,1.8,App.Vector(cable_x-3.0,D-5.8,cable_z-0.9))
    base=base.fuse(bridge.cut(tunnel))

    # Reference antenna is placed exactly on the adhesive face of the removable carrier.
    ant=Part.makeBox(40.0,0.35,20.0,App.Vector(px+2.0,py+plate_t,pz+2.0))
    add(doc,'REF_FPC_Antenna_40x20',ant,(0.85,0.45,0.08),65)
    return base,carrier

def add_sma_bulkhead(doc,base,W,D,wall,H):
    # Rear-wall horizontal SMA/RP-SMA bulkhead, 6.5 mm through-hole, reinforced flat seat.
    cx=W/2; cz=H/2.0
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
    doc=App.newDocument('GrowCentral_'+tag+'_V4_PROTOTYP')
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
    base=add_dual_orientation_mounts(doc,base,W,D,H)
    carrier=None
    if mode=='EXT': base=add_sma_bulkhead(doc,base,W,D,wall,H)
    elif mode=='FPC': base,carrier=add_fpc_base_system(doc,base,W,D,H)
    lid=rr(W,D,2.8,rad,0); tongue=rr(W-2*(wall+0.3),D-2*(wall+0.3),2.8,max(1.0,rad-wall-0.3),-2.6); tongue.translate(App.Vector(wall+0.3,wall+0.3,0)); lid=lid.fuse(tongue)
    if mode=='FPC':
        vent_xs=(9,18,27) if not hub else (9,19,29,39,49)
        for vx in vent_xs:
            lid=slot(lid,vx,2.2,-2.9,5.8,2.6,6,1.3); lid=slot(lid,vx,D-4.8,-2.9,5.8,2.6,6,1.3)
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
    base_name=f'GrowCentral_XIAO_{kind}_{mode}_Base_V4_PROTOTYP'; lid_name=f'GrowCentral_XIAO_{kind}_{mode}_Lid_V4_PROTOTYP'; brand_name=f'GrowCentral_XIAO_{kind}_{mode}_Branding_V4_PROTOTYP'
    bo=add(doc,'GC_'+tag+'_Base_V4',base); lo=add(doc,'GC_'+tag+'_Lid_V4',lid); br=add(doc,'GC_'+tag+'_Branding_V4',brand,GREEN)
    export(bo,base_name); export(lo,lid_name); export(br,brand_name)
    if mode=='FPC' and carrier is not None:
        co=add(doc,'GC_'+tag+'_AntennaCarrier_V4',carrier,(0.12,0.14,0.16),0)
        export(co,f'GrowCentral_XIAO_{kind}_{mode}_AntennaCarrier_V4_PROTOTYP')
        # Print copy: rotate so the completely flat adhesive face sits on the build plate,
        # while the chunky clip geometry grows upward without support.
        cps=carrier.copy(); cps.rotate(App.Vector(0,0,0),App.Vector(1,0,0),-90)
        bb=cps.BoundBox; cps.translate(App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
        cpo=add(doc,'GC_'+tag+'_AntennaCarrier_PRINT_V4',cps,(0.12,0.14,0.16),0)
        export(cpo,f'GrowCentral_XIAO_{kind}_{mode}_AntennaCarrier_PRINT_V4_PROTOTYP')
        doc.removeObject(cpo.Name)
    doc.recompute(); doc.saveAs(os.path.join(OUT,f'GrowCentral_XIAO_{kind}_{mode}_V4_PROTOTYP.FCStd')); App.closeDocument(doc.Name)

if __name__=='__main__':
    make_pi4()
    for k in ('Node','Hub'):
        for m in ('FPC','EXT'): make_xiao(k,m)
    print('V4 PROTOTYP generated',OUT)



