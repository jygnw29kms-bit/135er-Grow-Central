import FreeCAD as App
import Part, os
base=os.path.join(os.path.dirname(__file__),'references')
files=['RaspberryPi4_PartCAD_rpi4b.step','XIAO_ESP32C3_hansrune_detailed.step','XIAO_ESP32C3_hansrune_simple.step']
for f in files:
    s=Part.read(os.path.join(base,f))
    bb=s.BoundBox
    print(f)
    print(' bbox',round(bb.XLength,3),round(bb.YLength,3),round(bb.ZLength,3))
    print(' min ',round(bb.XMin,3),round(bb.YMin,3),round(bb.ZMin,3))
    print(' max ',round(bb.XMax,3),round(bb.YMax,3),round(bb.ZMax,3))
    print(' solids',len(s.Solids),'valid',s.isValid())
