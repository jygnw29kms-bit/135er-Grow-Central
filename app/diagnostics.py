"""Token-protected, allowlisted development diagnostics for the Raspberry Pi."""
from __future__ import annotations

import asyncio
import os
import platform
import re
import socket
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

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
        services[unit] = {
            "active": status == "active",
            "status": status or "unknown",
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
