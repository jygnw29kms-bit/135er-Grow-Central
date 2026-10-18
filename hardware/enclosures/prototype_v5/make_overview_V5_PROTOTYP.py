from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(r'C:\Users\dezen\Desktop\135er-Grow-Central\hardware\enclosures\prototype_v5\previews')
plate_cases=['Pi4','Node_FPC','Node_EXT','Hub_FPC','Hub_EXT']
bold=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',40); normal=ImageFont.truetype(r'C:\Windows\Fonts\bahnschrift.ttf',24)
for c in plate_cases:
 path=P/f'GrowCentral_{c}_P2S_V5_PROTOTYP_plate.png'; src=Image.open(path).convert('RGB')
 top=118; canvas=Image.new('RGB',(src.width,src.height+top),(238,240,242)); canvas.paste(src,(0,top)); dr=ImageDraw.Draw(canvas)
 dr.text((42,20),f'{c.replace("_"," ")}  |  PROTOTYP',font=bold,fill=(30,34,38)); dr.text((44,69),'P2S-Testplatte  |  keine Serienfreigabe  |  0,4 mm / 0,20 Standard',font=normal,fill=(176,42,42)); canvas.save(path)
entries=[]
for c in plate_cases: entries.append((P/f'GrowCentral_{c}_P2S_V5_PROTOTYP_plate.png',c.replace('_',' ')+' Platte'))
for c in ['Node_FPC','Node_EXT','Hub_FPC','Hub_EXT']: entries.append((P/f'GrowCentral_{c}_V5_PROTOTYP_Montage_MountingZones.png',c.replace('_',' ')+' Montage'))
thumb_w,thumb_h=620,475; gap=22; top=135; cols=2; rows=(len(entries)+1)//2
canvas=Image.new('RGB',(cols*thumb_w+(cols+1)*gap,top+rows*(thumb_h+62+gap)+gap),(235,237,239)); dr=ImageDraw.Draw(canvas)
fhead=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',46); fsub=ImageFont.truetype(r'C:\Windows\Fonts\bahnschrift.ttf',25); flab=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',27)
dr.text((30,20),'GROW-CENTRAL V5 - PROTOTYP',font=fhead,fill=(25,29,33)); dr.text((30,78),'Pi4 / Node / Hub | FPC + EXT | getrennte Montagezonen | Fertigungsverfahren offen',font=fsub,fill=(70,76,82))
for i,(path,label) in enumerate(entries):
 im=Image.open(path).convert('RGB'); im.thumbnail((thumb_w,thumb_h)); x=gap+(i%2)*(thumb_w+gap); y=top+(i//2)*(thumb_h+62+gap); px=x+(thumb_w-im.width)//2; canvas.paste(im,(px,y)); dr.text((x,y+thumb_h+10),label,font=flab,fill=(35,39,43))
out=P/'GrowCentral_V5_PROTOTYP_Gesamtuebersicht.png'; canvas.save(out); print(out)

