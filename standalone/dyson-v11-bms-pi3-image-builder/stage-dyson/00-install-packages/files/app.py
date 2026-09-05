#!/usr/bin/env python3
import os, subprocess, threading, time
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)
CAN_IFACE = os.getenv("CAN_IFACE", "can0")
CAN_BITRATE = int(os.getenv("CAN_BITRATE", "500000"))
frames = []
lock = threading.Lock()

PCB_ADAPTERS = [
    {"model":"V6","pcb":"61462","interface":"PIC-ICSP","status":"TESTED","status_class":"ok",
     "signals":["MCLR/VPP","GND","ICSPDAT","ICSPCLK"],
     "adapter":"V6_PCB_61462_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical":"Elektrisch verifiziert; hochauflösendes Referenzbild vorhanden. Pogo-Abstände am realen Board messen.",
     "notes":"PIC16LF1847. Programmer-VDD nicht blind in das Dyson-BMS einspeisen."},
    {"model":"V6","pcb":"188002","interface":"PIC-ICSP","status":"TESTED","status_class":"ok",
     "signals":["MCLR/VPP","GND","ICSPDAT","ICSPCLK"],
     "adapter":"V6_PCB_188002_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical":"Elektrisch verifiziert; Boardfoto vorhanden. Pogo-Abstände am realen Board messen.",
     "notes":"PIC16LF1847. Reprogrammierung in Community dokumentiert."},
    {"model":"V7","pcb":"279857","interface":"PIC-ICSP","status":"TESTED","status_class":"ok",
     "signals":["MCLR/VPP","GND","ICSPDAT","ICSPCLK"],
     "adapter":"V7_PCB_279857_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical":"Elektrisch verifiziert; hochauflösendes Board-/Wiring-Bild vorhanden. Millimeter-Pitch vor Druck messen.",
     "notes":"PIC16LF1847. PCB-spezifischer Adapter vorgesehen."},
    {"model":"V7","pcb":"228499","interface":"PIC-ICSP","status":"REPORTED WORKING","status_class":"warn",
     "signals":["MCLR/VPP","GND","ICSPDAT","ICSPCLK"],
     "adapter":"V7_PCB_228499_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical":"Elektrischer Pfad berichtet; keine autoritativen mm-Padkoordinaten gefunden.",
     "notes":"Vor Freigabe Boardrevision und Padabstände am Original prüfen."},
    {"model":"V8","pcb":"180207","interface":"PIC-ICSP","status":"WORKING REPORTS","status_class":"warn",
     "signals":["MCLR/VPP","GND","ICSPDAT","ICSPCLK"],
     "adapter":"V8_PCB_180207_PIC-ICSP_ALIGNMENT_FIXTURE",
     "mechanical":"Reverse Engineering und erfolgreiche Berichte; exakte mm-Padkoordinaten nicht öffentlich normiert.",
     "notes":"V8 D/E und weitere Revisionen nicht pauschal gleichsetzen."},
    {"model":"V10","pcb":"board-specific","interface":"SWD","status":"INTERFACE VERIFIED","status_class":"warn",
     "signals":["GND","SWDIO","SWCLK","UART optional"],
     "adapter":"V10_SWD_ALIGNMENT_FIXTURE_UNVERIFIED",
     "mechanical":"SWD/OpenOCD-Pfad bekannt; exakte Testpad-Geometrie pro Originalboard verifizieren.",
     "notes":"SAMD20-Familie. UART nur verwenden, wenn für das konkrete Board/Firmware dokumentiert."},
    {"model":"V11","pcb":"board-specific","interface":"SWD","status":"INTERFACE VERIFIED","status_class":"warn",
     "signals":["GND","SWDIO","SWCLK"],
     "adapter":"V11_SWD_ALIGNMENT_FIXTURE_UNVERIFIED",
     "mechanical":"SAMD20E15/SWD bekannt; Screw- und Click-In-Boards mechanisch getrennt prüfen.",
     "notes":"Keine universelle Pogo-Geometrie ohne Boardmessung verwenden."},
    {"model":"V12","pcb":"unverified","interface":"SWD-family","status":"EXPERIMENTAL","status_class":"exp",
     "signals":["nur nach Board-Verifikation"],"adapter":"kein freigegebener Adapter",
     "mechanical":"Keine universell bestätigte Testpad-Geometrie.","notes":"Nicht automatisch freischalten."},
    {"model":"V15","pcb":"unverified","interface":"SWD-family","status":"EXPERIMENTAL","status_class":"exp",
     "signals":["nur nach Board-Verifikation"],"adapter":"kein freigegebener Adapter",
     "mechanical":"Keine universell bestätigte Testpad-Geometrie.","notes":"Nicht automatisch freischalten."}
]

HTML = r'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>135er Dyson Service Center</title>
<style>
:root{--bg:#07121d;--panel:#0d1b28;--line:#20384b;--blue:#168cff;--green:#29e477;--yellow:#f7b928;--red:#ff4d5e;--muted:#8fa6b8;--text:#f5f8fb}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:linear-gradient(135deg,#06101a,#0a1723);color:var(--text)}
header{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line);background:#081520}
.brand{font-size:28px;font-weight:800}.brand span{color:var(--blue)}.sub,.muted{color:var(--muted);font-size:13px}
.online{background:#0f3b2a;color:#8affb7;padding:8px 12px;border-radius:8px;font-size:13px}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 74px)}
nav{border-right:1px solid var(--line);padding:18px 12px;background:#081722}
nav button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#c8d5df;padding:12px 14px;border-radius:8px;margin:4px 0;cursor:pointer;font-size:14px}
nav button.active,nav button:hover{background:#0e6ee8;color:white}
main{padding:18px;overflow:auto}.page{display:none}.page.active{display:block}
.grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:12px}
.card{background:linear-gradient(180deg,#0d1b28,#0a1823);border:1px solid var(--line);border-radius:12px;padding:15px}
.card h3{margin:0 0 10px;font-size:16px}.metric{font-size:28px;font-weight:800}
.models{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.model{padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:#0d1b28;font-weight:700}
.model.ok{border-color:#1d7b50}.model.warn{border-color:#876b24}.model.exp{border-color:#7b4d24}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800}.badge.ok{background:#123b28;color:#74f0a4}.badge.warn{background:#443919;color:#ffd765}.badge.exp{background:#4b2e1b;color:#ffb26d}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{color:#cfe3f2;background:#0a1d2b;position:sticky;top:0}
.signal{display:inline-block;background:#122c3f;border:1px solid #29465b;border-radius:6px;padding:3px 6px;margin:2px;font-size:11px}
.notice{border-left:4px solid var(--yellow);padding:12px 14px;background:#2b2717;border-radius:8px;margin:12px 0;color:#f7e5a4}.notice.red{border-color:var(--red);background:#2b171b;color:#ffc3ca}
input,button.action{padding:9px;border-radius:7px;border:1px solid #29465b;background:#0b1b27;color:white}.action{cursor:pointer}
pre{white-space:pre-wrap;word-break:break-word;background:#061019;padding:10px;border-radius:8px;max-height:320px;overflow:auto}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:900px){.layout{grid-template-columns:1fr}nav{display:flex;overflow:auto;border-right:0;border-bottom:1px solid var(--line)}nav button{min-width:140px}.grid{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
<div><div class="brand">135er <span>Dyson Service Center</span></div><div class="sub">Diagnose · PCB & Adapter · Raspberry Pi 3</div></div>
<div class="online">● System Online</div>
</header>
<div class="layout">
<nav>
<button class="active" onclick="showPage('dashboard',this)">Dashboard</button>
<button onclick="showPage('pcb',this)">PCB & Adapter</button>
<button onclick="showPage('can',this)">CAN Monitor</button>
<button onclick="showPage('system',this)">System</button>
</nav>
<main>
<section id="dashboard" class="page active">
<div class="models">
{% for m in models %}<div class="model {{m.cls}}">{{m.name}}<br><span class="sub">{{m.state}}</span></div>{% endfor %}
</div>
<div class="grid">
<div class="card"><h3>Akku</h3><div class="metric">Board-Diagnose</div><div class="muted">Interne BMS-Testpads</div></div>
<div class="card"><h3>Verifizierte PCBs</h3><div class="metric">{{verified_count}}</div><div class="muted">V6/V7 bekannte Revisionen</div></div>
<div class="card"><h3>Schnittstellen</h3><div class="metric">ICSP / SWD</div><div class="muted">revisionsabhängig</div></div>
<div class="card"><h3>Mechanik</h3><div class="metric">PCB-spezifisch</div><div class="muted">Pogo-Geometrie erst nach Boardmessung</div></div>
</div>
<div class="notice">Diagnose erfolgt direkt am internen BMS-Board. Der äußere Dyson-Leistungsstecker ist kein Ersatz für die PCB-Testpads.</div>
<div class="card"><h3>Freigabelogik</h3>
<p><span class="badge ok">TESTED</span> elektrischer Pfad/Boardfamilie belastbar belegt.</p>
<p><span class="badge warn">REPORTED / INTERFACE VERIFIED</span> elektrischer Pfad bekannt, mechanische Pad-Geometrie am Originalboard prüfen.</p>
<p><span class="badge exp">EXPERIMENTAL</span> keine automatische Servicefreigabe.</p>
</div>
</section>
<section id="pcb" class="page">
<div class="card">
<h3>PCB- & Adapterdatenbank</h3>
<div class="muted">Rev-5 Verifikationsmatrix direkt in der App. Suche nach Modell oder PCB.</div>
<p><input id="pcbSearch" placeholder="z. B. 61462, V7, SWD" oninput="filterPCB()"></p>
<div style="overflow:auto;max-height:65vh"><table id="pcbTable">
<thead><tr><th>Modell</th><th>PCB</th><th>Status</th><th>Schnittstelle</th><th>Signale</th><th>Adapter</th><th>Mechanik / Hinweis</th></tr></thead>
<tbody>{% for x in pcb %}<tr>
<td><b>{{x.model}}</b></td><td>{{x.pcb}}</td><td><span class="badge {{x.status_class}}">{{x.status}}</span></td>
<td>{{x.interface}}</td><td>{% for s in x.signals %}<span class="signal">{{s}}</span>{% endfor %}</td>
<td><code>{{x.adapter}}</code></td><td>{{x.mechanical}}<br><span class="muted">{{x.notes}}</span></td>
</tr>{% endfor %}</tbody></table></div>
</div>
<div class="notice red"><b>Wichtig:</b> Ein elektrisch bekanntes Pinout bedeutet nicht automatisch, dass die Pogo-Pin-Abstände mechanisch universell sind. Keine festen Bohrkoordinaten verwenden, bevor die konkrete PCB-Revision am Originalakku vermessen wurde.</div>
</section>
<section id="can" class="page"><div class="two">
<div class="card"><h3>CAN Setup</h3><input id="i" value="{{i}}"><input id="b" value="{{b}}"><button class="action" onclick="setc()">Übernehmen</button><pre id="s"></pre></div>
<div class="card"><h3>Read-only CAN Monitor</h3><pre id="f"></pre></div>
</div></section>
<section id="system" class="page"><div class="card"><h3>API</h3>
<p><code>GET /api/pcb-adapters</code> – komplette PCB-/Adaptermatrix</p>
<p><code>GET /api/pcb-adapters/&lt;pcb&gt;</code> – einzelnes PCB-Profil</p>
<p><code>GET /api/status</code> – CAN/Systemstatus</p>
</div><div class="notice">V6/V7/V8: PIC-ICSP. V10/V11: SWD/OpenOCD. V12/V15 bleiben bis zur mechanischen Verifikation experimentell.</div></section>
</main></div>
<script>
function showPage(id,btn){document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('nav button').forEach(x=>x.classList.remove('active'));btn.classList.add('active')}
function filterPCB(){let q=document.getElementById('pcbSearch').value.toLowerCase();document.querySelectorAll('#pcbTable tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')}
async function refreshCAN(){try{s.textContent=JSON.stringify(await fetch('/api/status').then(x=>x.json()),null,2);f.textContent=(await fetch('/api/frames').then(x=>x.json())).map(x=>x.ts+' '+x.id+' '+x.data).join('\\n')}catch(e){}}
async function setc(){await fetch('/api/can',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({iface:i.value,bitrate:Number(b.value)})});refreshCAN()}
setInterval(refreshCAN,1500);refreshCAN()
</script>
</body></html>'''

def sh(*a):
    return subprocess.run(a, text=True, capture_output=True)

def up(i,b):
    sh("ip","link","set",i,"down")
    r=sh("ip","link","set",i,"type","can","bitrate",str(b))
    if r.returncode:
        return False,r.stderr.strip()
    r=sh("ip","link","set",i,"up")
    return r.returncode==0,(r.stderr or r.stdout).strip()

def mon():
    global CAN_IFACE
    while True:
        try:
            p=subprocess.Popen(["candump","-L",CAN_IFACE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
            for line in p.stdout:
                z=line.strip().split()
                if len(z)>=3:
                    with lock:
                        v=z[-1].split("#")
                        frames.append({"ts":z[0].strip("()"),"id":v[0],"data":v[-1]})
                        del frames[:-200]
        except Exception:
            pass
        time.sleep(2)

@app.get("/")
def index():
    model_state={}
    for x in PCB_ADAPTERS:
        cur=model_state.setdefault(x["model"],{"ok":0,"warn":0,"exp":0})
        cur[x["status_class"]]+=1
    models=[]
    for name in ["V6","V7","V8","V10","V11","V12","V15"]:
        st=model_state.get(name,{"ok":0,"warn":0,"exp":1})
        if st["ok"]: cls,state="ok","integriert"
        elif st["warn"]: cls,state="warn","teilverifiziert"
        else: cls,state="exp","experimental"
        models.append({"name":name,"cls":cls,"state":state})
    verified_count=sum(1 for x in PCB_ADAPTERS if x["status_class"]=="ok")
    return render_template_string(HTML,i=CAN_IFACE,b=CAN_BITRATE,pcb=PCB_ADAPTERS,models=models,verified_count=verified_count)

@app.get("/api/pcb-adapters")
def pcb_adapters():
    return jsonify(PCB_ADAPTERS)

@app.get("/api/pcb-adapters/<pcb>")
def pcb_adapter(pcb):
    hits=[x for x in PCB_ADAPTERS if str(x["pcb"]).lower()==pcb.lower()]
    if not hits:
        return jsonify(error="PCB profile not found"),404
    return jsonify(hits)

@app.get("/api/status")
def status():
    r=sh("ip","-details","link","show",CAN_IFACE)
    return jsonify(iface=CAN_IFACE,bitrate=CAN_BITRATE,link_ok=r.returncode==0,details=r.stdout[-2000:])

@app.get("/api/frames")
def gf():
    with lock:
        return jsonify(list(frames[-100:]))

@app.post("/api/can")
def sc():
    global CAN_IFACE,CAN_BITRATE
    d=request.get_json(force=True)
    i=str(d.get("iface","can0")).strip()
    b=int(d.get("bitrate",500000))
    if not i.replace("_","").replace("-","").isalnum() or b not in (10000,20000,50000,100000,125000,250000,500000,800000,1000000):
        return jsonify(ok=False,error="invalid CAN settings"),400
    ok,msg=up(i,b)
    if ok:
        CAN_IFACE,CAN_BITRATE=i,b
        with open("/etc/default/dyson-bms","w",encoding="utf-8") as fh:
            fh.write(f"CAN_IFACE={i}\\nCAN_BITRATE={b}\\n")
    return jsonify(ok=ok,message=msg)

if __name__=="__main__":
    threading.Thread(target=mon,daemon=True).start()
    app.run(host="0.0.0.0",port=8080)
