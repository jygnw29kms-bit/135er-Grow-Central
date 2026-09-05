#!/usr/bin/env python3
import os, subprocess, threading, time
from flask import Flask, jsonify, request, render_template_string
app=Flask(__name__)
CAN_IFACE=os.getenv('CAN_IFACE','can0'); CAN_BITRATE=int(os.getenv('CAN_BITRATE','500000')); frames=[]; lock=threading.Lock()
HTML='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dyson V11 BMS</title><style>body{font-family:system-ui;background:#111;color:#eee;margin:20px}.card{background:#1c1c1c;padding:18px;border-radius:14px;margin-bottom:14px}input,button{padding:10px;margin:4px;border-radius:8px;border:0}pre{white-space:pre-wrap;word-break:break-word}</style></head><body><h1>Dyson V11 BMS · Pi3</h1><div class="card"><h2>CAN Setup</h2><input id="i" value="{{i}}"><input id="b" value="{{b}}"><button onclick="setc()">Apply</button><pre id="s"></pre></div><div class="card"><h2>Read-only CAN monitor</h2><pre id="f"></pre></div><script>async function r(){s.textContent=JSON.stringify(await fetch('/api/status').then(x=>x.json()),null,2);f.textContent=(await fetch('/api/frames').then(x=>x.json())).map(x=>x.ts+' '+x.id+' '+x.data).join('\n')}async function setc(){await fetch('/api/can',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({iface:i.value,bitrate:Number(b.value)})});r()}setInterval(r,1500);r()</script></body></html>'''
def sh(*a): return subprocess.run(a,text=True,capture_output=True)
def up(i,b):
 sh('ip','link','set',i,'down'); r=sh('ip','link','set',i,'type','can','bitrate',str(b));
 if r.returncode:return False,r.stderr.strip()
 r=sh('ip','link','set',i,'up'); return r.returncode==0,(r.stderr or r.stdout).strip()
def mon():
 global CAN_IFACE
 while True:
  p=subprocess.Popen(['candump','-L',CAN_IFACE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
  for line in p.stdout:
   z=line.strip().split()
   if len(z)>=3:
    with lock:
     v=z[-1].split('#'); frames.append({'ts':z[0].strip('()'),'id':v[0],'data':v[-1]}); del frames[:-200]
  time.sleep(2)
@app.get('/')
def index(): return render_template_string(HTML,i=CAN_IFACE,b=CAN_BITRATE)
@app.get('/api/status')
def status():
 r=sh('ip','-details','link','show',CAN_IFACE); return jsonify(iface=CAN_IFACE,bitrate=CAN_BITRATE,link_ok=r.returncode==0,details=r.stdout[-2000:])
@app.get('/api/frames')
def gf():
 with lock:return jsonify(list(frames[-100:]))
@app.post('/api/can')
def sc():
 global CAN_IFACE,CAN_BITRATE
 d=request.get_json(force=True); i=str(d.get('iface','can0')).strip(); b=int(d.get('bitrate',500000))
 if not i.replace('_','').replace('-','').isalnum() or b not in (10000,20000,50000,100000,125000,250000,500000,800000,1000000): return jsonify(ok=False,error='invalid CAN settings'),400
 ok,msg=up(i,b)
 if ok:
  CAN_IFACE,CAN_BITRATE=i,b
  open('/etc/default/dyson-bms','w').write(f'CAN_IFACE={i}\nCAN_BITRATE={b}\n')
 return jsonify(ok=ok,message=msg)
if __name__=='__main__': threading.Thread(target=mon,daemon=True).start(); app.run(host='0.0.0.0',port=8080)
