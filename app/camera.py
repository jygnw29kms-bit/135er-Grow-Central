"""Local UVC camera diagnostics, snapshots and guarded controls.

Reference hardware: Logitech C920 connected directly to the Raspberry Pi.
Other V4L2/UVC cameras are supported conservatively: Grow Central discovers the
controls the camera actually advertises and never accepts arbitrary device paths
or arbitrary control names from the browser.
"""
from __future__ import annotations

import asyncio
import glob
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/camera", tags=["camera"])
CONTROL_RE = re.compile(r"^\s*([a-zA-Z0-9_]+)\s+0x[0-9a-fA-F]+\s+\(([^)]+)\)\s*:\s*(.*)$")
PAIR_RE = re.compile(r"([a-zA-Z_]+)=(-?\d+)")
STREAM_LOCK = asyncio.Lock()


class CameraControlRequest(BaseModel):
    camera_id: str = Field(pattern=r"^cam\d+$")
    control: str = Field(pattern=r"^[a-zA-Z0-9_]+$", min_length=1, max_length=80)
    value: int


def _run(arguments: list[str], timeout: int = 8) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(arguments, capture_output=True, timeout=timeout, check=False)


def _candidate_devices() -> list[str]:
    configured = os.getenv("GC_CAMERA_DEVICE", "").strip()
    if configured:
        return [configured]
    return sorted(glob.glob("/dev/video*"))


def _camera_map() -> dict[str, str]:
    return {f"cam{index}": device for index, device in enumerate(_candidate_devices())}


def _resolve_camera(camera_id: str | None) -> tuple[str, str]:
    mapping = _camera_map()
    if camera_id:
        try:
            return camera_id, mapping[camera_id]
        except KeyError as exc:
            raise RuntimeError("unknown camera id") from exc
    status = _status_sync()
    preferred = status.get("selected_camera_id")
    if preferred and preferred in mapping:
        return preferred, mapping[preferred]
    raise RuntimeError("no capture-capable camera detected")


def _device_info(camera_id: str, device: str) -> dict[str, Any]:
    path = Path(device)
    row: dict[str, Any] = {
        "id": camera_id,
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
    mapping = _camera_map()
    devices = [_device_info(camera_id, device) for camera_id, device in mapping.items()]
    preferred = next((row for row in devices if row["c920_match"] and row["capture_capable"]), None)
    if preferred is None:
        preferred = next((row for row in devices if row["capture_capable"]), None)
    return {
        "enabled": enabled,
        "reference_model": "Logitech C920",
        "connected_directly_to_pi": True,
        "count": len(devices),
        "devices": devices,
        "selected_camera_id": preferred["id"] if preferred else None,
        "selected_device": preferred["device"] if preferred else None,
        "selected_is_c920": bool(preferred and preferred["c920_match"]),
        "ready": bool(enabled and preferred and preferred["readable"]),
    }


def _controls_sync(camera_id: str | None) -> dict[str, Any]:
    resolved_id, device = _resolve_camera(camera_id)
    try:
        result = _run(["v4l2-ctl", "--device", device, "--list-ctrls-menus"], timeout=8)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("camera control query timeout") from exc
    except OSError as exc:
        raise RuntimeError("v4l2-ctl unavailable") from exc
    text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(text.strip()[:300] or "camera control query failed")
    controls: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        match = CONTROL_RE.match(line)
        if match:
            name, kind, rest = match.groups()
            pairs = {key: int(value) for key, value in PAIR_RE.findall(rest)}
            flags = []
            if "flags=" in rest:
                flags = [item.strip() for item in rest.split("flags=", 1)[1].split(",") if item.strip()]
            current = {
                "name": name,
                "type": kind.strip(),
                "min": pairs.get("min"),
                "max": pairs.get("max"),
                "step": pairs.get("step", 1),
                "default": pairs.get("default"),
                "value": pairs.get("value"),
                "flags": flags,
                "menu": [],
                "writable": not any(flag in {"read-only", "inactive", "disabled"} for flag in flags),
            }
            controls.append(current)
            continue
        if current and current["type"] in {"menu", "integer menu"}:
            menu_match = re.match(r"^\s+(-?\d+):\s+(.+?)\s*$", line)
            if menu_match:
                current["menu"].append({"value": int(menu_match.group(1)), "label": menu_match.group(2)})
    return {"camera_id": resolved_id, "device": device, "controls": controls}


def _set_control_sync(request: CameraControlRequest) -> dict[str, Any]:
    controls = _controls_sync(request.camera_id)
    control = next((row for row in controls["controls"] if row["name"] == request.control), None)
    if not control:
        raise ValueError("camera does not expose this control")
    if not control["writable"]:
        raise PermissionError("camera control is read-only or inactive")
    minimum, maximum = control.get("min"), control.get("max")
    if minimum is not None and request.value < minimum:
        raise ValueError(f"value below minimum {minimum}")
    if maximum is not None and request.value > maximum:
        raise ValueError(f"value above maximum {maximum}")
    if control["menu"] and request.value not in {item["value"] for item in control["menu"]}:
        raise ValueError("invalid menu value")
    result = _run(["v4l2-ctl", "--device", controls["device"], "--set-ctrl", f"{request.control}={request.value}"], timeout=8)
    text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(text.strip()[:300] or "camera control write failed")
    refreshed = _controls_sync(request.camera_id)
    updated = next((row for row in refreshed["controls"] if row["name"] == request.control), None)
    return {"ok": True, "camera_id": request.camera_id, "control": updated}


def _snapshot_sync(camera_id: str | None) -> tuple[bytes, str, str]:
    status = _status_sync()
    if not status["enabled"]:
        raise RuntimeError("camera disabled")
    resolved_id, device = _resolve_camera(camera_id)
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
    return result.stdout, resolved_id, device


@router.get("/status")
async def camera_status():
    return await asyncio.to_thread(_status_sync)


@router.get("/controls")
async def camera_controls(camera_id: str | None = None):
    try:
        return await asyncio.to_thread(_controls_sync, camera_id)
    except TimeoutError as exc:
        raise HTTPException(504, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/controls", dependencies=[Depends(require_write_auth)])
async def camera_control_set(request: CameraControlRequest):
    try:
        result = await asyncio.to_thread(_set_control_sync, request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    append_audit("camera.control.set", camera_id=request.camera_id, control=request.control, value=request.value)
    return result


@router.get("/snapshot")
async def camera_snapshot(camera_id: str | None = None):
    try:
        data, resolved_id, device = await asyncio.to_thread(_snapshot_sync, camera_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-GrowCentral-Camera": resolved_id, "X-GrowCentral-Video-Device": device},
    )


async def _mjpeg_stream(camera_id: str | None):
    resolved_id, device = _resolve_camera(camera_id)
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480", "-framerate", "10",
            "-i", device, "-an", "-c:v", "copy", "-f", "mpjpeg", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if process.stdout is None:
            return
        while chunk := await process.stdout.read(64 * 1024):
            yield chunk
    finally:
        if process is not None and process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            else:
                try:
                    await asyncio.wait_for(process.wait(), timeout=2)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
        if STREAM_LOCK.locked():
            STREAM_LOCK.release()
        append_audit("camera.stream.closed", camera_id=resolved_id)


@router.get("/stream")
async def camera_stream(camera_id: str | None = None):
    if os.getenv("GC_CAMERA_ENABLED", "true").lower() != "true":
        raise HTTPException(503, "camera disabled")
    try:
        resolved_id, device = _resolve_camera(camera_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not os.access(device, os.R_OK):
        raise HTTPException(403, f"camera device is not readable: {device}")
    try:
        await asyncio.wait_for(STREAM_LOCK.acquire(), timeout=0.05)
    except asyncio.TimeoutError:
        raise HTTPException(409, "Es läuft bereits ein Kamera-Livebild")
    append_audit("camera.stream.opened", camera_id=resolved_id)
    try:
        return StreamingResponse(
            _mjpeg_stream(resolved_id),
            media_type="multipart/x-mixed-replace; boundary=ffmpeg",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-GrowCentral-Camera": resolved_id},
        )
    except Exception:
        STREAM_LOCK.release()
        raise
