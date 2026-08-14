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
from app.credential_store import delete_credentials, get_provider_config, set_credentials
from app.security import require_write_auth
from .adapters.base import AdapterError
from .adapters.fritz import FritzAhaClient, FritzLoginError
from .models import DeviceConfig
from .registry import DeviceRegistry

router = APIRouter(prefix="/onboarding/fritz", tags=["fritz-onboarding"])


class FritzLoginRequest(BaseModel):
    host: str | None = Field(default=None, min_length=1, max_length=253)
    username: str | None = Field(default=None, min_length=1, max_length=128)
    password: SecretStr | None = None
    import_devices: bool = True


class FritzObjectActionRequest(FritzLoginRequest):
    identifier: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9 _.-]+$")
    active: bool | None = None


class FritzSwitchRequest(FritzLoginRequest):
    ain: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9 _.-]+$")
    on: bool


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
    host, username, password, supplied = _request_credentials(request)
    verified = await _verify_fritz(host)
    if not verified:
        raise HTTPException(404, "Keine eindeutige FRITZ!Box unter dieser Adresse erkannt")
    client = FritzAhaClient(host, username, password)
    try:
        devices = await client.list_devices()
    except FritzLoginError as exc:
        append_audit(
            "fritz.login.failed",
            host=host,
            reason=exc.code,
            retry_after=exc.retry_after,
        )
        if exc.code == "unknown_user":
            raise HTTPException(401, "Der FRITZ!Box-Benutzername ist nicht bekannt. Bitte den vollständigen Namen aus System > FRITZ!Box-Benutzer verwenden.") from None
        if exc.code == "bad_credentials":
            raise HTTPException(401, "FRITZ!Box-Benutzername oder Passwort ist falsch. Nach Fehlversuchen kann die FRITZ!Box eine kurze Anmeldesperre setzen.") from None
        if exc.code == "blocked":
            raise HTTPException(
                429,
                f"Die FRITZ!Box-Anmeldung ist noch {exc.retry_after} Sekunden gesperrt. Bitte danach erneut versuchen.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from None
        if exc.code == "missing_homeauto_permission":
            raise HTTPException(403, "Anmeldung erfolgreich, aber der Benutzer darf Smart Home nicht lesen. In der FRITZ!Box beim Benutzer die Berechtigung Smart Home aktivieren.") from None
        raise HTTPException(502, f"FRITZ!Box antwortet, aber der Login schlug fehl ({exc.code}).") from None
    except AdapterError as exc:
        reason = str(exc)
        append_audit("fritz.login.failed", host=host, reason="aha_rejected")
        if "rejected command" in reason:
            raise HTTPException(403, "Anmeldung erfolgreich, aber der Benutzer darf Smart Home nicht lesen. In der FRITZ!Box beim Benutzer die Berechtigung Smart Home aktivieren.") from None
        raise HTTPException(502, "FRITZ!Box antwortet, aber der Smart-Home-Aufruf wurde abgelehnt.") from None
    except Exception as exc:
        append_audit("fritz.login.failed", host=host, reason=type(exc).__name__)
        raise HTTPException(502, f"FRITZ!Box-Kommunikation fehlgeschlagen ({type(exc).__name__})") from None

    if supplied:
        try:
            set_credentials("fritz", username, password, host=host)
        except OSError:
            raise HTTPException(500, "FRITZ!-Anmeldung war erfolgreich, konnte aber nicht sicher gespeichert werden") from None

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
                host=host,
                metadata={"product": row.get("product"), "auto_imported": True, "transport": "local-fritz-aha"},
            )
            registry.upsert(device)
            imported.append({"id": device.id, "name": device.name, "adapter": "fritz", "approved": True, "writable": True, "product": row.get("product"), "online": row.get("present"), "state": row.get("details")})

    append_audit("fritz.login.success", host=host, found=len(devices), imported=len(imported), credentials_saved=supplied)
    return {"ok": True, "host": host, "devices_found": len(devices), "imported": imported, "credentials_stored": get_provider_config("fritz") is not None}


def _request_credentials(request: FritzLoginRequest) -> tuple[str, str, str, bool]:
    username = (request.username or "").strip()
    password = request.password.get_secret_value() if request.password is not None else ""
    supplied = bool(username or password)
    stored = get_provider_config("fritz") or {}
    if supplied and (not username or not password):
        raise HTTPException(422, "FRITZ!-Benutzer und Passwort müssen gemeinsam angegeben werden")
    if not supplied:
        username = str(stored.get("username") or "").strip()
        password = str(stored.get("password") or "")
    if not username or not password:
        raise HTTPException(428, "FRITZ!-Anmeldung muss einmalig eingerichtet werden")
    host = (request.host or str(stored.get("host") or "fritz.box")).strip()
    return host, username, password, supplied


async def _manual_client(request: FritzLoginRequest) -> tuple[FritzAhaClient, str]:
    host, username, password, _supplied = _request_credentials(request)
    client = FritzAhaClient(host, username, password)
    try:
        await client.login()
    except FritzLoginError as exc:
        raise HTTPException(401 if exc.code != "blocked" else 429, "FRITZ!-Anmeldung fehlgeschlagen. Zugang und Smart-Home-Berechtigung prüfen.") from None
    except (AdapterError, httpx.HTTPError, OSError) as exc:
        raise HTTPException(502, f"FRITZ!Box-Verbindung fehlgeschlagen ({type(exc).__name__})") from None
    return client, host


@router.get("/credentials")
async def fritz_credentials_status():
    stored = get_provider_config("fritz") or {}
    return {
        "configured": bool(stored.get("username") and stored.get("password")),
        "host": str(stored.get("host") or "fritz.box"),
        "username": str(stored.get("username") or ""),
    }


@router.delete("/credentials", dependencies=[Depends(require_write_auth)])
async def fritz_credentials_delete():
    removed = delete_credentials("fritz")
    append_audit("fritz.credentials.deleted", removed=removed)
    return {"ok": True, "removed": removed}


@router.post("/automations", dependencies=[Depends(require_write_auth)])
async def fritz_automations(request: FritzLoginRequest):
    client, host = await _manual_client(request)
    try:
        result = await client.list_automations()
    except (AdapterError, httpx.HTTPError, ET.ParseError) as exc:
        raise HTTPException(502, f"FRITZ!-Automationen konnten nicht gelesen werden ({type(exc).__name__})") from None
    append_audit("fritz.automations.read", host=host, triggers=len(result["triggers"]), templates=len(result["templates"]))
    return {**result, "credentials_stored": True}


@router.post("/automations/trigger", dependencies=[Depends(require_write_auth)])
async def fritz_trigger_set(request: FritzObjectActionRequest):
    if request.active is None:
        raise HTTPException(422, "Aktivzustand fehlt")
    client, _host = await _manual_client(request)
    try:
        await client.set_trigger_active(request.identifier, request.active)
    except (AdapterError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"FRITZ!-Routine konnte nicht geändert werden ({type(exc).__name__})") from None
    append_audit("fritz.trigger.set", identifier=request.identifier, active=request.active)
    return {"ok": True, "identifier": request.identifier, "active": request.active, "credentials_stored": True}


@router.post("/automations/template", dependencies=[Depends(require_write_auth)])
async def fritz_template_apply(request: FritzObjectActionRequest):
    client, _host = await _manual_client(request)
    try:
        await client.apply_template(request.identifier)
    except (AdapterError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"FRITZ!-Vorlage konnte nicht angewendet werden ({type(exc).__name__})") from None
    append_audit("fritz.template.applied", identifier=request.identifier)
    return {"ok": True, "identifier": request.identifier, "credentials_stored": True}


@router.post("/switch", dependencies=[Depends(require_write_auth)])
async def fritz_manual_switch(request: FritzSwitchRequest):
    client, _host = await _manual_client(request)
    try:
        result = await client.command("setswitchon" if request.on else "setswitchoff", request.ain)
        if result not in {"0", "1"}:
            raise HTTPException(502, "FRITZ!Box meldet einen unerwarteten Schaltzustand")
        xml_text = await client.command("getdeviceinfos", request.ain)
        node = ET.fromstring(xml_text)
    except (AdapterError, httpx.HTTPError, ET.ParseError) as exc:
        raise HTTPException(502, f"FRITZ!-Steckdose konnte nicht geschaltet werden ({type(exc).__name__})") from None
    from .adapters.fritz import _device_data
    state = _device_data(node)
    append_audit("fritz.switch.manual", ain=request.ain, on=request.on)
    return {"ok": True, "state": state, "credentials_stored": True}
