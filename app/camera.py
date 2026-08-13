"""Local USB camera diagnostics and snapshot API.

Reference hardware: Logitech C920 connected directly to the Raspberry Pi.
The API performs read-only detection and single-frame capture. It never exposes
a device path supplied by the browser.
"""
from __future__ import annotations

import asyncio
import glob
import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/v1/camera", tags=["camera"])


def _run(arguments: list[str], timeout: int = 8) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(arguments, capture_output=True, timeout=timeout, check=False)


def _candidate_devices() -> list[str]:
    configured = os.getenv("GC_CAMERA_DEVICE", "").strip()
    if configured:
        return [configured]
    return sorted(glob.glob("/dev/video*"))


def _device_info(device: str) -> dict[str, Any]:
    path = Path(device)
    row: dict[str, Any] = {
        "device": device,
        "exists": path.exists(),
        "readable": os.access(device, os.R_OK) if path.exists() else False,
        "writable": os.access(device, os.W_OK) if path.exists() else False,
        "name": None,
        "driver": None,
        "card": None,
        "bus_info": None,
        "c920_match": False,
        "capture_capable": False,
        "error": None,
    }
    if not path.exists():
        return row
    try:
        result = _run(["v4l2-ctl", "--device", device, "--all"], timeout=6)
    except (OSError, subprocess.TimeoutExpired) as exc:
        row["error"] = type(exc).__name__
        return row
    text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        row["error"] = text.strip()[:240] or "v4l2 query failed"
        return row
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("driver name") and ":" in stripped:
            row["driver"] = stripped.split(":", 1)[1].strip()
        elif lower.startswith("card type") and ":" in stripped:
            row["card"] = stripped.split(":", 1)[1].strip()
            row["name"] = row["card"]
        elif lower.startswith("bus info") and ":" in stripped:
            row["bus_info"] = stripped.split(":", 1)[1].strip()
        elif "video capture" in lower:
            row["capture_capable"] = True
    haystack = " ".join(str(value or "") for value in (row["name"], row["card"], text[:4000])).lower()
    row["c920_match"] = "c920" in haystack or "hd pro webcam" in haystack or "logitech" in haystack
    return row


def _status_sync() -> dict[str, Any]:
    enabled = os.getenv("GC_CAMERA_ENABLED", "true").lower() == "true"
    devices = [_device_info(device) for device in _candidate_devices()]
    preferred = next((row for row in devices if row["c920_match"] and row["capture_capable"]), None)
    if preferred is None:
        preferred = next((row for row in devices if row["capture_capable"]), None)
    return {
        "enabled": enabled,
        "reference_model": "Logitech C920",
        "connected_directly_to_pi": True,
        "count": len(devices),
        "devices": devices,
        "selected_device": preferred["device"] if preferred else None,
        "selected_is_c920": bool(preferred and preferred["c920_match"]),
        "ready": bool(enabled and preferred and preferred["readable"]),
    }


def _snapshot_sync() -> tuple[bytes, str]:
    status = _status_sync()
    if not status["enabled"]:
        raise RuntimeError("camera disabled")
    device = status["selected_device"]
    if not device:
        raise RuntimeError("no capture-capable camera detected")
    if not os.access(device, os.R_OK):
        raise PermissionError(f"camera device is not readable: {device}")
    try:
        result = _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "v4l2", "-i", device,
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
        ], timeout=12)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("camera capture timeout") from exc
    except OSError as exc:
        raise RuntimeError("ffmpeg unavailable") from exc
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:300]
        raise RuntimeError(detail or "camera capture failed")
    return result.stdout, device


@router.get("/status")
async def camera_status():
    return await asyncio.to_thread(_status_sync)


@router.get("/snapshot")
async def camera_snapshot():
    try:
        data, device = await asyncio.to_thread(_snapshot_sync)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-GrowCentral-Camera": device},
    )
