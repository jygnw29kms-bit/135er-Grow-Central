from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(r'C:\Users\dezen\Desktop\135er-Grow-Central\hardware\enclosures\prototype_v5\previews')
CASES={'Node_FPC':'FPC','Node_EXT':'EXT','Hub_FPC':'FPC','Hub_EXT':'EXT'}
bold=Path(r'C:\Windows\Fonts\arialbd.ttf'); normal=Path(r'C:\Windows\Fonts\bahnschrift.ttf')
f1=ImageFont.truetype(str(bold),42); f2=ImageFont.truetype(str(normal),27); f3=ImageFont.truetype(str(normal),23)
for case,mode in CASES.items():
 for suffix,title_extra in [('Montage','RF / Gesamtansicht'),('Montage_MountingZones','Montagezonen')]:
  path=P/f'GrowCentral_{case}_V5_PROTOTYP_{suffix}.png'; src=Image.open(path).convert('RGB')
  top,bottom=150,180; canvas=Image.new('RGB',(src.width,src.height+top+bottom),(238,240,242)); canvas.paste(src,(0,top)); dr=ImageDraw.Draw(canvas)
  dr.text((45,24),f'GROW-CENTRAL {case.replace("_"," ")} V5',font=f1,fill=(28,32,36)); dr.text((47,78),f'PROTOTYP  |  {title_extra}  |  KEINE SERIENFREIGABE',font=f2,fill=(188,38,38))
  y=src.height+top+25
  dr.ellipse((45,y,73,y+28),fill=(20,78,250)); dr.text((92,y-2),'LIEGEND: 2 x M4, eigene Front-/Boden-Zone, vertikale Schraubachse',font=f3,fill=(32,36,40))
  dr.ellipse((45,y+48,73,y+76),fill=(0,188,220)); dr.text((92,y+46),'STEHEND: 2 x M4, getrennte Seitenwand-Zone, horizontale Schraubachse',font=f3,fill=(32,36,40))
  if mode=='FPC': dr.rectangle((45,y+96,73,y+124),fill=(245,86,12)); dr.text((92,y+94),'FPC-Antenne 40 x 20 mm auf separatem Heckträger',font=f3,fill=(32,36,40))
  else: dr.ellipse((45,y+96,73,y+124),fill=(230,155,18)); dr.text((92,y+94),'6,5 mm SMA / RP-SMA Bulkhead an separater Heckzone',font=f3,fill=(32,36,40))
  canvas.save(path); print('OVERLAY',path)
