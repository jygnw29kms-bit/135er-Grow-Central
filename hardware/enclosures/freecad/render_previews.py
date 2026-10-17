import os, glob, struct
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

BASE = os.path.dirname(os.path.abspath(__file__))
PRE = os.path.join(BASE, 'previews')
os.makedirs(PRE, exist_ok=True)

def load_binary_stl(path):
    tris=[]
    with open(path,'rb') as f:
        header=f.read(80)
        n=struct.unpack('<I',f.read(4))[0]
        for _ in range(n):
            data=f.read(50)
            if len(data)<50: break
            vals=struct.unpack('<12fH',data)
            tris.append([(vals[3],vals[4],vals[5]),(vals[6],vals[7],vals[8]),(vals[9],vals[10],vals[11])])
    return tris

def load_ascii_stl(path):
    tris=[]; cur=[]
    with open(path,'r',errors='ignore') as f:
        for line in f:
            s=line.strip().split()
            if len(s)==4 and s[0].lower()=='vertex':
                cur.append(tuple(map(float,s[1:])))
                if len(cur)==3:
                    tris.append(cur); cur=[]
    return tris

def load_stl(path):
    with open(path,'rb') as f:
        h=f.read(84)
    if len(h)>=84:
        n=struct.unpack('<I',h[80:84])[0]
        if 84+n*50==os.path.getsize(path):
            return load_binary_stl(path)
    return load_ascii_stl(path)

for stl in sorted(glob.glob(os.path.join(BASE, '*.stl'))):
    tris=load_stl(stl)
    xs=[p[0] for t in tris for p in t]; ys=[p[1] for t in tris for p in t]; zs=[p[2] for t in tris for p in t]
    fig=plt.figure(figsize=(11.2,8), dpi=125)
    ax=fig.add_subplot(111, projection='3d')
    poly=Poly3DCollection(tris, linewidths=0.16, edgecolors='black')
    poly.set_facecolor((0.42,0.82,0.52,1.0)); ax.add_collection3d(poly)
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); zmin,zmax=min(zs),max(zs)
    cx=(xmin+xmax)/2; cy=(ymin+ymax)/2; cz=(zmin+zmax)/2
    span=max(xmax-xmin,ymax-ymin,zmax-zmin)*0.60
    ax.set_xlim(cx-span,cx+span); ax.set_ylim(cy-span,cy+span); ax.set_zlim(cz-span*0.75,cz+span*0.75)
    ax.view_init(elev=28, azim=-55); ax.set_axis_off(); ax.set_box_aspect((1,1,0.7))
    title=os.path.basename(stl).replace('_FreeCAD.stl','').replace('_',' ')
    ax.set_title(title, fontsize=15, pad=8)
    out=os.path.join(PRE, os.path.splitext(os.path.basename(stl))[0]+'_preview.png')
    plt.savefig(out, bbox_inches='tight', pad_inches=0.18, facecolor='white')
    plt.close(fig)
    print(out)
