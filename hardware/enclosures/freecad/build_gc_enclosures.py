import os, math
import FreeCAD as App
import Part

OUT = os.path.dirname(os.path.abspath(__file__))


def box(x,y,z,px=0,py=0,pz=0):
    return Part.makeBox(x,y,z,App.Vector(px,py,pz))

def hex_prism(cx,cy,r,z0,h):
    pts=[]
    for i in range(6):
        a=math.radians(30+60*i)
        pts.append(App.Vector(cx+r*math.cos(a),cy+r*math.sin(a),z0))
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0,0,h))

def gc_mark(cx,cy,z0,h,scale=1.0):
    outer=hex_prism(cx,cy,8*scale,z0,h)
    inner=hex_prism(cx,cy,5.7*scale,z0,h)
    ring=outer.cut(inner)
    stem=box(1.2*scale,8*scale,h,cx-0.6*scale,cy-4*scale,z0)
    leaf1=Part.makeCylinder(2.4*scale,h,App.Vector(cx-2.2*scale,cy+1.2*scale,z0)).cut(
          Part.makeCylinder(1.4*scale,h,App.Vector(cx-1.4*scale,cy+1.2*scale,z0)))
    leaf2=Part.makeCylinder(2.4*scale,h,App.Vector(cx+2.2*scale,cy+1.2*scale,z0)).cut(
          Part.makeCylinder(1.4*scale,h,App.Vector(cx+1.4*scale,cy+1.2*scale,z0)))
    return ring.fuse(stem).fuse(leaf1).fuse(leaf2)

def vent_slots(shape, x0,y0,z0, count, length, width, height, dx=0,dy=0):
    s=shape
    for i in range(count):
        x=x0+i*dx; y=y0+i*dy
        cut=box(length,width,height,x,y,z0)
        s=s.cut(cut)
    return s

def save_part(doc,name,shape,stem):
    obj=doc.addObject('PartDesign::Feature',name)
    obj.Shape=shape
    obj.Label=name
    stl=os.path.join(OUT,stem+'.stl')
    step=os.path.join(OUT,stem+'.step')
    Part.export([obj],step)
    obj.Shape.exportStl(stl)
    return obj

def pi4_case():
    doc=App.newDocument('GrowCentral_Pi4_Case')
    # Internal envelope sized around 85x56 mm Pi 4 board with connector clearance.
    W,D,H=94.0,66.0,32.0
    wall=2.4; floor=2.6
    outer=box(W,D,H)
    inner=box(W-2*wall,D-2*wall,H-floor+1,wall,wall,floor)
    base=outer.cut(inner)
    # front-side USB-C + dual micro-HDMI + audio/service opening
    base=base.cut(box(58,wall+2,15,10,-1,6))
    # USB/Ethernet bank
    base=base.cut(box(wall+2,47,19,W-wall-1,10,7))
    # SD access at rear underside
    base=base.cut(box(18,wall+2,6,6,D-wall-1,0))
    # vertical vent slots on rear wall
    for i in range(7):
        base=base.cut(box(5,wall+2,14,28+i*8,D-wall-1,10))
    # board standoffs, Pi 4 hole pattern 58 x 49 mm
    for x,y in [(wall+3.5,wall+3.5),(wall+61.5,wall+3.5),(wall+3.5,wall+52.5),(wall+61.5,wall+52.5)]:
        boss=Part.makeCylinder(3.2,4.5,App.Vector(x,y,floor))
        hole=Part.makeCylinder(1.45,5.0,App.Vector(x,y,floor))
        base=base.fuse(boss.cut(hole))
    # tent/cable-tie mounting ears
    for y in (10,46):
        ear=box(10,12,4,-8,y,2)
        slot=box(5,8,6,-6,y+2,1)
        base=base.fuse(ear.cut(slot))
    # lid: inset lip + open GPIO service bay + crossflow vents + visible GC mark
    lid=box(W,D,2.6,0,0,0)
    lip=box(W-2*(wall+0.35),D-2*(wall+0.35),3.2,wall+0.35,wall+0.35,-3.0)
    lid=lid.fuse(lip)
    # GPIO access window sized to leave the 40-pin header genuinely usable
    lid=lid.cut(box(54,10,7,8,49,-3.2))
    # vents above SoC/USB area
    for r in range(3):
        for c in range(6):
            lid=lid.cut(box(7,2.6,7,14+c*11,14+r*8,-3.2))
    # embossed Grow Central mark
    lid=lid.fuse(gc_mark(77,47,2.6,1.2,0.85))
    # robust front badge bar, makes orientation obvious
    lid=lid.fuse(box(42,3,1.0,8,5,2.6))
    save_part(doc,'Pi4_Base',base,'GrowCentral_Pi4_Base_FreeCAD')
    save_part(doc,'Pi4_Lid_GPIO',lid,'GrowCentral_Pi4_Lid_GPIO_FreeCAD')
    doc.recompute()
    doc.saveAs(os.path.join(OUT,'GrowCentral_Pi4_Case.FCStd'))
    App.closeDocument(doc.Name)


def xiao_enclosure(kind='node'):
    # XIAO ESP32-C3 PCB is ~21 x 17.5 mm. Clearance includes soldered header strips.
    is_hub = kind=='hub'
    doc=App.newDocument('GrowCentral_XIAO_'+kind.capitalize())
    wall=2.0; floor=2.2
    if is_hub:
        W,D,H=58.0,44.0,24.0
        board_x,board_y=10.0,10.0
    else:
        W,D,H=38.0,30.0,20.0
        board_x,board_y=8.0,6.0
    outer=box(W,D,H)
    inner=box(W-2*wall,D-2*wall,H-floor+1,wall,wall,floor)
    base=outer.cut(inner)
    # USB-C opening aligned with short edge of XIAO.
    base=base.cut(box(12,wall+2,8,board_x+4,-1,6))
    # cable/sensor exits, deliberately separated from USB service side
    base=base.cut(box(wall+2,10,8,W-wall-1,D-15,6))
    if is_hub:
        base=base.cut(box(wall+2,10,8,W-wall-1,6,6))
        base=base.cut(box(14,wall+2,8,W/2-7,D-wall-1,6))
    # PCB support rails instead of relying on tiny screws near soldered headers
    rail_h=4.0
    base=base.fuse(box(23,2.2,rail_h,board_x,board_y,floor))
    base=base.fuse(box(23,2.2,rail_h,board_x,board_y+19.7,floor))
    # keep header-pin underside clear
    header_clear=box(23,15,4.5,board_x,board_y+3.5,floor)
    base=base.cut(header_clear)
    # cable tie wall mount
    ear=box(8,18,4,-6,(D-18)/2,2)
    ear=ear.cut(box(4,12,6,-4,(D-12)/2,1))
    base=base.fuse(ear)
    # Hub gets internal divider/terminal shelf
    if is_hub:
        shelf=box(22,30,2.6,34,7,floor-0.2)
        base=base.fuse(shelf)
    # lid with ventilation and highly visible GC mark
    lid=box(W,D,2.4)
    lip=box(W-2*(wall+0.3),D-2*(wall+0.3),2.8,wall+0.3,wall+0.3,-2.6)
    lid=lid.fuse(lip)
    rows=2 if not is_hub else 3
    cols=3 if not is_hub else 5
    for r in range(rows):
        for c in range(cols):
            lid=lid.cut(box(5.5,2.2,6,7+c*8.5,7+r*7,-2.8))
    logo_scale=0.62 if not is_hub else 0.75
    lid=lid.fuse(gc_mark(W-9,D-9,2.4,1.1,logo_scale))
    stem='GrowCentral_XIAO_'+kind.capitalize()
    save_part(doc,stem+'_Base',base,stem+'_Base_FreeCAD')
    save_part(doc,stem+'_Lid',lid,stem+'_Lid_FreeCAD')
    doc.recompute()
    doc.saveAs(os.path.join(OUT,stem+'.FCStd'))
    App.closeDocument(doc.Name)


if __name__=='__main__':
    pi4_case()
    xiao_enclosure('node')
    xiao_enclosure('hub')
    print('Grow-Central enclosure set generated in', OUT)
