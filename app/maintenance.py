from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])
ROOT = Path(os.getenv("GC_APP_ROOT", "/opt/135er-grow-central"))
STATE_DIR = Path(os.getenv("GC_STATE_DIR", "/var/lib/135er-grow-central"))


def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return default


def _service_state() -> dict:
    try:
        run = subprocess.run(
            ["systemctl", "show", "135er-grow-central.service", "--property=ActiveState", "--property=SubState", "--property=MainPID", "--no-pager"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        values = {}
        for line in run.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1); values[key] = value
        return {"active": values.get("ActiveState") == "active", "state": values.get("ActiveState", "unknown"), "substate": values.get("SubState", "unknown"), "main_pid": values.get("MainPID", "0")}
    except (OSError, subprocess.TimeoutExpired):
        return {"active": True, "state": "unknown", "substate": "unknown", "main_pid": "0"}


def _maintenance_bridge() -> dict:
    helper = Path("/usr/local/sbin/growcentral-maint")
    result = {"available": helper.is_file() and os.access(helper, os.X_OK), "noninteractive": False, "status": "unavailable"}
    if not result["available"]:
        return result
    try:
        run = subprocess.run(["sudo", "-n", str(helper), "status"], capture_output=True, text=True, timeout=3, check=False)
        result["noninteractive"] = run.returncode == 0
        result["status"] = "ready" if run.returncode == 0 else "password_required"
    except (OSError, subprocess.TimeoutExpired):
        result["status"] = "check_failed"
    return result


def _code_backups() -> list[dict]:
    parent = ROOT.parent
    rows = []
    try:
        candidates = sorted(parent.glob(ROOT.name + ".backup-*"), key=lambda item: item.stat().st_mtime, reverse=True)
    except OSError:
        return rows
    for item in candidates[:20]:
        try:
            stat = item.stat()
        except OSError:
            continue
        rows.append({"name": item.name, "modified": stat.st_mtime, "path_type": "code_rollback"})
    return rows


@router.get("/preflight")
async def preflight(deep: bool = Query(default=False)):
    disk = shutil.disk_usage(ROOT if ROOT.exists() else "/")
    service = _service_state()
    python_bin = ROOT / ".venv/bin/python"
    result = {
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "version": _read(ROOT / "VERSION", "unknown"),
        "build": _read(ROOT / "BUILD", "development"),
        "live_git_sha": _read(ROOT / ".live-git-sha"),
        "service": service,
        "disk": {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free, "free_percent": round(disk.free / disk.total * 100, 1) if disk.total else 0},
        "app": {"root_readable": os.access(ROOT, os.R_OK), "python_ready": python_bin.is_file() and os.access(python_bin, os.X_OK), "data_writable": os.access(ROOT / "data", os.W_OK), "state_writable": os.access(STATE_DIR, os.W_OK)},
        "maintenance_bridge": _maintenance_bridge(),
        "backup_count": len(_code_backups()),
    }
    result["ready"] = bool(service["active"] and result["app"]["root_readable"] and result["app"]["python_ready"] and disk.free >= 1024**3)
    if deep and result["app"]["python_ready"]:
        try:
            run = subprocess.run([str(python_bin), "-m", "pip", "check"], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
            result["pip_check"] = {"ok": run.returncode == 0, "summary": (run.stdout or run.stderr).strip()[:500]}
            result["ready"] = result["ready"] and run.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            result["pip_check"] = {"ok": False, "summary": "pip check nicht ausf?hrbar"}
            result["ready"] = False
    return result


@router.get("/backups")
async def backups():
    support = STATE_DIR / "support" / "Grow-Central-Support-latest.tar.gz"
    support_row = None
    try:
        stat = support.stat()
        support_row = {"available": support.is_file(), "size": stat.st_size, "modified": stat.st_mtime}
    except OSError:
        support_row = {"available": False, "size": 0, "modified": 0}
    return {"code_rollbacks": _code_backups(), "support_bundle": support_row}
