"""Captive first-boot portal for the unprovisioned appliance."""
from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app import firstboot

CAPTIVE_DNS = Path("/etc/NetworkManager/dnsmasq-shared.d/90-grow-central-captive.conf")
AP_CONNECTION = "grow-central-setup-ap"
_cleanup_done = False


def _cleanup_captive_runtime() -> None:
    """Best-effort cleanup once provisioning has succeeded."""
    global _cleanup_done
    if _cleanup_done:
        return
    try:
        CAPTIVE_DNS.unlink(missing_ok=True)
    except OSError:
        pass
    for args in (
        ("nmcli", "connection", "modify", AP_CONNECTION, "connection.autoconnect", "no"),
        ("nmcli", "connection", "down", AP_CONNECTION),
    ):
        try:
            subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
    _cleanup_done = True


SETUP_HTML = r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#02070a"><meta name="color-scheme" content="dark"><title>135er Grow Central · Ersteinrichtung</title><style>
:root{--bg:#02070a;--panel:#071319;--line:#17414a;--cyan:#2ae5ff;--green:#71ff3b;--amber:#ffb52b;--text:#edfdf9;--muted:#7ea1a8;--red:#ff6877}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:radial-gradient(circle at 70% 0,#0b2630,#02070a 38%);color:var(--text);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}body{min-height:100vh;min-height:100dvh;padding:max(18px,env(safe-area-inset-top)) max(14px,env(safe-area-inset-right)) max(18px,env(safe-area-inset-bottom)) max(14px,env(safe-area-inset-left))}.wrap{width:min(780px,100%);margin:auto}.brand{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px}.brand img{width:min(280px,65vw);max-height:72px;object-fit:contain;object-position:left}.badge{border:1px solid var(--green);color:var(--green);padding:7px 9px;border-radius:999px;font-size:.67rem;font-weight:800;white-space:nowrap}.panel{border:1px solid var(--line);background:linear-gradient(145deg,rgba(7,25,31,.96),rgba(3,11,15,.98));border-radius:18px;padding:clamp(18px,4vw,30px);box-shadow:0 24px 80px rgba(0,0,0,.4)}.eyebrow{color:var(--cyan);font-size:.68rem;font-weight:800;letter-spacing:.17em}.panel h1{margin:8px 0 7px;font-size:clamp(1.8rem,7vw,3.1rem);line-height:1}.lead{color:var(--muted);line-height:1.5;margin:0 0 20px}.network-state,.mode,.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.network-state{margin-bottom:18px}.network-state div{border:1px solid var(--line);padding:12px;border-radius:10px}.network-state small{display:block;color:var(--muted)}.network-state strong{display:block;margin-top:4px;color:var(--cyan)}.mode{margin-bottom:16px}.mode label{margin:0}.mode input{position:absolute;opacity:0}.mode span{display:block;text-align:center;border:1px solid var(--line);border-radius:10px;padding:13px;cursor:pointer;font-weight:800}.mode input:checked+span{border-color:var(--green);color:var(--green);background:rgba(113,255,59,.08)}label{display:grid;gap:6px;color:#b8d2d5;font-size:.78rem;margin-bottom:12px}input,select{width:100%;min-width:0;padding:13px;border:1px solid var(--line);border-radius:9px;background:#020a0e;color:white;font-size:16px;outline:none}input:focus,select:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(42,229,255,.08)}.wifi-box,.access-box{border:1px solid rgba(42,229,255,.14);padding:14px;border-radius:12px;margin-bottom:14px}.wifi-actions{display:flex;gap:8px;align-items:end}.wifi-actions label{flex:1;margin:0}.access-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.access-title div strong{display:block;font-size:.9rem}.access-title div small{display:block;color:var(--muted);margin-top:3px}.toggle{display:flex;align-items:center;gap:8px;margin:0;white-space:nowrap}.toggle input{width:20px;height:20px;min-width:20px;accent-color:var(--green)}.ssh-fields[hidden]{display:none}.notice{border:1px solid rgba(255,181,43,.28);background:rgba(255,181,43,.06);color:#d8c08e;border-radius:10px;padding:10px 12px;font-size:.72rem;line-height:1.5;margin-bottom:14px}button{min-height:48px;border:1px solid var(--green);border-radius:9px;background:rgba(113,255,59,.1);color:var(--green);font-weight:900;padding:0 16px;cursor:pointer}.submit{width:100%;margin-top:8px}.msg{min-height:1.4em;color:var(--muted);font-size:.8rem;margin-top:12px}.msg.error{color:var(--red)}.msg.ok{color:var(--green)}.hint{font-size:.72rem;color:var(--muted);line-height:1.5;margin-top:12px}@media(max-width:620px){.grid,.network-state,.mode{grid-template-columns:1fr}.brand{align-items:flex-start}.badge{font-size:.58rem}.wifi-actions{display:grid}.access-title{align-items:flex-start;flex-direction:column}.panel{border-radius:14px;padding:18px 14px}}</style></head><body><main class="wrap"><header class="brand"><img src="/static/brand-logo.png" alt="135er Grow Central"><div class="badge">FIRST BOOT</div></header><section class="panel"><div class="eyebrow">135ER GROW CENTRAL · ERSTEINRICHTUNG</div><h1>System einrichten</h1><p class="lead">Dieses Gerät besitzt ab Werk kein bekanntes Benutzer- oder Gerätepasswort. Netzwerk und persönlicher Grow-Central-Zugang werden jetzt einmalig eingerichtet.</p><div class="notice">Der Setup-Hotspot ist nur während der Ersteinrichtung aktiv. Solange das Setup nicht abgeschlossen ist, sind normale Grow-Central-Funktionen und lokaler SSH-Zugriff gesperrt.</div><div class="network-state"><div><small>LAN / WIRED</small><strong id="lanState">wird geprüft…</strong></div><div><small>SETUP</small><strong>10.42.0.1</strong></div></div><form id="setupForm"><div class="mode"><label><input type="radio" name="mode" value="ethernet" checked><span>WIRED / LAN</span></label><label><input type="radio" name="mode" value="wifi"><span>WLAN / WIFI</span></label></div><div id="wifiBox" class="wifi-box" hidden><div class="wifi-actions"><label>WLAN auswählen<select id="ssid"><option value="">Netzwerk wählen…</option></select></label><button type="button" id="scan">SUCHEN</button></div><label>WLAN-Passwort<input id="wifiPassword" type="password" autocomplete="new-password"></label></div><div class="access-box"><div class="access-title"><div><strong>Zugang zu Grow Central</strong><small>Diese Daten schützen die Weboberfläche nach Abschluss der Einrichtung.</small></div></div><div class="grid"><label>Benutzername<input id="guiUser" autocomplete="username" required minlength="3" maxlength="32" placeholder="z. B. admin"></label><span></span><label>Passwort<input id="guiPassword" type="password" autocomplete="new-password" required minlength="12" placeholder="mindestens 12 Zeichen"></label><label>Passwort wiederholen<input id="guiPassword2" type="password" autocomplete="new-password" required minlength="12"></label></div></div><div class="access-box"><div class="access-title"><div><strong>Erweiterter Systemzugriff</strong><small>Für den normalen Betrieb nicht erforderlich.</small></div><label class="toggle"><input id="sshEnabled" type="checkbox"><span>SSH aktivieren</span></label></div><div id="sshFields" class="ssh-fields" hidden><div class="grid"><label>System-/SSH-Passwort<input id="systemPassword" type="password" autocomplete="new-password" minlength="12" placeholder="mindestens 12 Zeichen"></label><label>System-/SSH-Passwort wiederholen<input id="systemPassword2" type="password" autocomplete="new-password" minlength="12"></label></div><div class="hint">SSH wird nur aktiviert, wenn diese Option gewählt ist. Andernfalls bleibt das lokale Systemkonto gesperrt und der SSH-Dienst deaktiviert.</div></div></div><button class="submit" id="submitBtn" type="submit">EINRICHTUNG SPEICHERN & PRÜFEN</button><div id="msg" class="msg" role="status" aria-live="polite"></div><div class="hint">Hostname nach der Einrichtung: <b>135er-GrowCentral.local</b>. Es gibt kein werkseitiges Standardpasswort.</div></form></section></main><script>
const $=id=>document.getElementById(id),msg=$('msg');const sleep=ms=>new Promise(r=>setTimeout(r,ms));function setMsg(t,c=''){msg.textContent=t;msg.className='msg '+c}function selectedMode(){return document.querySelector('input[name=mode]:checked').value}function mode(){const wifi=selectedMode()==='wifi';$('wifiBox').hidden=!wifi;if(wifi)scan()}document.querySelectorAll('input[name=mode]').forEach(x=>x.addEventListener('change',mode));
function sshMode(){const enabled=$('sshEnabled').checked;$('sshFields').hidden=!enabled;$('systemPassword').required=enabled;$('systemPassword2').required=enabled;if(!enabled){$('systemPassword').value='';$('systemPassword2').value=''}}$('sshEnabled').addEventListener('change',sshMode);
async function status(){try{const r=await fetch('/api/setup/network-status',{cache:'no-store'}),x=await r.json();$('lanState').textContent=x.ethernet?.connected?(x.ethernet.internet?'VERBUNDEN · INTERNET':'VERBUNDEN'):'NICHT VERBUNDEN'}catch{$('lanState').textContent='NICHT ERKANNT'}}
function option(ssid,signal,security){const o=document.createElement('option');o.value=ssid;o.textContent=ssid?`${ssid} · ${signal}% ${security||''}`:'Netzwerk wählen…';return o}async function scan(){setMsg('WLAN-Suche läuft…');try{const r=await fetch('/api/setup/networks',{cache:'no-store'}),x=await r.json();if(!r.ok)throw new Error(x.detail||'WLAN-Suche fehlgeschlagen');const s=$('ssid'),old=s.value;s.replaceChildren(option('','',''));for(const n of (x.networks||[]))s.append(option(String(n.ssid||''),String(n.signal||''),String(n.security||'')));if(old)s.value=old;setMsg(x.message||`${(x.networks||[]).length} WLAN-Netze gefunden.`,'ok')}catch(e){setMsg(e.message,'error')}}$('scan').addEventListener('click',scan);
async function waitForCompletion(){for(let attempt=0;attempt<90;attempt++){await sleep(2000);try{const r=await fetch('/api/setup/status',{cache:'no-store'});if(r.status===401||r.status===403){setMsg('Einrichtung abgeschlossen. Öffne Grow Central…','ok');location.href='http://135er-GrowCentral.local/';return}const x=await r.json();if(x.error)throw new Error(x.error);if(x.setup_required===false){setMsg('Einrichtung abgeschlossen. Öffne Grow Central…','ok');location.href='http://135er-GrowCentral.local/';return}setMsg(x.pending?'Konfiguration wird angewendet…':'System und Netzwerk werden geprüft…')}catch(e){if(e instanceof TypeError)continue;throw e}}throw new Error('Die Einrichtung wurde nicht rechtzeitig abgeschlossen. Bitte Verbindung zum Setup-WLAN prüfen und erneut versuchen.')}
$('setupForm').addEventListener('submit',async e=>{e.preventDefault();if($('guiPassword').value!==$('guiPassword2').value){setMsg('Die beiden Grow-Central-Passwörter stimmen nicht überein.','error');return}const ssh=$('sshEnabled').checked;if(ssh&&$('systemPassword').value!==$('systemPassword2').value){setMsg('Die beiden System-/SSH-Passwörter stimmen nicht überein.','error');return}const m=selectedMode();if(m==='wifi'&&!$('ssid').value){setMsg('Bitte ein WLAN auswählen.','error');return}$('submitBtn').disabled=true;setMsg('Einrichtung wird gespeichert…');const body={mode:m,timezone:'Europe/Berlin',ssid:m==='wifi'?$('ssid').value:'',wifi_password:m==='wifi'?$('wifiPassword').value:'',gui_username:$('guiUser').value.trim(),gui_password:$('guiPassword').value,ssh_enabled:ssh,new_password:ssh?$('systemPassword').value:'',fritz_enabled:false,fritz_host:'',fritz_username:'',fritz_password:''};try{const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),x=await r.json();if(!r.ok)throw new Error(x.detail||'Setup fehlgeschlagen');setMsg('Daten übernommen. Netzwerk und Dienste werden jetzt geprüft…','ok');await waitForCompletion()}catch(e){setMsg(e.message,'error');$('submitBtn').disabled=false}});sshMode();status();
</script></body></html>'''


class SetupPortalMiddleware(BaseHTTPMiddleware):
    """Expose only provisioning surfaces until the appliance is provisioned."""

    async def dispatch(self, request: Request, call_next):
        if not firstboot.setup_active():
            _cleanup_captive_runtime()
            return await call_next(request)

        path = request.url.path
        if path in {"/setup", "/"}:
            return HTMLResponse(SETUP_HTML, headers={"Cache-Control": "no-store"})
        if path in {
            "/hotspot-detect.html", "/library/test/success.html",
            "/generate_204", "/gen_204", "/connecttest.txt", "/ncsi.txt",
            "/canonical.html", "/success.txt",
        }:
            return RedirectResponse("/setup", status_code=302)

        if path == "/api/setup/status" and request.method == "GET":
            return JSONResponse(await firstboot.status(), headers={"Cache-Control": "no-store"})
        if path == "/api/setup/network-status" and request.method == "GET":
            try:
                return JSONResponse(await firstboot.network_status())
            except Exception as exc:
                return JSONResponse({"detail": getattr(exc, "detail", str(exc))}, status_code=getattr(exc, "status_code", 500))
        if path == "/api/setup/networks" and request.method == "GET":
            try:
                return JSONResponse(await firstboot.networks())
            except Exception as exc:
                return JSONResponse({"detail": getattr(exc, "detail", str(exc))}, status_code=getattr(exc, "status_code", 500))
        if path == "/api/setup" and request.method == "POST":
            try:
                payload = await request.json()
                body = firstboot.SetupBody.model_validate(payload)
                return JSONResponse(await firstboot.apply(body))
            except Exception as exc:
                return JSONResponse({"detail": getattr(exc, "detail", str(exc))}, status_code=getattr(exc, "status_code", 422))

        # Runtime verification needs the health endpoint before the marker exists.
        if path == "/api/health" and request.method == "GET":
            return await call_next(request)
        # Branding assets are the only normal static resources required by the portal.
        if path in {"/static/brand-logo.png", "/static/brand-mark.png"} and request.method == "GET":
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                {"detail": "Ersteinrichtung erforderlich"},
                status_code=403,
                headers={"Cache-Control": "no-store"},
            )
        return RedirectResponse("/setup", status_code=302)
