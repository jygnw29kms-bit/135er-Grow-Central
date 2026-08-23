"""Session authentication for the local Grow Central GUI/API.

The first-boot wizard stores only a PBKDF2 password verifier. The browser receives
an opaque, HttpOnly session cookie after login. Secrets are never returned by an
API endpoint.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, SecretStr
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE_NAME = "gc_gui_session"
SESSION_TTL = 12 * 60 * 60
PBKDF2_ITERATIONS = 240_000
ROOT = Path(__file__).resolve().parent.parent


@dataclass
class GuiSession:
    expires: float


SESSIONS: dict[str, GuiSession] = {}


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr


def hash_password(password: str, *, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    if len(password) < 12:
        raise ValueError("GUI password must contain at least 12 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="), base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_raw + "=" * (-len(salt_raw) % 4))
        expected = base64.urlsafe_b64decode(digest_raw + "=" * (-len(digest_raw) % 4))
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(candidate, expected)
    except (ValueError, TypeError):
        return False


def configured() -> bool:
    return bool(os.getenv("GC_GUI_USERNAME", "").strip() and os.getenv("GC_GUI_PASSWORD_HASH", "").strip())


def authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        return False
    current = SESSIONS.get(token)
    if not current or current.expires <= time.monotonic():
        SESSIONS.pop(token, None)
        return False
    current.expires = time.monotonic() + SESSION_TTL
    return True


class GuiAuthMiddleware(BaseHTTPMiddleware):
    """Protect the appliance UI and APIs once first-boot credentials exist."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public = path == "/api/health" or path == "/login" or path.startswith("/api/auth/") or path.startswith("/static/")
        if public:
            return await call_next(request)
        if not configured():
            if path.startswith("/api/"):
                return JSONResponse({"detail": "GUI authentication is not configured; complete first-boot setup"}, status_code=503)
            return HTMLResponse("<h1>135er-Grow Central</h1><p>First-Boot-Setup noch nicht abgeschlossen.</p>", status_code=503)
        if authenticated(request):
            if path == "/":
                return RedirectResponse("/ui", status_code=303)
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "GUI login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)


router = APIRouter(tags=["gui-auth"])


def _read_text(name: str, fallback: str) -> str:
    try:
        return (ROOT / name).read_text(encoding="utf-8").strip() or fallback
    except OSError:
        return fallback


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    username = os.getenv("GC_GUI_USERNAME", "").strip() or "beim First Boot vergeben"
    version = _read_text("VERSION", "unknown")
    build = _read_text("BUILD", "development")
    page = """<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#02070a"><title>135er-Grow Central Login</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 70% 0,#0a2730,#02070a 40%);color:#edfdf9;font-family:Inter,Arial,sans-serif}.intro{position:fixed;inset:0;z-index:5;background:#02070a;display:grid;place-items:center;transition:.5s}.intro.done{opacity:0;pointer-events:none}.slide{position:absolute;width:min(900px,88vw);text-align:center;opacity:0;transform:translateY(10px);transition:.45s}.slide.active{opacity:1;transform:none}.slide img{width:min(310px,60vw);max-height:130px;object-fit:contain;margin-bottom:22px}.slide .tag{color:#2ae5ff;font-size:.72rem;letter-spacing:.22em}.slide h2{font-size:clamp(1.8rem,5vw,3.5rem);margin:10px 0}.slide p{color:#8aaab1;font-size:1.05rem}.progress{position:absolute;bottom:8vh;width:min(520px,70vw);height:2px;background:#15343c}.progress i{display:block;height:100%;width:0;background:#71ff3b;animation:grow 10s linear forwards}@keyframes grow{to{width:100%}}
.login-wrap{min-height:100vh;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(360px,520px);align-items:stretch}.brand-side{padding:7vw;display:flex;flex-direction:column;justify-content:center}.brand-side img{width:min(430px,75%)}.brand-side h1{font-size:clamp(2rem,5vw,4.4rem);margin:24px 0 10px}.brand-side p{max-width:650px;color:#86a5ac;line-height:1.6}.facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:26px}.facts div{border:1px solid #17414a;background:#061319;padding:14px}.facts small{display:block;color:#62858d;margin-bottom:6px}.facts strong{color:#2ae5ff;font-size:.86rem}.login-side{border-left:1px solid #17414a;background:rgba(3,12,16,.86);display:grid;place-items:center;padding:28px}.box{width:min(430px,100%);padding:26px;border:1px solid #17414a;background:#061319;box-shadow:0 20px 70px #000}.eyebrow{color:#2ae5ff;font-size:.68rem;letter-spacing:.18em}.box h2{margin:8px 0 4px}.box .hint{color:#88a5ac;font-size:.88rem;line-height:1.5}label{display:grid;gap:7px;margin:16px 0;color:#2ae5ff;font-size:.78rem}input{padding:13px;border:1px solid #17414a;background:#020a0e;color:white;font-size:1rem}button{width:100%;padding:14px;border:1px solid #71ff3b;background:#71ff3b;color:#041006;font-weight:800;cursor:pointer}.msg{min-height:1.3em;color:#ff8b96;font-size:.85rem}.secure{margin-top:14px;color:#63858c;font-size:.75rem}@media(max-width:800px){.login-wrap{grid-template-columns:1fr}.brand-side{padding:28px 20px}.brand-side h1{font-size:2rem}.facts{grid-template-columns:1fr}.login-side{border-left:0;border-top:1px solid #17414a;padding:20px}.brand-side img{width:250px}}
</style></head><body>
<div class="intro" id="intro"><div class="slide active"><img src="/static/brand-logo.png" alt="135er-Grow Central"><div class="tag">WELCOME TO GROW CENTRAL</div><h2>Eine Zentrale. Alle Geräte.</h2><p>Lokale Steuerung für Klima, Energie, Smart Home und Grow-Hardware.</p></div><div class="slide"><div class="tag">SMART HOME</div><h2>FRITZ! · Tapo · Energie</h2><p>Steckdosen schalten, Leistung messen, Kosten und Historie auswerten.</p></div><div class="slide"><div class="tag">DEVICE CONTROL</div><h2>Mars Hydro · Kamera · Sensorik</h2><p>Geräte erkennen, Zustände sehen und Funktionen gezielt bedienen.</p></div><div class="slide"><div class="tag">LOCAL-FIRST</div><h2>135er-GrowCentral.local</h2><p>Deine Grow-Zentrale bleibt im Heimnetz direkt und dauerhaft erreichbar.</p></div><div class="progress"><i></i></div></div>
<div class="login-wrap"><section class="brand-side"><img src="/static/brand-logo.png" alt="135er-Grow Central"><h1>Grow Central</h1><p>Das lokale Control Center für Raspberry Pi, Smart Home, Kamera, Energieanalyse und Automationen.</p><div class="facts"><div><small>ADRESSE</small><strong>135er-GrowCentral.local</strong></div><div><small>SOFTWARE</small><strong>VERSION __VERSION__ · BUILD __BUILD__</strong></div><div><small>LOGIN-BENUTZER</small><strong>__USER__</strong></div></div></section><section class="login-side"><form class="box" id="login"><div class="eyebrow">SECURE LOCAL LOGIN</div><h2>Anmelden</h2><p class="hint">Verwende die Zugangsdaten, die beim First-Boot-Setup vergeben wurden. Das Passwort wird aus Sicherheitsgründen nicht im Klartext gespeichert oder erneut angezeigt.</p><label>Benutzername<input id="u" autocomplete="username" value="__USER_VALUE__" required></label><label>Passwort<input id="p" type="password" autocomplete="current-password" required></label><p class="msg" id="m"></p><button>Anmelden</button><div class="secure">Lokale Sitzung · HttpOnly Cookie · 12 h Session</div></form></section></div>
<script>const intro=document.getElementById('intro');const key='gc-intro-seen-v2';if(localStorage.getItem(key)==='1'){intro.remove()}else{const slides=[...document.querySelectorAll('.slide')];let i=0;const t=setInterval(()=>{slides[i].classList.remove('active');i++;if(i>=slides.length){clearInterval(t);localStorage.setItem(key,'1');intro.classList.add('done');setTimeout(()=>intro.remove(),600);return}slides[i].classList.add('active')},2500)}document.getElementById('login').addEventListener('submit',async e=>{e.preventDefault();const m=document.getElementById('m');m.textContent='Anmeldung läuft…';try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})});if(!r.ok){const x=await r.json().catch(()=>({}));throw new Error(x.detail||'Anmeldung fehlgeschlagen')}location.href='/ui'}catch(err){m.textContent=err.message}});</script></body></html>"""
    return HTMLResponse(page.replace("__VERSION__", version).replace("__BUILD__", build).replace("__USER__", username).replace("__USER_VALUE__", "" if username == "beim First Boot vergeben" else username))


@router.post("/api/auth/login")
async def login(body: LoginBody, response: Response):
    expected_user = os.getenv("GC_GUI_USERNAME", "").strip()
    expected_hash = os.getenv("GC_GUI_PASSWORD_HASH", "").strip()
    if not expected_user or not expected_hash:
        raise HTTPException(503, "GUI authentication is not configured")
    if not secrets.compare_digest(body.username, expected_user) or not verify_password(body.password.get_secret_value(), expected_hash):
        time.sleep(0.2)
        raise HTTPException(401, "Benutzername oder Passwort falsch")
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = GuiSession(expires=time.monotonic() + SESSION_TTL)
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_TTL, httponly=True, samesite="strict", secure=False, path="/")
    return {"ok": True, "username": expected_user}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME, "")
    if token:
        SESSIONS.pop(token, None)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/api/auth/status")
async def auth_status(request: Request):
    return {"configured": configured(), "authenticated": authenticated(request)}
