from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(r'C:\Users\dezen\Desktop\135er-Grow-Central\hardware\enclosures\prototype_v4\previews')
plate_cases=['Pi4','Node_FPC','Node_EXT','Hub_FPC','Hub_EXT']
bold=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',42); normal=ImageFont.truetype(r'C:\Windows\Fonts\bahnschrift.ttf',25)
for c in plate_cases:
 path=P/f'GrowCentral_{c}_P2S_V4_PROTOTYP_plate.png'; im=Image.open(path).convert('RGB'); dr=ImageDraw.Draw(im)
 dr.rounded_rectangle((30,28,430,100),14,fill=(18,20,22)); dr.text((50,40),'PROTOTYP',font=bold,fill=(245,65,60)); dr.text((50,105),'P2S-Testplatte, keine Serienfreigabe',font=normal,fill=(235,235,235),stroke_width=2,stroke_fill=(30,30,30)); im.save(path)
# overview: 5 plate renders + 4 mounting renders
entries=[]
for c in plate_cases: entries.append((P/f'GrowCentral_{c}_P2S_V4_PROTOTYP_plate.png',c.replace('_',' ')+' Platte'))
for c in ['Node_FPC','Node_EXT','Hub_FPC','Hub_EXT']: entries.append((P/f'GrowCentral_{c}_V4_PROTOTYP_Montage.png',c.replace('_',' ')+' Montage'))
thumb_w,thumb_h=620,435; gap=22; top=135; cols=2; rows=(len(entries)+1)//2
canvas=Image.new('RGB',(cols*thumb_w+(cols+1)*gap,top+rows*(thumb_h+62+gap)+gap),(25,27,29)); dr=ImageDraw.Draw(canvas)
fhead=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',46); fsub=ImageFont.truetype(r'C:\Windows\Fonts\bahnschrift.ttf',26); flab=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',28)
dr.text((30,20),'GROW-CENTRAL V4 - PROTOTYP',font=fhead,fill=(245,245,245)); dr.text((30,78),'Pi4 / Node / Hub | FPC + EXT | liegende + stehende Montage | Fertigungsverfahren offen',font=fsub,fill=(190,195,200))
for i,(path,label) in enumerate(entries):
 im=Image.open(path).convert('RGB'); im.thumbnail((thumb_w,thumb_h)); x=gap+(i%2)*(thumb_w+gap); y=top+(i//2)*(thumb_h+62+gap); canvas.paste(im,(x,y)); dr.text((x,y+thumb_h+10),label,font=flab,fill=(235,235,235))
out=P/'GrowCentral_V4_PROTOTYP_Gesamtuebersicht.png'; canvas.save(out); print(out)
