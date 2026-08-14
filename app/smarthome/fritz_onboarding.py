"""Automatic FRITZ!Box detection and explicit authenticated device import."""
from __future__ import annotations

import asyncio
import re
import socket
import subprocess

import httpx
from defusedxml import ElementTree as ET
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr

from app.audit import append_audit
from app.credential_store import set_credentials
from app.security import require_write_auth
from .adapters.fritz import FritzAhaClient
from .adapters.base import AdapterError
from .models import DeviceConfig
from .registry import DeviceRegistry

router = APIRouter(prefix="/onboarding/fritz", tags=["fritz-onboarding"])


class FritzLoginRequest(BaseModel):
    host: str = Field(default="fritz.box", min_length=1, max_length=253)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr
    import_devices: bool = True


def _default_gateway() -> str | None:
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"\bvia\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


def _candidate_hosts() -> list[str]:
    hosts = ["fritz.box"]
    gateway = _default_gateway()
    if gateway:
        hosts.append(gateway)
    try:
        resolved = socket.gethostbyname("fritz.box")
        hosts.append(resolved)
    except OSError:
        pass
    return list(dict.fromkeys(hosts))


async def _verify_fritz(host: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=2.5, follow_redirects=True) as client:
            login, tr64 = await asyncio.gather(
                client.get(f"http://{host}/login_sid.lua", params={"version": "2"}),
                client.get(f"http://{host}:49000/tr64desc.xml"),
                return_exceptions=True,
            )
        if isinstance(login, Exception) or login.status_code != 200:
            return None
        root = ET.fromstring(login.text)
        if root.tag.lower().endswith("sessioninfo") is False:
            return None
        fingerprint = ""
        if not isinstance(tr64, Exception) and tr64.status_code == 200:
            fingerprint = tr64.text[:12000].lower()
        if fingerprint and not any(token in fingerprint for token in ("avm", "fritz", "urn:dslforum-org")):
            return None
        return {"detected": True, "host": host, "login_required": True, "fingerprint": "AVM FRITZ!Box"}
    except (httpx.HTTPError, ET.ParseError, OSError):
        return None


@router.get("/presence")
async def fritz_presence():
    for host in _candidate_hosts():
        result = await _verify_fritz(host)
        if result:
            return result
    return {"detected": False, "login_required": False}


@router.post("/login", dependencies=[Depends(require_write_auth)])
async def fritz_login(request: FritzLoginRequest):
    verified = await _verify_fritz(request.host)
    if not verified:
        raise HTTPException(404, "Keine eindeutige FRITZ!Box unter dieser Adresse erkannt")
    username = request.username.strip()
    password = request.password.get_secret_value()
    client = FritzAhaClient(request.host, username, password)
    try:
        devices = await client.list_devices()
    except AdapterError as exc:
        reason = str(exc)
        append_audit("fritz.login.failed", host=request.host, reason=reason)
        if "username is unknown" in reason:
            raise HTTPException(401, "Der FRITZ!Box-Benutzername ist nicht bekannt. Bitte den vollständigen Namen aus System > FRITZ!Box-Benutzer verwenden.") from None
        if "authentication failed" in reason:
            raise HTTPException(401, "FRITZ!Box-Benutzername oder Passwort ist falsch. Nach Fehlversuchen kann die FRITZ!Box eine kurze Anmeldesperre setzen.") from None
        if "rejected command" in reason:
            raise HTTPException(403, "Anmeldung erfolgreich, aber der Benutzer darf Smart Home nicht lesen. In der FRITZ!Box beim Benutzer die Berechtigung Smart Home aktivieren.") from None
        raise HTTPException(502, f"FRITZ!Box antwortet, aber der Smart-Home-Aufruf schlug fehl: {reason}") from None
    except Exception as exc:
        append_audit("fritz.login.failed", host=request.host, reason=type(exc).__name__)
        raise HTTPException(502, f"FRITZ!Box-Kommunikation fehlgeschlagen ({type(exc).__name__})") from None

    set_credentials("fritz", username, password, host=request.host)
    imported = []
    if request.import_devices:
        registry = DeviceRegistry.from_env()
        for row in devices:
            safe = re.sub(r"[^a-z0-9]+", "-", row["ain"].lower()).strip("-")[:48] or "device"
            device = DeviceConfig(
                id=f"fritz-{safe}",
                name=row["name"],
                adapter="fritz",
                native_id=row["ain"],
                capability="switch",
                approved=True,
                writable=True,
                host=request.host,
                metadata={"product": row.get("product"), "auto_imported": True, "transport": "local-fritz-aha"},
            )
            registry.upsert(device)
            imported.append({"id": device.id, "name": device.name, "product": row.get("product"), "present": row.get("present")})

    append_audit("fritz.login.success", host=request.host, found=len(devices), imported=len(imported))
    return {"ok": True, "host": request.host, "devices_found": len(devices), "imported": imported, "credentials_stored": True}
