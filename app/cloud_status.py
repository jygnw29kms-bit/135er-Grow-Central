"""Read-only cloud-link status for the local GUI."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/cloud", tags=["cloud-status"])
ENV_FILE = Path("/opt/135er-grow-central/local/cloud_link/.env")


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
    enabled = env.get("GC_CLOUD_ENABLED", os.getenv("GC_CLOUD_ENABLED", "false")).lower() == "true"
    origin = env.get("GC_CLOUD_URL", os.getenv("GC_CLOUD_URL", "")).rstrip("/")
    parsed = urlparse(origin) if origin else None
    host = parsed.hostname if parsed else ""
    service_active = _service_active() if enabled else False
    connected = False
    latency_ms: int | None = None
    detail = "Cloud-Link deaktiviert"

    if enabled and not origin:
        detail = "Cloud-Link aktiviert, aber kein Cloudhost konfiguriert"
    elif enabled and origin:
        try:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                import time
                started = time.monotonic()
                response = await client.get(f"{origin}/api/health", timeout=4.0)
                latency_ms = round((time.monotonic() - started) * 1000)
                payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                connected = response.is_success and payload.get("ok") is True
                detail = "Cloud erreichbar" if connected else f"Cloud antwortet mit HTTP {response.status_code}"
        except Exception as exc:
            detail = f"Cloud nicht erreichbar ({type(exc).__name__})"

    return {
        "enabled": enabled,
        "service_active": service_active,
        "connected": connected,
        "origin": origin,
        "host": host,
        "site_id": env.get("GC_SITE_ID", os.getenv("GC_SITE_ID", "")),
        "closed_test_mode": env.get("GC_CLOUD_TEST_MODE", os.getenv("GC_CLOUD_TEST_MODE", "false")).lower() == "true",
        "latency_ms": latency_ms,
        "detail": detail,
    }
