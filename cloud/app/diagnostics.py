"""Central diagnostic mirror for 135er-Grow Central closed-test and production use."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import secrets
import socket

import aiosqlite
from fastapi import APIRouter, Header, HTTPException, Path as ApiPath, Request
from pydantic import BaseModel, Field

from .config import settings

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])

_SAFE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_MAX_BUNDLE_BYTES = 12 * 1024 * 1024


def _auth(token: str | None, *, allow_closed_test: bool = False) -> None:
    if allow_closed_test and settings.cloud_closed_test_mode:
        return
    expected = settings.cloud_api_token.strip()
    if len(expected) < 32 or expected.startswith("CHANGE_ME"):
        raise HTTPException(503, "cloud authentication is not configured")
    candidate = (token or "").strip()
    if not candidate or not secrets.compare_digest(candidate, expected):
        raise HTTPException(401, "invalid api token")


def _root() -> Path:
    root = Path(settings.cloud_db).resolve().parent / "diagnostics"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _device_dir(site_id: str, device_id: str) -> Path:
    if not _SAFE.fullmatch(site_id) or not _SAFE.fullmatch(device_id):
        raise HTTPException(422, "unsupported site_id or device_id")
    path = _root() / site_id / device_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _json_write(path: Path, value: object) -> None:
    _atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


class DiagnosticSnapshot(BaseModel):
    site_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    device_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    ts: datetime
    hostname: str = Field(default="", max_length=128)
    build: str = Field(default="", max_length=64)
    version: str = Field(default="", max_length=64)
    kernel: str = Field(default="", max_length=128)
    boot_id: str = Field(default="", max_length=128)
    uptime_seconds: float | None = Field(default=None, ge=0)
    local_status: dict = Field(default_factory=dict)
    support_bundle: dict = Field(default_factory=dict)
    cloud_link: dict = Field(default_factory=dict)


async def _latest_telemetry(site_id: str, device_id: str) -> dict | None:
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM telemetry WHERE site_id=? AND device_id=? ORDER BY id DESC LIMIT 1",
            (site_id, device_id),
        )
        row = await cursor.fetchone()
    return dict(row) if row else None


async def _refresh_server_report(site_id: str, device_id: str) -> dict:
    directory = _device_dir(site_id, device_id)
    snapshot_path = directory / "latest-pi-diagnostic.json"
    bundle_path = directory / "latest-pi-diagnostic.tar.gz"
    bundle_meta_path = directory / "latest-pi-diagnostic.meta.json"

    snapshot = json.loads(snapshot_path.read_text("utf-8")) if snapshot_path.exists() else None
    bundle_meta = json.loads(bundle_meta_path.read_text("utf-8")) if bundle_meta_path.exists() else None
    telemetry = await _latest_telemetry(site_id, device_id)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "server": {
            "hostname": socket.gethostname(),
            "kernel": platform.release(),
            "python": platform.python_version(),
            "closed_test_mode": settings.cloud_closed_test_mode,
            "remote_commands_enabled": settings.cloud_allow_commands,
            "database": str(Path(settings.cloud_db).name),
        },
        "identity": {"site_id": site_id, "device_id": device_id},
        "pi_snapshot": snapshot,
        "latest_telemetry": telemetry,
        "mirrored_bundle": {
            "available": bundle_path.is_file(),
            **(bundle_meta or {}),
        },
    }
    _json_write(directory / "server-diagnostic.json", report)
    return report


@router.post("/snapshot")
async def receive_snapshot(payload: DiagnosticSnapshot, x_api_token: str | None = Header(default=None)):
    """Receive the latest redacted Pi diagnostic state and regenerate the server report."""
    _auth(x_api_token, allow_closed_test=True)
    directory = _device_dir(payload.site_id, payload.device_id)
    data = payload.model_dump(mode="json")
    _json_write(directory / "latest-pi-diagnostic.json", data)

    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO diagnostic_events(ts,site_id,device_id,event_type,summary_json)
               VALUES(?,?,?,?,?)""",
            (payload.ts.isoformat(), payload.site_id, payload.device_id, "snapshot", json.dumps({
                "build": payload.build,
                "version": payload.version,
                "hostname": payload.hostname,
                "bundle": payload.support_bundle,
            }, separators=(",", ":"))),
        )
        await db.commit()
    await _refresh_server_report(payload.site_id, payload.device_id)
    return {"ok": True, "mirrored": True}


@router.put("/bundle/{site_id}/{device_id}")
async def receive_bundle(
    request: Request,
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    device_id: str = ApiPath(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$"),
    x_api_token: str | None = Header(default=None),
):
    """Mirror the newest redacted Pi support bundle. Uploads are capped and atomically replaced."""
    _auth(x_api_token, allow_closed_test=True)
    body = await request.body()
    if not body or len(body) > _MAX_BUNDLE_BYTES:
        raise HTTPException(413, "diagnostic bundle is empty or too large")
    if body[:2] != b"\x1f\x8b":
        raise HTTPException(415, "expected gzip support bundle")

    directory = _device_dir(site_id, device_id)
    digest = hashlib.sha256(body).hexdigest()
    bundle_path = directory / "latest-pi-diagnostic.tar.gz"
    _atomic_write(bundle_path, body)
    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "size": len(body),
        "sha256": digest,
        "filename": bundle_path.name,
    }
    _json_write(directory / "latest-pi-diagnostic.meta.json", meta)

    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO diagnostic_events(ts,site_id,device_id,event_type,summary_json)
               VALUES(?,?,?,?,?)""",
            (meta["updated_at"], site_id, device_id, "bundle", json.dumps(meta, separators=(",", ":"))),
        )
        await db.commit()
    await _refresh_server_report(site_id, device_id)
    return {"ok": True, **meta}


@router.get("/{site_id}/{device_id}")
async def diagnostic_report(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    device_id: str = ApiPath(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$"),
    x_api_token: str | None = Header(default=None),
):
    """Return the server-generated diagnostic report. Protected outside explicit closed-test mode."""
    _auth(x_api_token, allow_closed_test=True)
    return await _refresh_server_report(site_id, device_id)
