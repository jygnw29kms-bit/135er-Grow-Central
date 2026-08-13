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
from pathlib import Path
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, SecretStr
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE_NAME = "gc_gui_session"
SESSION_TTL = 12 * 60 * 60
PBKDF2_ITERATIONS = 240_000


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
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


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
        setup_active = (Path(__file__).resolve().parent.parent / "web" / "setup.html").is_file()
        public = (
            path == "/api/health"
            or path == "/login"
            or path.startswith("/api/auth/")
            or path.startswith("/static/")
            or (setup_active and (path == "/" or path.startswith("/api/setup")))
        )
        if public:
            return await call_next(request)
        if not configured():
            if path.startswith("/api/"):
                return JSONResponse({"detail": "GUI authentication is not configured; complete first-boot setup"}, status_code=503)
            return HTMLResponse("<h1>135er-Grow Central</h1><p>First-Boot-Setup noch nicht abgeschlossen.</p>", status_code=503)
        if authenticated(request):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "GUI login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)


router = APIRouter(tags=["gui-auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse("""<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>135er-Grow Central Login</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#02070a;color:#edfdf9;font-family:Arial,sans-serif}.box{width:min(430px,92vw);padding:28px;border:1px solid #17414a;background:#061319;box-shadow:0 20px 70px #000}h1{margin-top:0}label{display:grid;gap:7px;margin:16px 0;color:#2ae5ff;font-size:.8rem}input{padding:13px;border:1px solid #17414a;background:#020a0e;color:white;font-size:1rem}button{width:100%;padding:14px;border:1px solid #71ff3b;background:#71ff3b;color:#041006;font-weight:800}.msg{min-height:1.3em;color:#ff8b96;font-size:.85rem}</style></head><body><form class=\"box\" id=\"login\"><h1>135er-Grow Central</h1><p>Geschützter lokaler Steuerzugang</p><label>Benutzername<input id=\"u\" autocomplete=\"username\" required></label><label>Passwort<input id=\"p\" type=\"password\" autocomplete=\"current-password\" required></label><p class=\"msg\" id=\"m\"></p><button>Anmelden</button></form><script>document.getElementById('login').addEventListener('submit',async e=>{e.preventDefault();const m=document.getElementById('m');m.textContent='Anmeldung läuft…';try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})});if(!r.ok){const x=await r.json().catch(()=>({}));throw new Error(x.detail||'Anmeldung fehlgeschlagen')}location.href='/';}catch(err){m.textContent=err.message}});</script></body></html>""")


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
