#!/usr/bin/env python3
"""First-boot HTTPS provisioning portal for 135er-Grow Central."""
from __future__ import annotations

import html, http.cookies, http.server, json, os, re, secrets, ssl, subprocess, threading, time, urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

try:
    import PAM
except ImportError:
    PAM = None

SETUP_IP = "10.42.0.1"
SETUP_SSID_PREFIX = "135er-GrowCentral-Setup-"
DEFAULT_USERNAME = "GrowCentral"
DEFAULT_PASSWORD = "grow-central-test"
STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
CERT_FILE = Path("/etc/135er-grow-central/setup-portal.crt")
KEY_FILE = Path("/etc/135er-grow-central/setup-portal.key")
MAX_BODY = 32768
SESSION_TTL = 15 * 60
TIMEZONES = ("Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich")
HOSTNAME_RE = re.compile(r"(?=^.{1,63}$)^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")
GUI_USER_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")

@dataclass
class Session:
    csrf: str
    expires: float

@dataclass
class LoginGuard:
    failures: dict[str, list[float]] = field(default_factory=dict)
    def allowed(self, address: str) -> bool:
        now=time.monotonic(); rows=[x for x in self.failures.get(address,[]) if now-x<60]; self.failures[address]=rows; return len(rows)<5
    def failed(self,address:str)->None:self.failures.setdefault(address,[]).append(time.monotonic())
    def clear(self,address:str)->None:self.failures.pop(address,None)

SESSIONS: dict[str, Session] = {}
GUARD = LoginGuard()


def _run(args:list[str], timeout:int=8):
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)


def ethernet_connected() -> bool:
    try:
        result=_run(["nmcli","-t","-f","DEVICE,TYPE,STATE","device","status"])
    except (OSError,subprocess.TimeoutExpired):
        return False
    for line in result.stdout.splitlines():
        parts=line.split(":")
        if len(parts)>=3 and parts[1]=="ethernet" and parts[2] in {"connected","verbunden"}:
            return True
    return False


def _nmcli_fields(line:str)->list[str]:
    fields=[]; current=[]; escaped=False
    for ch in line:
        if escaped: current.append(ch); escaped=False
        elif ch=="\\": escaped=True
        elif ch==":": fields.append("".join(current)); current=[]
        else: current.append(ch)
    fields.append("".join(current)); return fields


def scan_networks()->tuple[list[tuple[str,str,str]],str|None]:
    try:
        _run(["nmcli","device","wifi","rescan","ifname","wlan0"],20)
        result=_run(["nmcli","-t","-e","yes","-f","SSID,SIGNAL,SECURITY","device","wifi","list","ifname","wlan0","--rescan","auto"],20)
    except subprocess.TimeoutExpired:
        return [],"WLAN-Suche hat das Zeitlimit überschritten."
    except OSError:
        return [],"NetworkManager/nmcli ist nicht verfügbar."
    if result.returncode!=0:
        return [],(result.stderr or "WLAN-Suche fehlgeschlagen.").strip()[:180]
    found={}
    for line in result.stdout.splitlines():
        p=_nmcli_fields(line)
        if len(p)!=3 or not p[0].strip(): continue
        ssid,signal,security=(x.strip() for x in p)
        if not signal.isdigit(): continue
        row=(ssid,signal,security or "OFFEN")
        if ssid not in found or int(signal)>int(found[ssid][1]): found[ssid]=row
    return sorted(found.values(),key=lambda r:int(r[1]),reverse=True),None


def validate_setup(form:dict[str,str])->tuple[dict[str,str]|None,str|None]:
    lan=ethernet_connected()
    mode="ethernet" if lan else form.get("mode","wifi")
    hostname=form.get("hostname","135er-grow-central").strip().lower()
    timezone=form.get("timezone","Europe/Berlin")
    system_password=form.get("new_password","")
    system_confirm=form.get("new_password_confirm","")
    ssid=(form.get("manual_ssid","").strip() or form.get("ssid","").strip())
    wifi_password=form.get("wifi_password","")
    gui_username=form.get("gui_username","").strip()
    gui_password=form.get("gui_password","")
    gui_confirm=form.get("gui_password_confirm","")
    fritz_enabled=form.get("fritz_enabled")=="1"
    fritz_host=form.get("fritz_host","fritz.box").strip() or "fritz.box"
    fritz_username=form.get("fritz_username","").strip()
    fritz_password=form.get("fritz_password","")

    if len(system_password)<12 or system_password!=system_confirm:
        return None,"Das neue GrowCentral-Systempasswort ist Pflicht, muss übereinstimmen und mindestens 12 Zeichen haben."
    if not HOSTNAME_RE.fullmatch(hostname): return None,"Ungültiger Hostname."
    if timezone not in TIMEZONES:return None,"Ungültige Zeitzone."
    if mode=="wifi":
        if not 1<=len(ssid.encode("utf-8"))<=32:return None,"Bitte ein WLAN aus der Liste wählen oder eine SSID eingeben."
        if wifi_password and not 8<=len(wifi_password)<=63:return None,"Das WLAN-Passwort muss 8 bis 63 Zeichen haben oder leer sein."
    if not GUI_USER_RE.fullmatch(gui_username):return None,"GUI-Benutzername: 3 bis 32 Zeichen, nur Buchstaben, Zahlen, Punkt, Unterstrich oder Bindestrich."
    if len(gui_password)<12 or gui_password!=gui_confirm:return None,"Das GUI-Passwort ist Pflicht, muss übereinstimmen und mindestens 12 Zeichen haben."
    if fritz_enabled and (not fritz_username or not fritz_password):return None,"Für die FRITZ!Box bitte Benutzer und Passwort des eigens angelegten GrowCentral-FRITZ!-Benutzers eingeben."

    return {
        "mode":mode,"hostname":hostname,"timezone":timezone,"ssid":ssid,"wifi_password":wifi_password,
        "new_password":system_password,"gui_username":gui_username,"gui_password":gui_password,
        "fritz_enabled":"1" if fritz_enabled else "0","fritz_host":fritz_host if fritz_enabled else "",
        "fritz_username":fritz_username if fritz_enabled else "","fritz_password":fritz_password if fritz_enabled else "",
    },None


def authenticate_user(username:str,password:str)->bool:
    if PAM is None or not secrets.compare_digest(username,DEFAULT_USERNAME):return False
    def conversation(_auth,queries,_data):
        return [(DEFAULT_USERNAME if kind==PAM.PAM_PROMPT_ECHO_ON else password if kind==PAM.PAM_PROMPT_ECHO_OFF else "",0) for _prompt,kind in queries]
    try:
        client=PAM.pam(); client.start("login"); client.set_item(PAM.PAM_USER,DEFAULT_USERNAME); client.set_item(PAM.PAM_CONV,conversation); client.authenticate(); return True
    except Exception:return False


def page(title:str,content:str)->bytes:
    return f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
:root{{--bg:#02070a;--panel:#061319;--line:#17414a;--cyan:#2ae5ff;--green:#71ff3b;--text:#edfdf9;--muted:#7e9aa1;--red:#ff5161}}*{{box-sizing:border-box}}body{{margin:0;padding:18px;background:#02070a;color:var(--text);font-family:Arial,sans-serif}}.shell{{max-width:980px;margin:auto;border:1px solid var(--line);background:var(--panel)}}header,main,footer{{padding:22px}}header{{border-bottom:1px solid var(--line)}}h1{{margin:.25em 0;font-size:clamp(2rem,6vw,4rem)}}h2{{margin-top:28px;color:var(--cyan)}}p,small{{color:#a8bdc1}}.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}.steps div,.card{{border:1px solid var(--line);padding:14px;background:#031014}}.steps b{{color:var(--green)}}form{{display:grid;gap:14px}}label{{display:grid;gap:6px;color:var(--cyan);font:12px monospace}}input,select{{width:100%;padding:12px;background:#020a0e;border:1px solid var(--line);color:var(--text)}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.network-list{{display:grid;gap:8px;max-height:280px;overflow:auto}}.network{{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;border:1px solid var(--line);padding:10px}}button,.btn{{padding:14px;border:1px solid var(--green);background:var(--green);color:#041006;font-weight:800;cursor:pointer}}.notice{{border-left:3px solid var(--cyan);padding:12px;background:#031014}}.ok{{color:var(--green)}}.error{{color:#ff8c98}}details{{border:1px solid var(--line);padding:12px}}@media(max-width:700px){{.steps,.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class="shell"><header><strong>135er-Grow Central · FIRST BOOT</strong><h1>Sicher einrichten.</h1><div class="steps"><div><b>01</b><br>Passwort</div><div><b>02</b><br>Netzwerk</div><div><b>03</b><br>FRITZ!</div><div><b>04</b><br>GUI Login</div></div></header><main>{content}</main><footer>Setup: https://{SETUP_IP} · Default: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}</footer></div></body></html>'''.encode()


class PortalHandler(http.server.BaseHTTPRequestHandler):
    server_version="GrowCentralSetup/2.0"
    def log_message(self,fmt,*args):print(f"portal {self.client_address[0]} {fmt%args}")
    def security_headers(self):
        self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("X-Frame-Options","DENY"); self.send_header("Referrer-Policy","no-referrer")
    def send_page(self,status:int,body:bytes,cookie:str|None=None):
        self.send_response(status); self.security_headers();
        if cookie:self.send_header("Set-Cookie",cookie)
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def form(self):
        length=int(self.headers.get("Content-Length","0"));
        if length<0 or length>MAX_BODY:raise ValueError("request too large")
        values=urllib.parse.parse_qs(self.rfile.read(length).decode(),keep_blank_values=True); return {k:v[-1] for k,v in values.items()}
    def session(self):
        cookie=http.cookies.SimpleCookie(); cookie.load(self.headers.get("Cookie","")); token=cookie.get("gc_setup_session")
        if not token:return None,None
        row=SESSIONS.get(token.value)
        if not row or row.expires<time.monotonic():SESSIONS.pop(token.value,None);return None,None
        return token.value,row
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path not in {"/","/setup"}:self.send_error(404);return
        _,session=self.session()
        if not session:
            body=page("Grow Central Setup",f'''<p class="notice">Beim ersten Start müssen die Standard-Zugangsdaten geändert werden.</p><div class="grid"><div class="card"><small>SETUP WLAN</small><br><b>{SETUP_SSID_PREFIX}XXXX</b></div><div class="card"><small>SETUP ADRESSE</small><br><b>https://{SETUP_IP}</b></div><div class="card"><small>BENUTZER</small><br><b>{DEFAULT_USERNAME}</b></div><div class="card"><small>PASSWORT</small><br><b>{DEFAULT_PASSWORD}</b></div></div><form method="post" action="/login"><label>Benutzer<input name="username" value="{DEFAULT_USERNAME}" required></label><label>Temporäres Passwort<input type="password" name="password" value="{DEFAULT_PASSWORD}" required></label><button>SETUP STARTEN</button></form>'''); self.send_page(200,body);return
        lan=ethernet_connected(); networks,scan_error=scan_networks()
        opts="".join(f'<label class="network"><input type="radio" name="ssid" value="{html.escape(s,quote=True)}"><span>{html.escape(s)}</span><small>{sig}% · {html.escape(sec)}</small></label>' for s,sig,sec in networks)
        netinfo='<p class="notice ok">LAN-Verbindung erkannt. WLAN ist optional und wird für den Abschluss nicht benötigt.</p>' if lan else '<p class="notice">Kein aktives LAN erkannt. Bitte WLAN auswählen.</p>'
        scanf=f'<p class="error">{html.escape(scan_error)}</p>' if scan_error else f'<p>{len(networks)} WLAN-Netzwerk(e) gefunden.</p>'
        body=page("Grow Central einrichten",f'''<form method="post" action="/apply"><input type="hidden" name="csrf" value="{session.csrf}">
<h2>1 · Systempasswort ändern (Pflicht)</h2><div class="grid"><label>Neues GrowCentral-Passwort<input type="password" name="new_password" minlength="12" required></label><label>Wiederholen<input type="password" name="new_password_confirm" minlength="12" required></label></div><small>Dieses Passwort schützt Systembenutzer und SSH.</small>
<h2>2 · Heimnetzwerk</h2>{netinfo}<input type="hidden" name="mode" value="{'ethernet' if lan else 'wifi'}">{scanf}<div class="network-list">{opts}</div><details><summary>SSID manuell eingeben</summary><label>SSID<input name="manual_ssid" maxlength="32"></label></details><label>WLAN-Passwort<input type="password" name="wifi_password" maxlength="63"></label>
<h2>3 · FRITZ!Box / FRITZ!SmartHome (optional)</h2><p>Wenn eine FRITZ!Box verwendet wird, bitte dort vorher einen eigenen Benutzer <b>GrowCentral</b> mit den nötigen Smart-Home-Rechten anlegen. Grow Central verwendet diese Daten nur lokal.</p><label><input type="checkbox" name="fritz_enabled" value="1"> FRITZ!Box verwenden</label><div class="grid"><label>FRITZ!Box Adresse<input name="fritz_host" value="fritz.box"></label><label>FRITZ!-Benutzer<input name="fritz_username" value="GrowCentral"></label></div><label>FRITZ!-Passwort<input type="password" name="fritz_password"></label>
<h2>4 · Grow-Central-GUI absichern (Pflicht)</h2><div class="grid"><label>GUI-Benutzername<input name="gui_username" value="GrowCentral" minlength="3" maxlength="32" required></label><label>GUI-Passwort<input type="password" name="gui_password" minlength="12" required></label></div><label>GUI-Passwort wiederholen<input type="password" name="gui_password_confirm" minlength="12" required></label><small>Dieser Login schützt die lokale GUI und API vor fremder Nutzung im LAN und bei späterem Remote-Zugriff.</small>
<h2>System</h2><div class="grid"><label>Hostname<input name="hostname" value="135er-grow-central" required></label><label>Zeitzone<select name="timezone">{''.join(f'<option>{z}</option>' for z in TIMEZONES)}</select></label></div><button>KONFIGURATION ABSCHLIESSEN</button></form>'''); self.send_page(200,body)
    def do_POST(self):
        try:form=self.form()
        except Exception:self.send_page(400,page("Fehler","<p class=\"error\">Ungültige Anfrage.</p>"));return
        if self.path=="/login":
            addr=self.client_address[0]
            if not GUARD.allowed(addr):self.send_page(429,page("Warten","<p>Zu viele Versuche.</p>"));return
            if not authenticate_user(form.get("username",""),form.get("password","")):GUARD.failed(addr);self.send_page(401,page("Fehler","<p class=\"error\">Anmeldung fehlgeschlagen.</p>"));return
            GUARD.clear(addr); token=secrets.token_urlsafe(32); SESSIONS[token]=Session(secrets.token_urlsafe(32),time.monotonic()+SESSION_TTL); self.send_response(303); self.security_headers(); self.send_header("Location","/setup"); self.send_header("Set-Cookie",f"gc_setup_session={token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}"); self.end_headers();return
        if self.path!="/apply":self.send_error(404);return
        token,session=self.session()
        if not session or not secrets.compare_digest(form.get("csrf",""),session.csrf):self.send_page(403,page("Fehler","<p class=\"error\">Sitzung abgelaufen.</p>"));return
        setup,error=validate_setup(form)
        if error:self.send_page(400,page("Konfiguration ungültig",f'<p class="error">{html.escape(error)}</p><p><a href="/setup">Zurück</a></p>'));return
        STATE_DIR.mkdir(mode=0o750,parents=True,exist_ok=True); temp=PENDING_FILE.with_suffix(".tmp"); fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,"w") as h:json.dump(setup,h);h.flush();os.fsync(h.fileno())
        os.replace(temp,PENDING_FILE); SESSIONS.pop(token or "",None)
        unit=f"grow-central-apply-setup-{secrets.token_hex(6)}"; started=_run(["systemd-run",f"--unit={unit}","--collect","/usr/local/sbin/grow-central-apply-setup.py"])
        if started.returncode!=0:PENDING_FILE.unlink(missing_ok=True);self.send_page(503,page("Fehler","<p class=\"error\">Setup konnte nicht gestartet werden.</p>"));return
        self.send_page(202,page("Setup läuft","<p class=\"notice ok\">Konfiguration akzeptiert. Netzwerk und GUI werden jetzt vorbereitet.</p>"),"gc_setup_session=; Path=/; Secure; HttpOnly; Max-Age=0")

class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):self.send_response(302);self.send_header("Location",f"https://{SETUP_IP}/");self.end_headers()
    def log_message(self,*args):return

def main():
    redirect=http.server.ThreadingHTTPServer(("0.0.0.0",80),RedirectHandler);threading.Thread(target=redirect.serve_forever,daemon=True).start();server=http.server.ThreadingHTTPServer(("0.0.0.0",443),PortalHandler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(CERT_FILE,KEY_FILE);server.socket=context.wrap_socket(server.socket,server_side=True);server.serve_forever()

if __name__=="__main__":main()
