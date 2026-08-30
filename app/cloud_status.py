"""Read-only cloud-link status for the local GUI."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/cloud", tags=["cloud-status"])
ENV_FILE = Path("/opt/135er-grow-central/local/cloud_link/.env")
RUNTIME_FILE = Path("/var/lib/135er-grow-central/cloud-link-status.json")


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


def _read_runtime() -> dict:
    try:
        value = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _service_active() -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", "135er-grow-central-cloud-link.service"],
        capture_output=True,
        timeout=3,
        check=False,
    )
    return result.returncode == 0


@router.get("/status")
async def cloud_status():
    env = _read_env()
    runtime = _read_runtime()
    enabled = env.get("GC_CLOUD_ENABLED", os.getenv("GC_CLOUD_ENABLED", "false")).lower() == "true"
    origin = env.get("GC_CLOUD_URL", os.getenv("GC_CLOUD_URL", "")).rstrip("/")
    parsed = urlparse(origin) if origin else None
    host = parsed.hostname if parsed else ""
    service_active = _service_active() if enabled else False
    connected = runtime.get("state") == "connected"
    compatible = runtime.get("cloud_compatible")
    latency_ms: int | None = None
    detail = str(runtime.get("detail") or ("Cloud-Link deaktiviert" if not enabled else "Cloud-Link startet"))

    # Health probing is advisory only. A reachable /api/health endpoint does not
    # mean telemetry sync works; agent_v2 owns the authoritative connection state.
    health_reachable = False
    if enabled and origin:
        try:
            import time
            async with httpx.AsyncClient(follow_redirects=False) as client:
                started = time.monotonic()
                response = await client.get(f"{origin}/api/health", timeout=4.0)
                latency_ms = round((time.monotonic() - started) * 1000)
                payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                health_reachable = response.is_success and payload.get("ok") is True
        except Exception:
            health_reachable = False

    return {
        "enabled": enabled,
        "service_active": service_active,
        "connected": connected,
        "compatible": compatible,
        "health_reachable": health_reachable,
        "origin": origin,
        "host": host,
        "site_id": env.get("GC_SITE_ID", os.getenv("GC_SITE_ID", "")),
        "closed_test_mode": env.get("GC_CLOUD_TEST_MODE", os.getenv("GC_CLOUD_TEST_MODE", "false")).lower() == "true",
        "latency_ms": latency_ms,
        "detail": detail,
        "runtime": runtime,
    }
