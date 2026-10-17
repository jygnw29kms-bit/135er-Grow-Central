"""Raspberry Pi power-health event monitor.

Records only transitions observed while Grow-Central is running. Historical
firmware bits remain visible through system_info but are not treated as fresh events.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/system/power", tags=["system"])
STATE_FILE = Path(os.getenv("GC_POWER_HEALTH_FILE", "/var/lib/135er-grow-central/power-health.json"))
_task: asyncio.Task | None = None
_last_current: dict[str, bool] | None = None


def _run(args: list[str], timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def _flags() -> dict[str, bool] | None:
    raw = _run(["vcgencmd", "get_throttled"])
    if "=" not in raw:
        return None
    try:
        value = int(raw.split("=", 1)[1], 16)
    except ValueError:
        return None
    return {
        "under_voltage_now": bool(value & 0x1),
        "frequency_capped_now": bool(value & 0x2),
        "throttled_now": bool(value & 0x4),
        "under_voltage_occurred": bool(value & 0x10000),
        "frequency_capped_occurred": bool(value & 0x20000),
        "throttled_occurred": bool(value & 0x40000),
    }


def _load() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"events": []}
    except (OSError, json.JSONDecodeError):
        return {"events": []}


def _save(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o640)
    os.replace(temp, STATE_FILE)


def _snapshot(event_type: str, flags: dict[str, bool]) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "flags": flags,
        "temperature": _run(["vcgencmd", "measure_temp"]),
        "usb_tree": _run(["lsusb", "-t"], timeout=3.0),
        "loadavg": Path("/proc/loadavg").read_text(encoding="utf-8", errors="replace").strip() if Path("/proc/loadavg").exists() else "",
    }


def sample() -> list[dict]:
    global _last_current
    flags = _flags()
    if flags is None:
        return []
    current = {key: value for key, value in flags.items() if key.endswith("_now")}
    if _last_current is None:
        _last_current = current
        return []
    events = []
    for key in ("under_voltage_now", "throttled_now", "frequency_capped_now"):
        if current.get(key) and not _last_current.get(key):
            events.append(_snapshot(key, flags))
    _last_current = current
    if events:
        state = _load()
        history = list(state.get("events") or [])
        history.extend(events)
        state["events"] = history[-50:]
        state["last_sample"] = datetime.now(timezone.utc).isoformat()
        _save(state)
    return events


async def _loop() -> None:
    while True:
        try:
            sample()
        except Exception:
            pass
        await asyncio.sleep(10)


def install(app) -> None:
    async def startup() -> None:
        global _task
        sample()  # baseline: historical bits are not fresh events
        if _task is None or _task.done():
            _task = asyncio.create_task(_loop(), name="growcentral-power-monitor")

    async def shutdown() -> None:
        global _task
        task, _task = _task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app.router.add_event_handler("startup", startup)
    app.router.add_event_handler("shutdown", shutdown)


@router.get("")
async def power_history():
    state = _load()
    return {"current": _flags(), "events": list(state.get("events") or [])[-50:]}
