"""Token-protected, allowlisted development diagnostics for the Raspberry Pi."""
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

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])

UNITS = (
    "135er-grow-central.service",
    "grow-central-headless-firstboot.service",
    "grow-central-firstboot-firewall.service",
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
SECRET_PATTERN = re.compile(r"(?i)(authorization|password|passwd|secret|token)(\s*[:=]\s*)([^\s,;]+)")


def redact(text: str) -> str:
    return SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)


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
async def diagnostic_snapshot(lines: int = Query(default=80, ge=10, le=300)):
    services = {}
    for unit in UNITS:
        status_code, status = await _command("systemctl", "is-active", unit)
        journal_code, journal = await _command(
            "journalctl", "--no-pager", "--output=short-iso", f"--lines={lines}", "--unit", unit
        )
        marker = COMPLETION_MARKERS.get(unit)
        completed = marker.exists() if marker else False
        active = status == "active"
        services[unit] = {
            "active": active,
            "healthy": active or completed,
            "completed": completed,
            "status": "completed" if completed and not active else status or "unknown",
            "status_exit_code": status_code,
            "journal_exit_code": journal_code,
            "journal": journal,
        }
    _, listeners = await _command("ss", "--listening", "--tcp", "--numeric", "--processes")
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "services": services,
        "tcp_listeners": listeners,
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
    return FileResponse(
        SUPPORT_LATEST,
        media_type="application/gzip",
        filename="Grow-Central-Support.tar.gz",
    )
