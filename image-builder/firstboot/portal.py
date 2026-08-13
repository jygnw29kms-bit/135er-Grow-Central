#!/usr/bin/env python3
"""First-boot HTTPS provisioning portal for 135er-Grow Central."""

from __future__ import annotations

import html
import http.cookies
import http.server
import json
import os
import re
import secrets
import ssl
import subprocess
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

try:
    import PAM
except ImportError:  # allows validation tests outside the Raspberry Pi image
    PAM = None


SETUP_IP = "10.42.0.1"
SETUP_SSID_PREFIX = "135er-GrowCentral-Setup-"
DEFAULT_USERNAME = "GrowCentral"
DEFAULT_PASSWORD = "grow-central-test"
STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
CERT_FILE = Path("/etc/135er-grow-central/setup-portal.crt")
KEY_FILE = Path("/etc/135er-grow-central/setup-portal.key")
USERNAME = DEFAULT_USERNAME
MAX_BODY = 16_384
SESSION_TTL = 15 * 60
TIMEZONES = ("Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich")
HOSTNAME_RE = re.compile(r"(?=^.{1,63}$)^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")


@dataclass
class Session:
    csrf: str
    expires: float


@dataclass
class LoginGuard:
    failures: dict[str, list[float]] = field(default_factory=dict)

    def allowed(self, address: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        recent = [stamp for stamp in self.failures.get(address, []) if current - stamp < 60]
        self.failures[address] = recent
        return len(recent) < 5

    def failed(self, address: str, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        self.failures.setdefault(address, []).append(current)

    def clear(self, address: str) -> None:
        self.failures.pop(address, None)


SESSIONS: dict[str, Session] = {}
GUARD = LoginGuard()


def validate_setup(form: dict[str, str]) -> tuple[dict[str, str] | None, str | None]:
    mode = form.get("mode", "wifi")
    hostname = form.get("hostname", "135er-grow-central").strip().lower()
    timezone = form.get("timezone", "Europe/Berlin")
    password = form.get("new_password", "")
    confirmation = form.get("new_password_confirm", "")
    ssid = (form.get("manual_ssid", "").strip() or form.get("ssid", "").strip())
    wifi_password = form.get("wifi_password", "")

    if mode not in {"wifi", "ethernet"}:
        return None, "Ungültiger Netzwerkmodus."
    if not HOSTNAME_RE.fullmatch(hostname):
        return None, "Der Hostname ist ungültig."
    if timezone not in TIMEZONES:
        return None, "Die Zeitzone ist nicht freigegeben."
    if len(password) < 12 or password != confirmation:
        return None, "Das neue GrowCentral-Passwort muss übereinstimmen und mindestens 12 Zeichen haben."
    if mode == "wifi":
        if not 1 <= len(ssid.encode("utf-8")) <= 32:
            return None, "Die WLAN-SSID muss 1 bis 32 Byte lang sein."
        if wifi_password and not 8 <= len(wifi_password) <= 63:
            return None, "Das WLAN-Passwort muss 8 bis 63 Zeichen haben oder leer bleiben."

    return {
        "mode": mode,
        "hostname": hostname,
        "timezone": timezone,
        "ssid": ssid,
        "wifi_password": wifi_password,
        "new_password": password,
    }, None


def _nmcli_fields(line: str) -> list[str]:
    fields, current, escaped = [], [], False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def scan_networks() -> list[tuple[str, str, str]]:
    subprocess.run(["nmcli", "device", "wifi", "rescan", "ifname", "wlan0"], capture_output=True, text=True, timeout=20, check=False)
    result = subprocess.run(["nmcli", "-t", "-e", "yes", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", "wlan0", "--rescan", "auto"], capture_output=True, text=True, timeout=20, check=False)
    networks: dict[str, tuple[str, str, str]] = {}
    for raw_line in result.stdout.splitlines():
        parts = _nmcli_fields(raw_line)
        if len(parts) != 3 or not parts[0].strip():
            continue
        ssid, signal, security = (part.strip() for part in parts)
        if not signal.isdecimal():
            continue
        previous = networks.get(ssid)
        if previous is None or int(signal or "0") > int(previous[1] or "0"):
            networks[ssid] = (ssid, signal or "0", security or "OFFEN")
    return sorted(networks.values(), key=lambda item: int(item[1]), reverse=True)


def authenticate_user(username: str, password: str) -> bool:
    if PAM is None or not secrets.compare_digest(username, USERNAME):
        return False

    def conversation(_auth: object, queries: list[tuple[str, int]], _data: object) -> list[tuple[str, int]]:
        answers = []
        for _prompt, kind in queries:
            if kind == PAM.PAM_PROMPT_ECHO_ON:
                answers.append((USERNAME, 0))
            elif kind == PAM.PAM_PROMPT_ECHO_OFF:
                answers.append((password, 0))
            else:
                answers.append(("", 0))
        return answers

    try:
        client = PAM.pam()
        client.start("login")
        client.set_item(PAM.PAM_USER, USERNAME)
        client.set_item(PAM.PAM_CONV, conversation)
        client.authenticate()
        return True
    except Exception:
        return False


def page(title: str, content: str) -> bytes:
    document = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>
:root{{--bg:#02070a;--panel:#061319;--panel2:#081c23;--line:#17414a;--cyan:#2ae5ff;--green:#71ff3b;--text:#edfdf9;--muted:#7e9aa1;--red:#ff5161}}
*{{box-sizing:border-box}}html{{background:var(--bg)}}body{{margin:0;min-height:100vh;padding:clamp(10px,3vw,34px);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 78% 4%,rgba(42,229,255,.15),transparent 28%),radial-gradient(circle at 12% 78%,rgba(113,255,59,.07),transparent 25%),linear-gradient(rgba(42,229,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(42,229,255,.025) 1px,transparent 1px),#02070a;background-size:auto,auto,34px 34px,34px 34px}}
.shell{{width:min(980px,100%);margin:auto;border:1px solid rgba(42,229,255,.28);background:linear-gradient(145deg,rgba(6,19,25,.98),rgba(2,9,12,.98));box-shadow:0 32px 100px #000,0 0 40px rgba(42,229,255,.06);clip-path:polygon(0 0,calc(100% - 24px) 0,100% 24px,100% 100%,24px 100%,0 calc(100% - 24px))}}
header{{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px clamp(18px,4vw,38px);border-bottom:1px solid var(--line);background:linear-gradient(90deg,rgba(42,229,255,.06),transparent 55%)}}.identity{{display:flex;align-items:center;gap:15px}}.emblem{{width:50px;height:56px;display:grid;place-items:center;color:var(--green);font:800 13px Consolas,monospace;border:2px solid var(--green);clip-path:polygon(50% 0,100% 24%,100% 76%,50% 100%,0 76%,0 24%);box-shadow:inset 0 0 18px rgba(113,255,59,.15)}}.brand{{font-size:clamp(1.15rem,3.5vw,1.85rem);font-weight:800;letter-spacing:-.035em}}.brand span{{color:var(--green)}}.brand small{{display:block;color:var(--muted);font:10px Consolas,monospace;letter-spacing:.2em;margin-top:4px}}.live{{display:flex;align-items:center;gap:9px;color:var(--cyan);font:11px Consolas,monospace;letter-spacing:.12em}}.live i{{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 14px var(--green)}}
.rail{{display:grid;grid-template-columns:repeat(3,1fr);border-bottom:1px solid var(--line)}}.rail span{{padding:11px 16px;color:#52747c;font:10px Consolas,monospace;letter-spacing:.14em;border-right:1px solid var(--line)}}.rail span:last-child{{border:0}}.rail b{{color:var(--cyan);margin-right:7px}}
main{{padding:clamp(24px,5vw,52px)}}.content{{position:relative}}.content:before{{content:"";position:absolute;right:0;top:0;width:100px;height:1px;background:var(--green);box-shadow:0 0 15px var(--green)}}
.kicker,label,small,.eyebrow{{font-family:Consolas,monospace}}.kicker{{display:inline-flex;align-items:center;gap:9px;color:var(--cyan);letter-spacing:.16em;font-size:.72rem}}.kicker:before{{content:"";width:24px;height:1px;background:var(--cyan)}}h1{{font-size:clamp(2.25rem,7vw,4.8rem);line-height:.94;letter-spacing:-.055em;margin:16px 0 20px;max-width:800px}}h1 em{{font-style:normal;color:var(--green)}}h2{{font-size:1rem;letter-spacing:.08em;margin:0 0 13px}}p{{color:#a8bdc1;line-height:1.65;max-width:760px}}
.hud-card{{border:1px solid var(--line);background:linear-gradient(135deg,rgba(8,28,35,.92),rgba(3,12,16,.96));padding:clamp(16px,3vw,26px);clip-path:polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,12px 100%,0 calc(100% - 12px))}}.default-access{{margin:18px 0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}.default-access div{{border:1px solid var(--line);background:#031014;padding:13px}}.default-access span{{display:block;color:var(--muted);font:10px Consolas,monospace;letter-spacing:.08em}}.default-access strong{{display:block;color:var(--green);font:700 14px Consolas,monospace;margin-top:4px;word-break:break-word}}form{{display:grid;gap:18px;margin-top:26px}}.field-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}label{{display:grid;gap:8px;color:var(--cyan);font-size:.72rem;letter-spacing:.1em}}input,select{{width:100%;padding:14px 15px;border:1px solid #17414a;background:#020a0e;color:var(--text);font:1rem Consolas,monospace;transition:.2s}}input:focus,select:focus{{outline:none;border-color:var(--green);box-shadow:0 0 0 2px rgba(113,255,59,.08),0 0 22px rgba(113,255,59,.08)}}
.choice{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.choice label{{display:flex;align-items:center;gap:10px;padding:15px;border:1px solid var(--line);background:#041116;cursor:pointer}}.choice input{{width:auto;accent-color:var(--green)}}button,.refresh{{padding:15px 18px;border:1px solid var(--green);background:linear-gradient(90deg,var(--green),#9cff72);color:#041006;font-weight:850;letter-spacing:.06em;cursor:pointer;box-shadow:0 0 24px rgba(113,255,59,.12)}}.refresh{{display:inline-block;text-decoration:none;margin:5px 0 12px;font:700 11px Consolas,monospace;padding:10px 13px;background:transparent;color:var(--green)}}
.notice{{padding:15px 17px;border-left:3px solid var(--cyan);background:rgba(4,17,22,.9);color:#a8bdc1}}.error{{border-color:var(--red);color:#ff929c}}.status{{color:var(--green)}}.network-list{{display:grid;gap:9px;border:0;padding:0;margin:0;max-height:330px;overflow:auto}}.network{{display:grid;grid-template-columns:auto 1fr auto;gap:13px;align-items:center;padding:13px 14px;border:1px solid var(--line);background:rgba(2,10,14,.8);color:var(--text);font-size:.86rem;cursor:pointer}}.network:hover{{border-color:var(--cyan);background:rgba(42,229,255,.045)}}.network input{{width:auto;accent-color:var(--green)}}.network small{{color:var(--muted);text-align:right}}.signal{{height:4px;background:#10252b;margin-top:7px}}.signal span{{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green));box-shadow:0 0 8px var(--green)}}details{{border:1px solid var(--line);padding:14px;background:#031014}}summary{{color:var(--cyan);cursor:pointer;font:12px Consolas,monospace}}details label{{margin-top:14px}}footer{{display:flex;justify-content:space-between;gap:15px;padding:14px clamp(18px,4vw,38px);border-top:1px solid var(--line);color:#52747c;font:9px Consolas,monospace;letter-spacing:.12em}}
@media(max-width:640px){{body{{padding:7px}}header{{align-items:flex-start}}.live{{display:none}}.rail{{grid-template-columns:1fr}}.rail span{{border-right:0;border-bottom:1px solid var(--line)}}.field-grid,.choice,.default-access{{grid-template-columns:1fr}}main{{padding:24px 16px}}.network{{grid-template-columns:auto 1fr}}.network small{{grid-column:2;text-align:left}}footer{{flex-direction:column}}}}
</style></head><body><div class="shell"><header><div class="identity"><div class="emblem">J.L.</div><div class="brand">135er-<span>Grow</span> Central<small>LOCAL CORE · SECURE PROVISIONING</small></div></div><div class="live"><i></i> SETUP NODE ONLINE</div></header><div class="rail"><span><b>01</b>SECURE LINK</span><span><b>02</b>NETWORK UPLINK</span><span><b>03</b>LOCAL CORE</span></div><main><div class="content">{content}</div></main><footer><span>RASPBERRY PI · LOCAL-FIRST · SECURE</span><span>SETUP GATEWAY {SETUP_IP}</span></footer></div></body></html>"""
    return document.encode("utf-8")


class PortalHandler(http.server.BaseHTTPRequestHandler):
    server_version = "GrowCentralSetup/1.2"

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"portal {self.client_address[0]} {format_string % args}")

    def security_headers(self, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def send_page(self, status: int, body: bytes, cookie: str | None = None) -> None:
        self.send_response(status)
        self.security_headers()
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > MAX_BODY:
            raise ValueError("request too large")
        values = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        return {key: entries[-1] for key, entries in values.items()}

    def session(self) -> tuple[str | None, Session | None]:
        raw_cookie = self.headers.get("Cookie", "")
        cookie = http.cookies.SimpleCookie()
        cookie.load(raw_cookie)
        token = cookie.get("gc_setup_session")
        if not token:
            return None, None
        session_id = token.value
        current = SESSIONS.get(session_id)
        if not current or current.expires < time.monotonic():
            SESSIONS.pop(session_id, None)
            return None, None
        return session_id, current

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        if path not in {"/", "/setup"}:
            self.send_error(404)
            return
        _, session = self.session()
        if not session:
            content = f"""<span class="kicker">FIRST BOOT / AUTHENTICATION GATE</span><h1>Lokalen Core<br><em>aktivieren.</em></h1>
<p>Der Setup-Knoten läuft vollständig lokal auf diesem Raspberry Pi. Diese Zugangsdaten gelten nur für den ersten Start und müssen im Setup geändert werden.</p>
<div class="default-access"><div><span>SETUP WLAN</span><strong>{SETUP_SSID_PREFIX}XXXX</strong></div><div><span>SETUP ADRESSE</span><strong>https://{SETUP_IP}</strong></div><div><span>STANDARD-BENUTZER</span><strong>{DEFAULT_USERNAME}</strong></div><div><span>STANDARD-PASSWORT</span><strong>{DEFAULT_PASSWORD}</strong></div></div>
<p class="notice">Nach erfolgreichem Setup verwendest du das neu gesetzte GrowCentral-Passwort auch für SSH. Die spätere IP-Adresse erhält der Pi per DHCP; zusätzlich ist der konfigurierte Hostname über mDNS als <strong>&lt;hostname&gt;.local</strong> vorgesehen.</p>
<div class="hud-card"><h2>SECURE DEVICE LOGIN</h2><form method="post" action="/login"><div class="field-grid"><label>BENUTZER<input name="username" value="{DEFAULT_USERNAME}" autocomplete="username" required></label>
<label>GERÄTEPASSWORT<input type="password" name="password" value="{DEFAULT_PASSWORD}" autocomplete="current-password" required></label></div><button type="submit">SETUP-SITZUNG ÖFFNEN</button></form></div>"""
            self.send_page(200, page("Grow Central Setup", content))
            return

        networks = scan_networks()
        options = "".join(
            f'<label class="network"><input type="radio" name="ssid" value="{html.escape(ssid, quote=True)}">'
            f'<span><strong>{html.escape(ssid)}</strong><div class="signal"><span style="width:{max(0, min(100, int(signal)))}%"></span></div></span>'
            f'<small>{html.escape(signal)}% · {html.escape(security)}</small></label>'
            for ssid, signal, security in networks
        ) or '<p class="notice">Keine WLANs gefunden. Bitte aktualisieren oder die SSID manuell eingeben.</p>'
        content = f"""<span class="kicker">LOCAL-FIRST / CONFIGURATION MATRIX</span><h1>System <em>einrichten.</em></h1>
<p class="notice">Nach erfolgreicher Prüfung wird der Setup-Zugangspunkt abgeschaltet und das Hauptsystem gestartet. Schlägt die WLAN-Verbindung fehl, erscheint der Zugangspunkt erneut.</p>
<div class="hud-card"><h2>01 · NETZWERK-UPLINK</h2><form method="post" action="/apply"><input type="hidden" name="csrf" value="{session.csrf}">
<div class="choice"><label><input type="radio" name="mode" value="wifi" checked> WLAN verwenden</label><label><input type="radio" name="mode" value="ethernet"> Nur LAN verwenden</label></div>
<div><label>VERFÜGBARE WLAN-NETZE</label><a class="refresh" href="/setup?refresh=1">NETZLISTE AKTUALISIEREN</a><fieldset class="network-list">{options}</fieldset></div>
<details><summary>Verstecktes oder nicht gefundenes WLAN</summary><label>SSID MANUELL EINGEBEN<input name="manual_ssid" maxlength="32"></label></details>
<label>WLAN-PASSWORT<input type="password" name="wifi_password" autocomplete="new-password" maxlength="63"></label>
<h2>02 · SYSTEMIDENTITÄT</h2><div class="field-grid"><label>HOSTNAME<input name="hostname" value="135er-grow-central" maxlength="63" required></label>
<label>ZEITZONE<select name="timezone">{''.join(f'<option value="{zone}">{zone}</option>' for zone in TIMEZONES)}</select></label></div>
<h2>03 · ZUGANG ABSICHERN</h2><div class="field-grid"><label>NEUES GROWCENTRAL-PASSWORT<input type="password" name="new_password" autocomplete="new-password" minlength="12" required></label>
<label>PASSWORT WIEDERHOLEN<input type="password" name="new_password_confirm" autocomplete="new-password" minlength="12" required></label></div>
<small>Mindestens 12 Zeichen. Dieses Passwort gilt danach für Benutzer, SSH und das Setup-Portal.</small>
<button type="submit">KONFIGURATION PRÜFEN UND CORE STARTEN</button></form></div>"""
        self.send_page(200, page("Grow Central einrichten", content))

    def do_POST(self) -> None:  # noqa: N802
        try:
            form = self.form()
        except (ValueError, UnicodeDecodeError):
            self.send_page(400, page("Ungültige Anfrage", '<p class="error">Die Anfrage ist ungültig.</p>'))
            return

        if self.path == "/login":
            address = self.client_address[0]
            if not GUARD.allowed(address):
                self.send_page(429, page("Anmeldung gesperrt", '<p class="error">Zu viele Versuche. Bitte 60 Sekunden warten.</p>'))
                return
            authenticated = authenticate_user(form.get("username", ""), form.get("password", ""))
            if not authenticated:
                GUARD.failed(address)
                self.send_page(401, page("Anmeldung fehlgeschlagen", '<p class="error">Benutzername oder Passwort ist falsch.</p><p><a href="/">Erneut versuchen</a></p>'))
                return
            GUARD.clear(address)
            session_id = secrets.token_urlsafe(32)
            SESSIONS[session_id] = Session(csrf=secrets.token_urlsafe(32), expires=time.monotonic() + SESSION_TTL)
            self.send_response(303)
            self.security_headers()
            self.send_header("Location", "/setup")
            self.send_header("Set-Cookie", f"gc_setup_session={session_id}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}")
            self.end_headers()
            return

        if self.path != "/apply":
            self.send_error(404)
            return
        session_id, session = self.session()
        if not session or not secrets.compare_digest(form.get("csrf", ""), session.csrf):
            self.send_page(403, page("Sitzung ungültig", '<p class="error">Die Sitzung ist abgelaufen. Bitte neu anmelden.</p>'))
            return
        setup, error = validate_setup(form)
        if error:
            self.send_page(400, page("Konfiguration ungültig", f'<p class="error">{html.escape(error)}</p><p><a href="/setup">Zurück zur Konfiguration</a></p>'))
            return

        STATE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
        temporary = PENDING_FILE.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(setup, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, PENDING_FILE)
        SESSIONS.pop(session_id or "", None)
        apply_unit = f"grow-central-apply-setup-{secrets.token_hex(6)}"
        started = subprocess.run(["systemd-run", f"--unit={apply_unit}", "--collect", "/usr/local/sbin/grow-central-apply-setup.py"], check=False, capture_output=True, text=True)
        if started.returncode != 0:
            PENDING_FILE.unlink(missing_ok=True)
            self.send_page(503, page("Setup konnte nicht gestartet werden", '<p class="error">Die Konfiguration wurde nicht gestartet. Bitte erneut versuchen.</p><p><a href="/setup">Zurück zur Konfiguration</a></p>'))
            return
        content = """<span class="kicker status">CONFIGURATION ACCEPTED</span><h1>Wird übernommen.</h1>
<p>Der Pi prüft jetzt die Verbindung. Bei Erfolg wird dieser Zugangspunkt geschlossen und 135er-Grow Central gestartet.</p>
<p class="notice">Falls das Ziel-WLAN nicht erreichbar ist, erscheint <strong>135er-GrowCentral-Setup-XXXX</strong> automatisch wieder.</p>"""
        self.send_page(202, page("Konfiguration wird übernommen", content), "gc_setup_session=; Path=/; Secure; HttpOnly; Max-Age=0")


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(302)
        self.send_header("Location", f"https://{SETUP_IP}/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def log_message(self, format_string: str, *args: object) -> None:
        return


def main() -> None:
    redirect = http.server.ThreadingHTTPServer(("0.0.0.0", 80), RedirectHandler)  # nosec B104
    threading.Thread(target=redirect.serve_forever, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 443), PortalHandler)  # nosec B104
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(CERT_FILE, KEY_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
