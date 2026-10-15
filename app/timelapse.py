"""Bounded local timelapse capture for Grow Central.

A timelapse is a sequence of local JPEG snapshots. Jobs are intentionally
bounded by interval and frame count; no unbounded video recording is started.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.camera import _snapshot_sync, _stop_active_stream
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/timelapse", tags=["timelapse"])
ROOT = Path(os.getenv("GC_TIMELAPSE_DIR", "/var/lib/135er-grow-central/timelapse"))
MAX_RUNS = max(3, min(int(os.getenv("GC_TIMELAPSE_MAX_RUNS", "20")), 100))
_RUN_ID = re.compile(r"^run_[0-9a-f]{12}$")
_FRAME = re.compile(r"^frame_[0-9]{5}\.jpg$")


class StartBody(BaseModel):
    interval_seconds: int = Field(default=300, ge=15, le=86400)
    max_frames: int = Field(default=72, ge=2, le=1000)
    camera_id: str | None = Field(default=None, max_length=128)


class _Job:
    def __init__(self):
        self.task: asyncio.Task | None = None
        self.run_id: str | None = None
        self.interval_seconds = 0
        self.max_frames = 0
        self.frames = 0
        self.started_at: str | None = None
        self.last_frame_at: str | None = None
        self.camera_id: str | None = None
        self.error: str | None = None
        self.stop_requested = False

    def public(self) -> dict[str, Any]:
        return {
            "active": bool(self.task and not self.task.done()),
            "run_id": self.run_id,
            "interval_seconds": self.interval_seconds,
            "max_frames": self.max_frames,
            "frames": self.frames,
            "started_at": self.started_at,
            "last_frame_at": self.last_frame_at,
            "camera_id": self.camera_id,
            "error": self.error,
        }


job = _Job()
lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_run(run_id: str) -> Path:
    if not _RUN_ID.fullmatch(run_id):
        raise HTTPException(404, "Zeitraffer-Lauf nicht gefunden")
    path = ROOT / run_id
    if not path.is_dir():
        raise HTTPException(404, "Zeitraffer-Lauf nicht gefunden")
    return path


def _metadata(path: Path) -> dict[str, Any]:
    meta = path / "meta.json"
    try:
        value = json.loads(meta.read_text(encoding="utf-8"))
        if isinstance(value, dict): return value
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _write_meta(path: Path, payload: dict[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    temp = path / ".meta.tmp"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o640)
    os.replace(temp, path / "meta.json")


def _prune_runs() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    runs = sorted((p for p in ROOT.iterdir() if p.is_dir() and _RUN_ID.fullmatch(p.name)), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in runs[MAX_RUNS:]:
        shutil.rmtree(old, ignore_errors=True)


async def _capture_loop(run_id: str, body: StartBody) -> None:
    path = ROOT / run_id
    error = None
    try:
        for index in range(body.max_frames):
            if job.stop_requested: break
            started = time.monotonic()
            try:
                await _stop_active_stream("timelapse")
                data, resolved_id, _device, mode = await asyncio.to_thread(_snapshot_sync, body.camera_id, None, None)
                frame = path / f"frame_{index + 1:05d}.jpg"
                frame.write_bytes(data); os.chmod(frame, 0o640)
                job.frames += 1; job.last_frame_at = _now(); job.camera_id = resolved_id
                _write_meta(path, {"run_id": run_id, "started_at": job.started_at, "last_frame_at": job.last_frame_at, "interval_seconds": body.interval_seconds, "max_frames": body.max_frames, "frames": job.frames, "camera_id": resolved_id, "resolution": f"{mode['width']}x{mode['height']}", "active": True, "error": None})
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                job.error = error
                break
            if index + 1 >= body.max_frames or job.stop_requested: break
            delay = max(0.0, body.interval_seconds - (time.monotonic() - started))
            await asyncio.sleep(delay)
    finally:
        _write_meta(path, {**_metadata(path), "active": False, "finished_at": _now(), "frames": job.frames, "error": error})
        append_audit("timelapse.finished", run_id=run_id, frames=job.frames, stopped=job.stop_requested, failed=bool(error))
        job.task = None
        _prune_runs()


@router.get("/status")
async def status():
    return job.public()


@router.get("/runs")
async def runs():
    ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted((p for p in ROOT.iterdir() if p.is_dir() and _RUN_ID.fullmatch(p.name)), key=lambda p: p.stat().st_mtime, reverse=True):
        meta = _metadata(path); frames = sorted(p.name for p in path.glob("frame_*.jpg") if _FRAME.fullmatch(p.name))
        rows.append({**meta, "run_id": path.name, "frames": len(frames), "preview": frames[-1] if frames else None})
    return {"runs": rows[:MAX_RUNS]}


@router.get("/runs/{run_id}/frames/{filename}")
async def frame(run_id: str, filename: str):
    path = _safe_run(run_id)
    if not _FRAME.fullmatch(filename): raise HTTPException(404, "Frame nicht gefunden")
    target = path / filename
    if not target.is_file(): raise HTTPException(404, "Frame nicht gefunden")
    return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/start", dependencies=[Depends(require_write_auth)])
async def start(body: StartBody):
    async with lock:
        if job.task and not job.task.done(): raise HTTPException(409, "Zeitraffer l?uft bereits")
        ROOT.mkdir(parents=True, exist_ok=True); _prune_runs()
        run_id = "run_" + uuid.uuid4().hex[:12]; path = ROOT / run_id; path.mkdir(mode=0o750)
        job.run_id = run_id; job.interval_seconds = body.interval_seconds; job.max_frames = body.max_frames; job.frames = 0; job.started_at = _now(); job.last_frame_at = None; job.camera_id = body.camera_id; job.error = None; job.stop_requested = False
        _write_meta(path, {"run_id": run_id, "started_at": job.started_at, "interval_seconds": body.interval_seconds, "max_frames": body.max_frames, "frames": 0, "camera_id": body.camera_id, "active": True, "error": None})
        job.task = asyncio.create_task(_capture_loop(run_id, body))
        append_audit("timelapse.started", run_id=run_id, interval_seconds=body.interval_seconds, max_frames=body.max_frames)
        return {"ok": True, **job.public()}


@router.post("/stop", dependencies=[Depends(require_write_auth)])
async def stop():
    async with lock:
        if not job.task or job.task.done(): return {"ok": True, "active": False}
        job.stop_requested = True
        return {"ok": True, **job.public()}
