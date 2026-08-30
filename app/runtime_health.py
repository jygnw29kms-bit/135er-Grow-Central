"""Unified runtime health contract for web and mobile clients."""
from __future__ import annotations

import json
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from app.devices.runtime import runtime as device_runtime
from shared.hardware_profile import current_hardware

router = APIRouter(prefix="/api/runtime", tags=["runtime"])

STATE_DIR = Path("/var/lib/135er-grow-central")
APP_DIR = Path("/opt/135er-grow-central")
CLOUD_STATE = STATE_DIR / "cloud-link-status.json"


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _setup_lifecycle() -> str:
    if (STATE_DIR / ".provisioned").is_file():
        return "provisioned"
    if (STATE_DIR / "setup-pending.json").exists():
        return "applying"
    if (STATE_DIR / "setup-last-error").is_file():
        return "error"
    return "required"


@router.get("/health")
async def runtime_health():
    cloud = _json(CLOUD_STATE)
    setup_state = _setup_lifecycle()
    provisioned = setup_state == "provisioned"
    setup_error = _text(STATE_DIR / "setup-last-error")
    setup_warning = _text(STATE_DIR / "setup-last-warning")
    provider_ids = list(device_runtime.ids())
    hardware = current_hardware()

    cloud_enabled = os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true"
    cloud_state = str(cloud.get("state") or ("disabled" if not cloud_enabled else "starting"))
    cloud_optional_ok = not cloud_enabled or cloud_state in {"connected", "degraded", "disabled", "starting"}

    blockers: list[str] = []
    warnings: list[str] = []
    if setup_state == "error" or setup_error:
        blockers.append("setup_error")
    if not provider_ids:
        blockers.append("device_runtime_empty")
    if setup_warning:
        warnings.append("setup_warning")
    if setup_state in {"required", "applying"}:
        warnings.append(f"setup_{setup_state}")
    if cloud_enabled and cloud_state != "connected":
        warnings.append("cloud_not_connected")

    state = "error" if blockers else ("warning" if warnings else "ok")
    return {
        "ok": not blockers,
        "state": state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product": "135er-Grow Central",
        "architecture": "headless-local-first",
        "device_api": "gc-device-v1",
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "version": _text(APP_DIR / "VERSION") or "0.7.5",
        "build": _text(APP_DIR / "BUILD"),
        "provisioned": provisioned,
        "setup": {
            "state": setup_state,
            "required": setup_state != "provisioned",
            "error": setup_error,
            "warning": setup_warning,
        },
        "cloud": {
            "enabled": cloud_enabled,
            "state": cloud_state,
            "optional_ok": cloud_optional_ok,
            "detail": cloud.get("detail", ""),
            "compatible": cloud.get("cloud_compatible"),
        },
        "device_runtime": {
            "provider_count": len(provider_ids),
            "providers": provider_ids,
        },
        "hardware": hardware,
        "ui": {
            "local_kiosk": False,
            "desktop_web": True,
            "mobile": True,
            "modes": ["simple", "advanced"],
        },
        "blockers": blockers,
        "warnings": warnings,
    }
