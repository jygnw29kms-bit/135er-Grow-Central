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
    import pam
except ImportError:  # allows validation tests outside the Raspberry Pi image
    pam = None


SETUP_IP = "10.42.0.1"
STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
CERT_FILE = Path("/etc/135er-grow-central/setup-portal.crt")
KEY_FILE = Path("/etc/135er-grow-central/setup-portal.key")
USERNAME = "GrowCentral"
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
    hostname = form.get("hostname", "grow-central").strip().lower()
    timezone = form.get("timezone", "Europe/Berlin")
    password = form.get("new_password", "")
    confirmation = form.get("new_password_confirm", "")
    ssid = form.get("ssid", "").strip()
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


def scan_networks() -> list[tuple[str, str, str]]:
    result = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    networks: dict[str, tuple[str, str, str]] = {}
    for raw_line in result.stdout.splitlines():
        parts = raw_line.rsplit(":", 2)
        if len(parts) != 3 or not parts[0].strip():
            continue
        ssid, signal, security = (part.replace(r"\:", ":").strip() for part in parts)
        previous = networks.get(ssid)
        if previous is None or int(signal or "0") > int(previous[1] or "0"):
            networks[ssid] = (ssid, signal or "0", security or "OFFEN")
    return sorted(networks.values(), key=lambda item: int(item[1]), reverse=True)


def page(title: str, content: str) -> bytes:
    document = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>
:root{{--bg:#020608;--panel:#07171c;--line:#12313a;--cyan:#35e8da;--green:#71ff3b;--text:#edf8f6;--muted:#789096;--red:#ff4352}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;padding:24px;background:radial-gradient(circle at 70% 0,rgba(53,232,218,.1),transparent 35%),var(--bg);color:var(--text);font-family:Arial,sans-serif}}
main{{width:min(760px,100%);margin:auto;border:1px solid var(--line);background:linear-gradient(145deg,rgba(7,23,28,.98),rgba(2,10,13,.98));box-shadow:0 28px 80px #000;padding:clamp(22px,5vw,48px)}}
.brand{{font-size:clamp(1.6rem,5vw,2.7rem);font-weight:700;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:28px}}.brand span{{color:var(--green)}}
.kicker,label,small{{font-family:Consolas,monospace}}.kicker{{color:var(--cyan);letter-spacing:.1em;font-size:.78rem}}h1{{font-size:clamp(2rem,7vw,4rem);line-height:1;margin:12px 0 18px}}p{{color:#a6b8bb;line-height:1.6}}
form{{display:grid;gap:16px;margin-top:25px}}label{{display:grid;gap:7px;color:var(--cyan);font-size:.8rem}}input,select{{width:100%;padding:13px;border:1px solid var(--line);background:#02090c;color:var(--text);font:1rem Consolas,monospace}}input:focus,select:focus{{outline:2px solid var(--green);outline-offset:2px}}
.choice{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.choice label{{display:flex;align-items:center;padding:13px;border:1px solid var(--line)}}.choice input{{width:auto}}button{{padding:14px;border:1px solid #4abf2a;background:var(--green);color:#041006;font-weight:700;cursor:pointer}}.notice{{padding:13px;border-left:3px solid var(--cyan);background:#041116;color:#9fb5b9}}.error{{border-color:var(--red);color:#ff8991}}.status{{color:var(--green)}}
@media(max-width:540px){{body{{padding:10px}}main{{padding:22px 16px}}.choice{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="brand">135er-<span>Grow</span> Central · J.L.</div>{content}</main></body></html>"""
    return document.encode("utf-8")


class PortalHandler(http.server.BaseHTTPRequestHandler):
    server_version = "GrowCentralSetup/1.0"

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
        if self.path not in {"/", "/setup"}:
            self.send_error(404)
            return
        _, session = self.session()
        if not session:
            content = """<span class="kicker">FIRST BOOT / SECURE SETUP</span><h1>Pi konfigurieren.</h1>
<p>Mit dem lokalen Benutzer <strong>GrowCentral</strong> anmelden. Die Zugangsdaten werden über die geräteeigene HTTPS-Verbindung übertragen.</p>
<form method="post" action="/login"><label>BENUTZER<input name="username" value="GrowCentral" autocomplete="username" required></label>
<label>PASSWORT<input type="password" name="password" autocomplete="current-password" required></label><button type="submit">ANMELDEN</button></form>"""
            self.send_page(200, page("Grow Central Setup", content))
            return

        options = "".join(
            f'<option value="{html.escape(ssid, quote=True)}">{html.escape(ssid)} · {html.escape(signal)}% · {html.escape(security)}</option>'
            for ssid, signal, security in scan_networks()
        )
        content = f"""<span class="kicker">LOCAL-FIRST PROVISIONING</span><h1>System einrichten.</h1>
<p class="notice">Nach erfolgreicher Prüfung wird der Setup-Zugangspunkt abgeschaltet und das Hauptsystem gestartet. Schlägt die WLAN-Verbindung fehl, erscheint der Zugangspunkt erneut.</p>
<form method="post" action="/apply"><input type="hidden" name="csrf" value="{session.csrf}">
<div class="choice"><label><input type="radio" name="mode" value="wifi" checked> WLAN verwenden</label><label><input type="radio" name="mode" value="ethernet"> Nur LAN verwenden</label></div>
<label>WLAN-NAME (SSID)<input name="ssid" list="networks" maxlength="32"><datalist id="networks">{options}</datalist></label>
<label>WLAN-PASSWORT<input type="password" name="wifi_password" autocomplete="new-password" maxlength="63"></label>
<label>HOSTNAME<input name="hostname" value="grow-central" maxlength="63" required></label>
<label>ZEITZONE<select name="timezone">{''.join(f'<option value="{zone}">{zone}</option>' for zone in TIMEZONES)}</select></label>
<label>NEUES GROWCENTRAL-PASSWORT<input type="password" name="new_password" autocomplete="new-password" minlength="12" required></label>
<label>PASSWORT WIEDERHOLEN<input type="password" name="new_password_confirm" autocomplete="new-password" minlength="12" required></label>
<small>Mindestens 12 Zeichen. Dieses Passwort gilt danach für Benutzer, SSH und das Setup-Portal.</small>
<button type="submit">KONFIGURATION PRÜFEN UND ÜBERNEHMEN</button></form>"""
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
            authenticated = pam is not None and secrets.compare_digest(form.get("username", ""), USERNAME) and pam.pam().authenticate(
                USERNAME, form.get("password", ""), service="login"
            )
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
        subprocess.run(
            ["systemd-run", "--unit=grow-central-apply-setup", "--collect", "/usr/local/sbin/grow-central-apply-setup.py"],
            check=False,
        )
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
    # The setup portal must listen on the temporary AP. UFW restricts both
    # ports to 10.42.0.0/24 and the service stops after provisioning.
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
