"""Local UVC camera diagnostics, snapshots and guarded controls.

Reference hardware: Logitech C920 connected directly to the Raspberry Pi.
Other MJPEG-capable V4L2/UVC cameras are supported conservatively: Grow Central
discovers the controls the camera actually advertises and never accepts arbitrary
device paths or arbitrary control names from the browser.
"""
from __future__ import annotations

import asyncio
import glob
import os
import re
import subprocess
import threading
import time
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
DISCOVERY_CACHE_SECONDS = 15.0
_DISCOVERY_LOCK = threading.Lock()
_DISCOVERY_CACHE: tuple[float, str, list[dict[str, Any]], int] | None = None
_STREAM_STATE_LOCK = asyncio.Lock()
_ACTIVE_STREAM_TOKEN: object | None = None
_ACTIVE_STREAM_PROCESS: asyncio.subprocess.Process | None = None


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
    devices, _ignored = _discover_devices_sync()
    return {row["id"]: row["device"] for row in devices}


def _resolve_camera(camera_id: str | None) -> tuple[str, str]:
    mapping = _camera_map()
    if camera_id:
        try:
            return camera_id, mapping[camera_id]
        except KeyError as exc:
            raise RuntimeError("unknown camera id") from exc
    if mapping:
        return next(iter(mapping.items()))
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
        "stream_capable": False,
        "pixel_formats": [],
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
    if row["capture_capable"]:
        try:
            formats = _run(["v4l2-ctl", "--device", device, "--list-formats-ext"], timeout=6)
        except (OSError, subprocess.TimeoutExpired) as exc:
            row["error"] = type(exc).__name__
        else:
            formats_text = (formats.stdout + b"\n" + formats.stderr).decode("utf-8", errors="replace")
            row["pixel_formats"] = list(dict.fromkeys(re.findall(r"'([A-Z0-9]{4})'", formats_text)))
            # The live endpoint copies MJPEG without transcoding. Hiding nodes
            # without native MJPEG avoids advertising devices that can only fail
            # (or would require expensive real-time transcoding on a Pi 3B).
            row["stream_capable"] = formats.returncode == 0 and "MJPG" in row["pixel_formats"]
    return row


def _discover_devices_sync(*, force: bool = False) -> tuple[list[dict[str, Any]], int]:
    """Return only real capture nodes; hide Pi codec/ISP and metadata nodes."""
    global _DISCOVERY_CACHE
    configured = os.getenv("GC_CAMERA_DEVICE", "").strip()
    now = time.monotonic()
    with _DISCOVERY_LOCK:
        if (
            not force
            and _DISCOVERY_CACHE
            and _DISCOVERY_CACHE[1] == configured
            and now - _DISCOVERY_CACHE[0] < DISCOVERY_CACHE_SECONDS
        ):
            return _DISCOVERY_CACHE[2], _DISCOVERY_CACHE[3]

        discovered: list[dict[str, Any]] = []
        ignored = 0
        for device in _candidate_devices():
            row = _device_info("", device)
            bus_info = str(row.get("bus_info") or "").lower()
            driver = str(row.get("driver") or "").lower()
            is_usb_uvc = "usb" in bus_info or driver == "uvcvideo"
            allowed = bool(
                row["capture_capable"]
                and row["stream_capable"]
                and row["readable"]
                and (configured or is_usb_uvc)
            )
            if not allowed:
                ignored += 1
                continue
            row["id"] = f"cam{len(discovered)}"
            discovered.append(row)
        discovered.sort(key=lambda row: (not row["c920_match"], row["device"]))
        for index, row in enumerate(discovered):
            row["id"] = f"cam{index}"
        _DISCOVERY_CACHE = (now, configured, discovered, ignored)
        return discovered, ignored


def _status_sync(*, force: bool = False) -> dict[str, Any]:
    enabled = os.getenv("GC_CAMERA_ENABLED", "true").lower() == "true"
    devices, ignored = _discover_devices_sync(force=force)
    preferred = devices[0] if devices else None
    return {
        "enabled": enabled,
        "reference_model": "Logitech C920",
        "connected_directly_to_pi": True,
        "count": len(devices),
        "ignored_video_nodes": ignored,
        "devices": devices,
        "selected_camera_id": preferred["id"] if preferred else None,
        "selected_device": preferred["device"] if preferred else None,
        "selected_is_c920": bool(preferred and preferred["c920_match"]),
        "ready": bool(enabled and preferred and preferred["stream_capable"]),
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
async def camera_status(refresh: bool = False):
    return await asyncio.to_thread(_status_sync, force=refresh)


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
    await _stop_active_stream("snapshot")
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


async def _terminate_process(process: asyncio.subprocess.Process | None) -> None:
    if process is None or process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


async def _stop_active_stream(reason: str) -> bool:
    global _ACTIVE_STREAM_TOKEN, _ACTIVE_STREAM_PROCESS
    async with _STREAM_STATE_LOCK:
        token = _ACTIVE_STREAM_TOKEN
        process = _ACTIVE_STREAM_PROCESS
        _ACTIVE_STREAM_TOKEN = None
        _ACTIVE_STREAM_PROCESS = None
    await _terminate_process(process)
    if token is not None:
        append_audit("camera.stream.stopped", reason=reason)
        return True
    return False


async def _claim_stream(token: object) -> None:
    global _ACTIVE_STREAM_TOKEN, _ACTIVE_STREAM_PROCESS
    async with _STREAM_STATE_LOCK:
        old_process = _ACTIVE_STREAM_PROCESS
        replaced = _ACTIVE_STREAM_TOKEN is not None
        _ACTIVE_STREAM_TOKEN = token
        _ACTIVE_STREAM_PROCESS = None
    await _terminate_process(old_process)
    if replaced:
        append_audit("camera.stream.replaced")


async def _register_stream_process(token: object, process: asyncio.subprocess.Process) -> bool:
    global _ACTIVE_STREAM_PROCESS
    async with _STREAM_STATE_LOCK:
        if _ACTIVE_STREAM_TOKEN is not token:
            return False
        _ACTIVE_STREAM_PROCESS = process
        return True


async def _release_stream(token: object, process: asyncio.subprocess.Process) -> None:
    global _ACTIVE_STREAM_TOKEN, _ACTIVE_STREAM_PROCESS
    async with _STREAM_STATE_LOCK:
        if _ACTIVE_STREAM_TOKEN is token:
            _ACTIVE_STREAM_TOKEN = None
            _ACTIVE_STREAM_PROCESS = None
    await _terminate_process(process)


async def _mjpeg_stream(resolved_id: str, device: str):
    token = object()
    process: asyncio.subprocess.Process | None = None
    stderr_task: asyncio.Task[bytes] | None = None
    await _claim_stream(token)
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480", "-framerate", "10",
            "-i", device, "-an", "-c:v", "copy", "-f", "mpjpeg", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if not await _register_stream_process(token, process):
            await _terminate_process(process)
            return
        if process.stderr is not None:
            stderr_task = asyncio.create_task(process.stderr.read())
        if process.stdout is None:
            return
        while chunk := await process.stdout.read(64 * 1024):
            yield chunk
    finally:
        if process is not None:
            await _release_stream(token, process)
        detail = ""
        if stderr_task is not None:
            try:
                detail = (await asyncio.wait_for(stderr_task, timeout=1)).decode("utf-8", errors="replace").strip()[:240]
            except (asyncio.TimeoutError, asyncio.CancelledError):
                stderr_task.cancel()
        append_audit(
            "camera.stream.closed",
            camera_id=resolved_id,
            result="ffmpeg_error" if detail else "closed",
            detail=detail,
        )


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
    append_audit("camera.stream.opened", camera_id=resolved_id)
    return StreamingResponse(
        _mjpeg_stream(resolved_id, device),
        media_type="multipart/x-mixed-replace; boundary=ffmpeg",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-GrowCentral-Camera": resolved_id},
    )


@router.post("/stream/stop", dependencies=[Depends(require_write_auth)])
async def camera_stream_stop():
    stopped = await _stop_active_stream("browser_request")
    return {"ok": True, "stopped": stopped}
