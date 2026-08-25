"""Central diagnostic mirror for Grow Central closed-test and production use."""
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
_MAX_BUNDLE_BYTES = 32 * 1024 * 1024
_MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def _normal_token_ok(token: str | None) -> bool:
    expected = settings.cloud_api_token.strip()
    candidate = (token or "").strip()
    return len(expected) >= 32 and not expected.startswith("CHANGE_ME") and bool(candidate) and secrets.compare_digest(candidate, expected)


def _allow_upload(token: str | None, site_id: str, device_id: str) -> None:
    if _normal_token_ok(token):
        return
    if settings.cloud_closed_test_mode:
        if site_id != settings.cloud_closed_test_site:
            raise HTTPException(403, "closed-test site is not allowed")
        if not device_id.startswith("raspberry-pi-"):
            raise HTTPException(403, "closed-test device id is not allowed")
        return
    raise HTTPException(401, "invalid api token")


def _require_read_token(token: str | None) -> None:
    """Diagnostic reads are never anonymous, including in closed-test mode."""
    candidate = (token or "").strip()
    expected = settings.cloud_diagnostic_read_token.strip()
    if len(expected) >= 32 and candidate and secrets.compare_digest(candidate, expected):
        return
    if _normal_token_ok(token):
        return
    raise HTTPException(401, "diagnostic read access requires an operator token")


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


class ContactPayload(DiagnosticSnapshot):
    reason: str = Field(default="connect", max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")


async def _latest_telemetry(site_id: str, device_id: str) -> dict | None:
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM telemetry WHERE site_id=? AND device_id=? ORDER BY id DESC LIMIT 1",
            (site_id, device_id),
        )
        row = await cursor.fetchone()
    return dict(row) if row else None


async def _record_event(ts: str, site_id: str, device_id: str, event_type: str, summary: dict) -> None:
    retention = max(100, int(settings.cloud_diagnostic_event_retention_rows))
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            "INSERT INTO diagnostic_events(ts,site_id,device_id,event_type,summary_json) VALUES(?,?,?,?,?)",
            (ts, site_id, device_id, event_type, json.dumps(summary, separators=(",", ":"))),
        )
        await db.execute(
            "DELETE FROM diagnostic_events WHERE id NOT IN (SELECT id FROM diagnostic_events ORDER BY id DESC LIMIT ?)",
            (retention,),
        )
        await db.commit()


async def _refresh_server_report(site_id: str, device_id: str) -> dict:
    directory = _device_dir(site_id, device_id)
    snapshot_path = directory / "latest-pi-diagnostic.json"
    contact_path = directory / "latest-contact.json"
    bundle_path = directory / "latest-pi-diagnostic.tar.gz"
    bundle_meta_path = directory / "latest-pi-diagnostic.meta.json"
    snapshot = json.loads(snapshot_path.read_text("utf-8")) if snapshot_path.exists() else None
    contact = json.loads(contact_path.read_text("utf-8")) if contact_path.exists() else None
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
            "diagnostic_root": str(_root()),
            "max_bundle_bytes": _MAX_BUNDLE_BYTES,
        },
        "identity": {"site_id": site_id, "device_id": device_id},
        "last_contact": contact,
        "pi_snapshot": snapshot,
        "latest_telemetry": telemetry,
        "mirrored_bundle": {"available": bundle_path.is_file(), **(bundle_meta or {})},
    }
    _json_write(directory / "server-diagnostic.json", report)
    return report


@router.post("/contact")
async def receive_contact(
    payload: ContactPayload,
    request: Request,
    x_api_token: str | None = Header(default=None),
):
    """Bidirectional online handshake: store the Pi state and return server state."""
    _allow_upload(x_api_token, payload.site_id, payload.device_id)
    directory = _device_dir(payload.site_id, payload.device_id)
    data = payload.model_dump(mode="json")
    data["source"] = request.client.host if request.client else "unknown"
    encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > _MAX_SNAPSHOT_BYTES:
        raise HTTPException(413, "contact diagnostic too large")
    _atomic_write(directory / "latest-contact.json", encoded + b"\n")
    await _record_event(
        payload.ts.isoformat(), payload.site_id, payload.device_id, "contact",
        {
            "reason": payload.reason,
            "build": payload.build,
            "version": payload.version,
            "hostname": payload.hostname,
            "source": data["source"],
        },
    )
    report = await _refresh_server_report(payload.site_id, payload.device_id)
    return {
        "ok": True,
        "contact_accepted": True,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "server": report["server"],
        "mirrored_bundle": report["mirrored_bundle"],
    }


@router.post("/snapshot")
async def receive_snapshot(
    payload: DiagnosticSnapshot,
    request: Request,
    x_api_token: str | None = Header(default=None),
):
    _allow_upload(x_api_token, payload.site_id, payload.device_id)
    data = payload.model_dump(mode="json")
    encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > _MAX_SNAPSHOT_BYTES:
        raise HTTPException(413, "diagnostic snapshot too large")
    directory = _device_dir(payload.site_id, payload.device_id)
    _atomic_write(directory / "latest-pi-diagnostic.json", encoded + b"\n")
    await _record_event(
        payload.ts.isoformat(), payload.site_id, payload.device_id, "snapshot",
        {
            "build": payload.build,
            "version": payload.version,
            "hostname": payload.hostname,
            "bundle": payload.support_bundle,
            "source": request.client.host if request.client else "unknown",
        },
    )
    await _refresh_server_report(payload.site_id, payload.device_id)
    return {"ok": True, "mirrored": True}


@router.put("/bundle/{site_id}/{device_id}")
async def receive_bundle(
    request: Request,
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    device_id: str = ApiPath(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$"),
    x_api_token: str | None = Header(default=None),
    x_content_sha256: str | None = Header(default=None),
):
    _allow_upload(x_api_token, site_id, device_id)
    body = await request.body()
    if not body or len(body) > _MAX_BUNDLE_BYTES:
        raise HTTPException(413, "diagnostic bundle is empty or too large")
    if body[:2] != b"\x1f\x8b":
        raise HTTPException(415, "expected gzip support bundle")
    digest = hashlib.sha256(body).hexdigest()
    if x_content_sha256 and not secrets.compare_digest(x_content_sha256.lower(), digest):
        raise HTTPException(400, "diagnostic bundle checksum mismatch")

    directory = _device_dir(site_id, device_id)
    bundle_path = directory / "latest-pi-diagnostic.tar.gz"
    _atomic_write(bundle_path, body)
    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "size": len(body),
        "sha256": digest,
        "filename": bundle_path.name,
        "source": request.client.host if request.client else "unknown",
    }
    _json_write(directory / "latest-pi-diagnostic.meta.json", meta)
    await _record_event(meta["updated_at"], site_id, device_id, "bundle", meta)
    await _refresh_server_report(site_id, device_id)
    return {"ok": True, **meta}


@router.get("/{site_id}/{device_id}")
async def diagnostic_report(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    device_id: str = ApiPath(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$"),
    x_api_token: str | None = Header(default=None),
):
    _require_read_token(x_api_token)
    return await _refresh_server_report(site_id, device_id)
