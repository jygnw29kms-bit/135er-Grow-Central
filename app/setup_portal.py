"""Captive first-boot portal for the unprovisioned appliance."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app import firstboot


SETUP_HTML = r'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#02070a"><title>135er Grow Central · Ersteinrichtung</title><style>
:root{--bg:#02070a;--panel:#071319;--line:#17414a;--cyan:#2ae5ff;--green:#71ff3b;--text:#edfdf9;--muted:#7ea1a8;--red:#ff6877}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:radial-gradient(circle at 70% 0,#0b2630,#02070a 38%);color:var(--text);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}body{min-height:100vh;min-height:100dvh;padding:max(18px,env(safe-area-inset-top)) max(14px,env(safe-area-inset-right)) max(18px,env(safe-area-inset-bottom)) max(14px,env(safe-area-inset-left))}.wrap{width:min(760px,100%);margin:auto}.brand{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px}.brand img{width:min(280px,65vw);max-height:72px;object-fit:contain;object-position:left}.badge{border:1px solid var(--green);color:var(--green);padding:7px 9px;border-radius:999px;font-size:.67rem;font-weight:800;white-space:nowrap}.panel{border:1px solid var(--line);background:linear-gradient(145deg,rgba(7,25,31,.96),rgba(3,11,15,.98));border-radius:18px;padding:clamp(18px,4vw,30px);box-shadow:0 24px 80px rgba(0,0,0,.4)}.eyebrow{color:var(--cyan);font-size:.68rem;font-weight:800;letter-spacing:.17em}.panel h1{margin:8px 0 7px;font-size:clamp(1.8rem,7vw,3.1rem);line-height:1}.lead{color:var(--muted);line-height:1.5;margin:0 0 20px}.network-state{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:18px}.network-state div{border:1px solid var(--line);padding:12px;border-radius:10px}.network-state small{display:block;color:var(--muted)}.network-state strong{display:block;margin-top:4px;color:var(--cyan)}.mode{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}.mode label{margin:0}.mode input{position:absolute;opacity:0}.mode span{display:block;text-align:center;border:1px solid var(--line);border-radius:10px;padding:13px;cursor:pointer;font-weight:800}.mode input:checked+span{border-color:var(--green);color:var(--green);background:rgba(113,255,59,.08)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:6px;color:#b8d2d5;font-size:.78rem;margin-bottom:12px}input,select{width:100%;min-width:0;padding:13px;border:1px solid var(--line);border-radius:9px;background:#020a0e;color:white;font-size:16px;outline:none}input:focus,select:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(42,229,255,.08)}.wifi-box{border:1px solid rgba(42,229,255,.14);padding:14px;border-radius:12px;margin-bottom:14px}.wifi-actions{display:flex;gap:8px;align-items:end}.wifi-actions label{flex:1;margin:0}button{min-height:48px;border:1px solid var(--green);border-radius:9px;background:rgba(113,255,59,.1);color:var(--green);font-weight:900;padding:0 16px;cursor:pointer}.submit{width:100%;margin-top:8px}.msg{min-height:1.4em;color:var(--muted);font-size:.8rem;margin-top:12px}.msg.error{color:var(--red)}.msg.ok{color:var(--green)}.hint{font-size:.72rem;color:var(--muted);line-height:1.5;margin-top:12px}@media(max-width:620px){.grid,.network-state,.mode{grid-template-columns:1fr}.brand{align-items:flex-start}.badge{font-size:.58rem}.wifi-actions{display:grid}.panel{border-radius:14px;padding:18px 14px}}
</style></head><body><main class="wrap"><header class="brand"><img src="/static/brand-logo.png" alt="135er Grow Central"><div class="badge">FIRST BOOT</div></header><section class="panel"><div class="eyebrow">135ER GROW CENTRAL · ERSTEINRICHTUNG</div><h1>System einrichten</h1><p class="lead">Nur die Daten, die Grow Central für den ersten Start wirklich benötigt. Danach wird der Setup-Hotspot beendet und die normale GUI verwendet.</p><div class="network-state"><div><small>LAN / WIRED</small><strong id="lanState">wird geprüft…</strong></div><div><small>SETUP</small><strong>10.42.0.1</strong></div></div><form id="setupForm"><div class="mode"><label><input type="radio" name="mode" value="ethernet" checked><span>WIRED / LAN</span></label><label><input type="radio" name="mode" value="wifi"><span>WLAN / WIFI</span></label></div><div id="wifiBox" class="wifi-box" hidden><div class="wifi-actions"><label>WLAN auswählen<select id="ssid"><option value="">Netzwerk wählen…</option></select></label><button type="button" id="scan">SUCHEN</button></div><label>WLAN-Passwort<input id="wifiPassword" type="password" autocomplete="new-password"></label></div><div class="grid"><label>GUI-Benutzer<input id="guiUser" autocomplete="username" required minlength="3" maxlength="32" placeholder="z. B. admin"></label><label>GUI-Passwort<input id="guiPassword" type="password" autocomplete="new-password" required minlength="12" placeholder="mindestens 12 Zeichen"></label><label>System-/SSH-Passwort<input id="systemPassword" type="password" autocomplete="new-password" required minlength="12" placeholder="mindestens 12 Zeichen"></label><label>System-/SSH-Passwort bestätigen<input id="systemPassword2" type="password" autocomplete="new-password" required minlength="12"></label></div><button class="submit" type="submit">EINRICHTUNG SPEICHERN & PRÜFEN</button><div id="msg" class="msg" role="status"></div><div class="hint">Hostname nach der Einrichtung: <b>135er-GrowCentral.local</b>. GUI- und System/SSH-Passwort sind getrennte Zugangsdaten.</div></form></section></main><script>
const $=id=>document.getElementById(id),msg=$('msg');function setMsg(t,c=''){msg.textContent=t;msg.className='msg '+c}function mode(){const m=document.querySelector('input[name=mode]:checked').value;$('wifiBox').hidden=m!=='wifi';if(m==='wifi')scan()}document.querySelectorAll('input[name=mode]').forEach(x=>x.addEventListener('change',mode));
async function status(){try{const r=await fetch('/api/setup/network-status',{cache:'no-store'}),x=await r.json();$('lanState').textContent=x.ethernet?.connected?(x.ethernet.internet?'VERBUNDEN · INTERNET':'VERBUNDEN'):'NICHT VERBUNDEN'}catch{$('lanState').textContent='NICHT ERKANNT'}}
async function scan(){setMsg('WLAN-Suche läuft…');try{const r=await fetch('/api/setup/networks',{cache:'no-store'}),x=await r.json();if(!r.ok)throw new Error(x.detail||'WLAN-Suche fehlgeschlagen');const s=$('ssid'),old=s.value;s.innerHTML='<option value="">Netzwerk wählen…</option>'+(x.networks||[]).map(n=>`<option value="${String(n.ssid).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;')}">${n.ssid} · ${n.signal}% ${n.security||''}</option>`).join('');if(old)s.value=old;setMsg(x.message||((x.networks||[]).length+' WLAN-Netze gefunden.'),'ok')}catch(e){setMsg(e.message,'error')}}$('scan').addEventListener('click',scan);
$('setupForm').addEventListener('submit',async e=>{e.preventDefault();if($('systemPassword').value!==$('systemPassword2').value){setMsg('Die beiden System-/SSH-Passwörter stimmen nicht überein.','error');return}const m=document.querySelector('input[name=mode]:checked').value;if(m==='wifi'&&!$('ssid').value){setMsg('Bitte ein WLAN auswählen.','error');return}setMsg('Einrichtung wird gespeichert und geprüft…');const body={mode:m,timezone:'Europe/Berlin',ssid:m==='wifi'?$('ssid').value:'',wifi_password:m==='wifi'?$('wifiPassword').value:'',new_password:$('systemPassword').value,gui_username:$('guiUser').value.trim(),gui_password:$('guiPassword').value,fritz_enabled:false,fritz_host:'',fritz_username:'',fritz_password:''};try{const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),x=await r.json();if(!r.ok)throw new Error(x.detail||'Setup fehlgeschlagen');setMsg('Daten übernommen. Grow Central prüft jetzt die Konfiguration. Der Setup-Hotspot kann gleich beendet werden.','ok');setTimeout(()=>location.href='http://135er-GrowCentral.local/',5000)}catch(e){setMsg(e.message,'error')}});status();
</script></body></html>'''


class SetupPortalMiddleware(BaseHTTPMiddleware):
    """Serve captive-portal probes and setup API before GUI authentication."""

    async def dispatch(self, request: Request, call_next):
        if not firstboot.setup_active():
            return await call_next(request)

        path = request.url.path
        if path == "/setup" or path == "/":
            return HTMLResponse(SETUP_HTML)

        if path in {
            "/hotspot-detect.html", "/library/test/success.html",  # Apple
            "/generate_204", "/gen_204",                         # Android
            "/connecttest.txt", "/ncsi.txt",                     # Windows
            "/canonical.html", "/success.txt",
        }:
            return RedirectResponse("/setup", status_code=302)

        if path == "/api/setup/status" and request.method == "GET":
            return JSONResponse(await firstboot.status())
        if path == "/api/setup/network-status" and request.method == "GET":
            try:
                return JSONResponse(await firstboot.network_status())
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                detail = getattr(exc, "detail", str(exc))
                return JSONResponse({"detail": detail}, status_code=status_code)
        if path == "/api/setup/networks" and request.method == "GET":
            try:
                return JSONResponse(await firstboot.networks())
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                detail = getattr(exc, "detail", str(exc))
                return JSONResponse({"detail": detail}, status_code=status_code)
        if path == "/api/setup" and request.method == "POST":
            try:
                payload = await request.json()
                body = firstboot.SetupBody.model_validate(payload)
                return JSONResponse(await firstboot.apply(body))
            except Exception as exc:
                status_code = getattr(exc, "status_code", 422)
                detail = getattr(exc, "detail", str(exc))
                return JSONResponse({"detail": detail}, status_code=status_code)

        return await call_next(request)
