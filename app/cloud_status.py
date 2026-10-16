"""Cloud-link status and local device-code pairing API for the Grow Central GUI."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.cloud_link_state import connection_state
from local.cloud_link.cloud_url import https_origin
from local.cloud_link.device_identity import ensure_identity
from local.cloud_link.device_pairing import clear_state, load_state, poll_pairing, start_pairing

router = APIRouter(prefix="/api/cloud", tags=["cloud-status"])
ENV_FILE = Path("/opt/135er-grow-central/local/cloud_link/.env")
RUNTIME_FILE = Path("/var/lib/135er-grow-central/cloud-link-status.json")


class PairStartRequest(BaseModel):
    name: str = Field(default="GrowCentral", min_length=1, max_length=120)


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def _cloud_origin() -> str:
    env = _read_env()
    origin = env.get("GC_CLOUD_URL", os.getenv("GC_CLOUD_URL", "")).rstrip("/")
    if not origin:
        raise HTTPException(status_code=503, detail="Cloud-Adresse fehlt")
    try:
        return https_origin(origin)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Cloud-Adresse ist kein gültiger HTTPS-Ursprung") from exc


def _read_runtime() -> dict:
    try:
        value = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _service_active() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", "135er-grow-central-cloud-link.service"],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _pairing_public_state() -> dict:
    try:
        identity = ensure_identity()
    except (OSError, RuntimeError, ValueError):
        return {"status": "identity_unavailable"}
    if identity.device_id:
        return {"status": "paired", "device_id": identity.device_id}
    pending = load_state()
    if not pending:
        return {"status": "not_started"}
    return {
        "status": str(pending.get("status", "authorization_pending")),
        "user_code": pending.get("user_code"),
        "verification_uri": pending.get("verification_uri"),
        "verification_uri_complete": pending.get("verification_uri_complete"),
        "expires_at": pending.get("expires_at"),
        "interval": pending.get("interval", 5),
    }


@router.get("/status")
async def cloud_status():
    env = _read_env()
    runtime = _read_runtime()
    enabled = env.get("GC_CLOUD_ENABLED", os.getenv("GC_CLOUD_ENABLED", "false")).lower() == "true"
    origin = env.get("GC_CLOUD_URL", os.getenv("GC_CLOUD_URL", "")).rstrip("/")
    invalid_origin = False
    if origin:
        try:
            origin = https_origin(origin)
        except ValueError:
            origin = ""
            invalid_origin = True
    parsed = urlparse(origin) if origin else None
    host = parsed.hostname if parsed else ""
    service_active = await asyncio.to_thread(_service_active) if enabled else False
    status = connection_state(runtime, enabled=enabled, origin=origin)
    connected = status["connected"] and service_active and not invalid_origin
    compatible = runtime.get("cloud_compatible")
    latency_ms: int | None = None
    detail = status["detail"] or "Cloud-Link startet"
    if enabled and invalid_origin:
        detail = "Cloud-Adresse ist kein gültiger HTTPS-Ursprung"
    elif enabled and not service_active:
        detail = "Cloud-Link-Dienst ist nicht aktiv"

    # Health probing is advisory only. V7 is primary; /api/health remains a
    # compatibility fallback. agent_v2 owns the authoritative connection state.
    health_reachable = False
    if enabled and origin:
        try:
            import time
            async with httpx.AsyncClient(follow_redirects=False) as client:
                started = time.monotonic()
                response = await client.get(f"{origin}/v7/health", timeout=4.0)
                payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                health_reachable = (
                    response.is_success
                    and isinstance(payload, dict)
                    and payload.get("ok") is True
                    and isinstance(payload.get("version"), int)
                    and payload.get("version") >= 7
                )
                if not health_reachable:
                    response = await client.get(f"{origin}/api/health", timeout=4.0)
                    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    health_reachable = response.is_success and isinstance(payload, dict) and payload.get("ok") is True and payload.get("service") == "135er-Grow Central Cloud"
                latency_ms = round((time.monotonic() - started) * 1000)
        except Exception:
            health_reachable = False

    return {
        "enabled": enabled,
        "service_active": service_active,
        "connected": connected,
        "state": "disabled" if not enabled else "invalid_configuration" if invalid_origin else "stopped" if not service_active else status["state"],
        "stale": status["stale"],
        "age_seconds": status["age_seconds"],
        "updated_at": status["updated_at"],
        "compatible": compatible,
        "health_reachable": health_reachable,
        "origin": origin,
        "host": host,
        "site_id": env.get("GC_SITE_ID", os.getenv("GC_SITE_ID", "")),
        "closed_test_mode": env.get("GC_CLOUD_TEST_MODE", os.getenv("GC_CLOUD_TEST_MODE", "false")).lower() == "true",
        "latency_ms": latency_ms,
        "detail": detail,
        "pairing": _pairing_public_state(),
        "runtime": {**runtime, "cloud_origin": origin},
    }


@router.post("/pair/start")
async def cloud_pair_start(body: PairStartRequest):
    origin = _cloud_origin()
    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            return await start_pairing(client, cloud_url=origin, name=body.name)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Cloud-Pairing konnte nicht gestartet werden") from exc
    except (httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Cloud-Pairing ist derzeit nicht verfügbar") from exc


@router.get("/pair/status")
async def cloud_pair_status():
    public = _pairing_public_state()
    if public.get("status") in {"paired", "not_started", "identity_unavailable"}:
        return public
    origin = _cloud_origin()
    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            return await poll_pairing(client, cloud_url=origin)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Cloud-Pairing-Status konnte nicht geprüft werden") from exc
    except (httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Cloud-Pairing-Status ist derzeit nicht verfügbar") from exc


@router.post("/pair/cancel")
async def cloud_pair_cancel():
    # Cancels only an unapproved local device-code flow. An already approved
    # installation must be revoked through the cloud account/device controls.
    identity = ensure_identity()
    if identity.device_id:
        raise HTTPException(status_code=409, detail="Bereits verbundene Installation muss in der Cloud widerrufen werden")
    clear_state()
    return {"ok": True, "status": "not_started"}
