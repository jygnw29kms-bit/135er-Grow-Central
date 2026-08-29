"""Allowlisted diagnostics for the Raspberry Pi appliance."""
from __future__ import annotations

import asyncio
import os
import platform
import re
import socket
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.audit import append_audit
from app.security import require_write_auth
from shared.hardware_profile import current_hardware

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])

UNITS = (
    "135er-grow-central.service",
    "135er-grow-central-cloud-link.service",
    "grow-central-display-kiosk.service",
    "grow-central-setup-ap.service",
    "grow-central-apply-setup.path",
    "grow-central-apply-setup.service",
    "grow-central-headless-firstboot.service",
    "grow-central-firstboot-firewall.service",
    "grow-central-healthcheck.service",
    "grow-central-healthcheck.timer",
    "grow-central-firstboot-debug.service",
    "grow-central-support-bundle.path",
    "grow-central-support-bundle.service",
    "NetworkManager.service",
    "avahi-daemon.service",
    "ssh.service",
    "bluetooth.service",
)
COMPLETION_MARKERS = {
    "grow-central-headless-firstboot.service": Path("/var/lib/135er-grow-central/.headless-firstboot-ready"),
    "grow-central-firstboot-firewall.service": Path("/var/lib/135er-grow-central/.firewall-initialized"),
}
STATE_DIR = Path("/var/lib/135er-grow-central")
SUPPORT_DIR = STATE_DIR / "support"
SUPPORT_REQUEST = STATE_DIR / "support-bundle-request"
SUPPORT_LATEST = SUPPORT_DIR / "Grow-Central-Support-latest.tar.gz"
APP_DIR = Path("/opt/135er-grow-central")
SECRET_PATTERN = re.compile(r"(?i)(authorization|password|passwd|secret|token)(\s*[:=]\s*)([^\s,;]+)")


def redact(text: str) -> str:
    return SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)


def _read(path: Path, limit: int = 4096) -> str:
    try:
        return redact(path.read_text(encoding="utf-8", errors="replace")[:limit].strip())
    except OSError:
        return ""


async def _command(*args: str, timeout: float = 8.0) -> tuple[int, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={"PATH": os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin"), "LANG": "C.UTF-8"},
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return 124, "TimeoutError"
        return process.returncode or 0, redact(output.decode("utf-8", "replace").strip())
    except FileNotFoundError as exc:
        return 127, type(exc).__name__


@router.get("/snapshot", dependencies=[Depends(require_write_auth)])
async def diagnostic_snapshot(lines: int = Query(default=120, ge=10, le=500)):
    services = {}
    for unit in UNITS:
        status_code, status = await _command("systemctl", "is-active", unit)
        _, failed_state = await _command("systemctl", "is-failed", unit)
        journal_code, journal = await _command(
            "journalctl", "--no-pager", "--output=short-iso", f"--lines={lines}", "--unit", unit
        )
        marker = COMPLETION_MARKERS.get(unit)
        completed = marker.exists() if marker else False
        active = status == "active"
        failed = failed_state == "failed"
        if completed and not active:
            display_status = "completed"
        else:
            display_status = status or ("failed" if failed else "unknown")
        services[unit] = {
            "active": active,
            "healthy": not failed,
            "completed": completed,
            "status": display_status,
            "status_exit_code": status_code,
            "journal_exit_code": journal_code,
            "journal": journal,
        }

    _, listeners = await _command("ss", "--listening", "--tcp", "--numeric", "--processes")
    _, addresses = await _command("ip", "-brief", "address")
    _, routes = await _command("ip", "route")
    _, nm_state = await _command("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device")
    _, nm_general = await _command("nmcli", "general", "status")
    _, rfkill_state = await _command("rfkill", "list")
    _, uptime = await _command("uptime", "-p")
    _, failed_units = await _command("systemctl", "--failed", "--no-pager", "--plain")
    _, disk = await _command("df", "-h", "/", "/var/lib/135er-grow-central")
    _, memory = await _command("free", "-m")

    display = {
        "name": _read(STATE_DIR / "display-name"),
        "mode": _read(STATE_DIR / "display-mode"),
        "connector": _read(STATE_DIR / "display-connector"),
        "kiosk_started": _read(STATE_DIR / "display-kiosk-started"),
        "packages_missing": _read(STATE_DIR / "display-kiosk-packages-missing"),
        "api_not_ready": _read(STATE_DIR / "display-api-not-ready"),
        "kiosk_files_missing": (STATE_DIR / "display-kiosk-files-missing").exists(),
    }

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "platform": platform.platform(),
        "hardware": current_hardware(),
        "build": _read(APP_DIR / "BUILD"),
        "version": _read(APP_DIR / "VERSION"),
        "uptime": uptime,
        "system": {"failed_units": failed_units, "disk": disk, "memory": memory},
        "services": services,
        "network": {
            "addresses": addresses,
            "routes": routes,
            "network_manager": nm_state,
            "network_manager_general": nm_general,
            "tcp_listeners": listeners,
        },
        "display": display,
        "radios": {"rfkill": rfkill_state},
        "setup": {
            "last_error": _read(STATE_DIR / "setup-last-error"),
            "last_warning": _read(STATE_DIR / "setup-last-warning"),
        },
        "markers": {
            "provisioned": (STATE_DIR / ".provisioned").exists(),
            "headless_firstboot_ready": (STATE_DIR / ".headless-firstboot-ready").exists(),
            "firewall_initialized": (STATE_DIR / ".firewall-initialized").exists(),
            "firstboot_debug_complete": (STATE_DIR / ".firstboot-debug-complete").exists(),
        },
    }
    append_audit("diagnostics.snapshot.read", lines=lines, units=list(UNITS))
    return result


@router.post("/bundle")
async def create_support_bundle():
    if SUPPORT_REQUEST.exists():
        raise HTTPException(409, "Ein Support-Paket wird bereits erstellt")
    STATE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    try:
        descriptor = os.open(SUPPORT_REQUEST, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(datetime.now(timezone.utc).isoformat() + "\n")
    except FileExistsError as exc:
        raise HTTPException(409, "Ein Support-Paket wird bereits erstellt") from exc
    append_audit("diagnostics.bundle.requested")
    return {"ok": True, "pending": True}


@router.get("/bundle/status")
async def support_bundle_status():
    available = SUPPORT_LATEST.is_file()
    stat = SUPPORT_LATEST.stat() if available else None
    return {
        "pending": SUPPORT_REQUEST.exists(),
        "available": available,
        "filename": "Grow-Central-Support-latest.tar.gz" if available else "",
        "size": stat.st_size if stat else 0,
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if stat else "",
    }


@router.get("/bundle/download")
async def download_support_bundle():
    if not SUPPORT_LATEST.is_file():
        raise HTTPException(404, "Noch kein Support-Paket vorhanden")
    append_audit("diagnostics.bundle.downloaded")
    return FileResponse(SUPPORT_LATEST, media_type="application/gzip", filename="Grow-Central-Support.tar.gz")
