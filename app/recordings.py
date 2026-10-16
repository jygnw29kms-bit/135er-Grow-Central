"""Bounded local video recordings for Grow Central cameras.

Recordings share the camera stream lease with snapshots/live view/timelapse so a
single UVC device is never driven by competing ffmpeg processes. Clips are
finite by construction and retained locally with a bounded history.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.camera import (
    _claim_stream,
    _register_stream_process,
    _release_stream,
    _resolve_capture_mode,
    _stop_active_stream,
)
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])
ROOT = Path(os.getenv("GC_RECORDINGS_DIR", "/var/lib/135er-grow-central/recordings"))
def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


MAX_CLIPS = _bounded_env_int("GC_RECORDINGS_MAX_CLIPS", 20, 3, 100)
MAX_DURATION_SECONDS = _bounded_env_int("GC_RECORDINGS_MAX_DURATION_SECONDS", 300, 30, 1800)
MAX_CLIP_BYTES = _bounded_env_int("GC_RECORDINGS_MAX_CLIP_MB", 1024, 64, 8192) * 1024 * 1024
MIN_FREE_BYTES = 512 * 1024 * 1024
_CLIP_ID = re.compile(r"^clip_[0-9a-f]{12}$")


class StartBody(BaseModel):
    duration_seconds: int = Field(default=60, ge=5, le=MAX_DURATION_SECONDS)
    camera_id: str | None = Field(default=None, pattern=r"^cam\d+$")


class _Job:
    def __init__(self):
        self.task: asyncio.Task | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.clip_id: str | None = None
        self.camera_id: str | None = None
        self.duration_seconds = 0
        self.started_at: str | None = None
        self.stop_requested = False
        self.error: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "active": bool(self.task and not self.task.done()),
            "clip_id": self.clip_id,
            "camera_id": self.camera_id,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "stop_requested": self.stop_requested,
            "error": self.error,
        }


job = _Job()
lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_clip_id() -> str:
    for _ in range(16):
        clip_id = "clip_" + uuid.uuid4().hex[:12]
        if not (ROOT / clip_id).exists():
            return clip_id
    raise RuntimeError("Keine freie Aufnahme-ID verf\u00fcgbar")


def _safe_clip(clip_id: str) -> Path:
    if not _CLIP_ID.fullmatch(clip_id):
        raise HTTPException(404, "Aufnahme nicht gefunden")
    path = ROOT / clip_id
    if path.is_symlink() or not path.is_dir():
        raise HTTPException(404, "Aufnahme nicht gefunden")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except (OSError, ValueError):
        raise HTTPException(404, "Aufnahme nicht gefunden") from None
    return path


def _safe_target(path: Path) -> Path | None:
    target = path / "clip.mkv"
    if target.is_symlink() or not target.is_file():
        return None
    try:
        target.resolve().relative_to(path.resolve())
    except (OSError, ValueError):
        return None
    return target


def _read_meta(path: Path) -> dict[str, Any]:
    try:
        meta_path = path / "meta.json"
        if meta_path.is_symlink():
            return {}
        value = json.loads(meta_path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_meta(path: Path, payload: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o750)
    temp = path / ".meta.tmp"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(temp, 0o640)
    os.replace(temp, path / "meta.json")


def _clip_rows() -> list[tuple[Path, dict[str, Any]]]:
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o750)
    rows = []
    for path in ROOT.iterdir():
        if path.is_symlink() or not path.is_dir() or not _CLIP_ID.fullmatch(path.name):
            continue
        meta = _read_meta(path)
        target = _safe_target(path)
        active_now = bool(job.clip_id == path.name and job.task and not job.task.done())
        if meta.get("active") and not active_now:
            meta["active"] = False
            meta["interrupted"] = True
            meta["error"] = meta.get("error") or "Aufnahme durch Dienstneustart unterbrochen"
        meta["clip_id"] = path.name
        meta["bytes"] = target.stat().st_size if target else 0
        meta["download_ready"] = bool(target and target.stat().st_size > 0)
        rows.append((path, meta))
    rows.sort(key=lambda row: row[0].stat().st_mtime, reverse=True)
    return rows


def _prune() -> None:
    active = job.clip_id if job.task and not job.task.done() else None
    kept = 0
    for path, _meta in _clip_rows():
        if path.name == active:
            continue
        kept += 1
        if kept > MAX_CLIPS:
            shutil.rmtree(path, ignore_errors=True)


async def _record(clip_id: str, body: StartBody) -> None:
    token = object()
    path = ROOT / clip_id
    target = path / "clip.mkv"
    process: asyncio.subprocess.Process | None = None
    stderr_task: asyncio.Task[bytes] | None = None
    error: str | None = None
    resolved_id: str | None = None
    mode: dict[str, Any] | None = None
    try:
        await _stop_active_stream("recording")
        resolved_id, device, mode = _resolve_capture_mode(body.camera_id, None, None)
        job.camera_id = resolved_id
        await _claim_stream(token)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "v4l2", "-input_format", "mjpeg",
            "-video_size", f'{mode["width"]}x{mode["height"]}',
            "-framerate", str(mode["selected_fps"]), "-i", device,
            "-t", str(body.duration_seconds), "-an", "-c:v", "copy",
            "-fs", str(MAX_CLIP_BYTES), "-f", "matroska", str(target),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        job.process = process
        if not await _register_stream_process(token, process):
            raise RuntimeError("Kamera wurde bereits von einem anderen Vorgang \u00fcbernommen")
        if process.stderr is not None:
            stderr_task = asyncio.create_task(process.stderr.read())
        returncode = await process.wait()
        detail = ""
        if stderr_task is not None:
            detail = (await stderr_task).decode("utf-8", errors="replace").strip()[:400]
        if returncode not in (0, 255) and not job.stop_requested:
            raise RuntimeError(detail or f"ffmpeg exit {returncode}")
        if target.is_file() and target.stat().st_size > 0 and os.name != "nt":
            os.chmod(target, 0o640)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        job.error = error
    finally:
        if process is not None:
            await _release_stream(token, process)
        finished = _now()
        bytes_written = target.stat().st_size if target.is_file() else 0
        _write_meta(path, {
            **_read_meta(path),
            "clip_id": clip_id,
            "camera_id": resolved_id or job.camera_id,
            "duration_seconds": body.duration_seconds,
            "resolution": f'{mode["width"]}x{mode["height"]}' if mode else None,
            "started_at": job.started_at,
            "finished_at": finished,
            "active": False,
            "stopped": job.stop_requested,
            "bytes": bytes_written,
            "error": error,
        })
        append_audit("camera.recording.finished", clip_id=clip_id, stopped=job.stop_requested, failed=bool(error), bytes=bytes_written)
        job.process = None
        job.task = None
        _prune()


@router.get("/status")
async def status():
    return job.public()


@router.get("")
async def list_recordings():
    return {"recordings": [meta for _path, meta in _clip_rows()[:MAX_CLIPS]], "max_clips": MAX_CLIPS, "max_duration_seconds": MAX_DURATION_SECONDS, "max_clip_bytes": MAX_CLIP_BYTES}


@router.post("/start", dependencies=[Depends(require_write_auth)])
async def start(body: StartBody):
    async with lock:
        if job.task and not job.task.done():
            raise HTTPException(409, "Kameraaufnahme l\u00e4uft bereits")
        ROOT.mkdir(parents=True, exist_ok=True, mode=0o750)
        _prune()
        if shutil.disk_usage(ROOT).free < MIN_FREE_BYTES:
            raise HTTPException(507, "Zu wenig freier Speicher f\u00fcr eine Videoaufnahme")
        clip_id = _new_clip_id()
        path = ROOT / clip_id
        path.mkdir(mode=0o750)
        job.clip_id = clip_id
        job.camera_id = body.camera_id
        job.duration_seconds = body.duration_seconds
        job.started_at = _now()
        job.stop_requested = False
        job.error = None
        _write_meta(path, {"clip_id": clip_id, "camera_id": body.camera_id, "duration_seconds": body.duration_seconds, "started_at": job.started_at, "active": True, "bytes": 0, "error": None})
        job.task = asyncio.create_task(_record(clip_id, body), name=f"growcentral-recording-{clip_id}")
        append_audit("camera.recording.started", clip_id=clip_id, duration_seconds=body.duration_seconds, camera_id=body.camera_id)
        return {"ok": True, **job.public()}


@router.post("/stop", dependencies=[Depends(require_write_auth)])
async def stop():
    async with lock:
        if not job.task or job.task.done():
            return {"ok": True, "active": False}
        job.stop_requested = True
        process = job.process
    if process is not None and process.returncode is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
    return {"ok": True, **job.public()}


@router.get("/{clip_id}/download")
async def download(clip_id: str):
    path = _safe_clip(clip_id)
    target = _safe_target(path)
    if target is None or target.stat().st_size <= 0:
        raise HTTPException(404, "Aufnahmedatei nicht verf\u00fcgbar")
    return FileResponse(target, media_type="video/x-matroska", filename=f"Grow-Central-{clip_id}.mkv", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/{clip_id}", dependencies=[Depends(require_write_auth)])
async def delete(clip_id: str):
    path = _safe_clip(clip_id)
    if job.clip_id == clip_id and job.task and not job.task.done():
        raise HTTPException(409, "Aktive Aufnahme kann nicht gel\u00f6scht werden")
    shutil.rmtree(path)
    append_audit("camera.recording.deleted", clip_id=clip_id)
    return {"ok": True, "clip_id": clip_id}
