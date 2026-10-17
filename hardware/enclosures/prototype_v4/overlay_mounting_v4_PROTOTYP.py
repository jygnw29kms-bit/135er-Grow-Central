from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(r'C:\Users\dezen\Desktop\135er-Grow-Central\hardware\enclosures\prototype_v4\previews')
CASES={'Node_FPC':'FPC','Node_EXT':'EXT','Hub_FPC':'FPC','Hub_EXT':'EXT'}
bold=Path(r'C:\Windows\Fonts\arialbd.ttf'); normal=Path(r'C:\Windows\Fonts\bahnschrift.ttf')
f1=ImageFont.truetype(str(bold),44); f2=ImageFont.truetype(str(normal),29); f3=ImageFont.truetype(str(normal),25)
for case,mode in CASES.items():
 path=P/f'GrowCentral_{case}_V4_PROTOTYP_Montage.png'; im=Image.open(path).convert('RGB'); dr=ImageDraw.Draw(im)
 dr.rounded_rectangle((28,24,1030,155),18,fill=(18,20,22)); dr.text((50,40),f'GROW-CENTRAL {case.replace("_"," ")} V4',font=f1,fill=(240,240,240)); dr.text((50,101),'PROTOTYP  |  KEINE SERIENFREIGABE',font=f2,fill=(245,72,66))
 dr.rounded_rectangle((28,820,810,1018),18,fill=(18,20,22)); dr.ellipse((55,850,85,880),fill=(15,88,255)); dr.text((105,846),'LIEGEND: 2 x M4, vertikale Schraubachse',font=f3,fill=(232,232,232)); dr.ellipse((55,900,85,930),fill=(0,225,240)); dr.text((105,896),'STEHEND: 2 x M4, horizontale Schraubachse',font=f3,fill=(232,232,232))
 if mode=='FPC': dr.rectangle((55,952,85,982),fill=(255,94,5)); dr.text((105,947),'Original-Klebeantenne 40 x 20 mm',font=f3,fill=(232,232,232))
 else: dr.ellipse((55,952,85,982),fill=(235,165,25)); dr.text((105,947),'6,5 mm SMA / RP-SMA Bulkhead',font=f3,fill=(232,232,232))
 im.save(path); print('OVERLAY',path)
