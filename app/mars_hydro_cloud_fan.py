"""Optional Mars Hydro *legacy* cloud fan adapter.

Separate from local MZF002 BLE telemetry and from MarsPro/MH-CB43 MQTT.
Tested upstream shape: Mars Hydro (not MarsPro) Android REST legacy API.
Default disabled. Never starts login without an explicit authenticated action.
An upstream login may log out the official phone app.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Literal

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_write_auth

BASE = "https://api.lgledsolutions.com/api/android"
router = APIRouter(prefix="/api/mars-hydro/cloud-fan",
                   tags=["Mars Hydro legacy fan cloud"],
                   dependencies=[Depends(require_write_auth)])
_lock = asyncio.Lock()
_token: str | None = None
_login_at = 0.0


class FanControl(BaseModel):
    action: Literal["power", "speed"]
    value: int = Field(ge=0, le=100)
    confirm: bool = False


def configured() -> bool:
    return (
        os.getenv("GC_MARS_CLOUD_ENABLE") == "1"
        and bool(os.getenv("GC_MARS_CLOUD_EMAIL", "").strip())
        and bool(os.getenv("GC_MARS_CLOUD_PASSWORD", "").strip())

    )


def _headers(token: str | None, *, device_id: str | None = None) -> dict[str, str]:
    header = {
        "reqId": int(time.time() * 1000),
        "appVersion": "1.2.0",
        "osType": "android",
        "osVersion": "14",
        "deviceType": "SM-S928C",
        "deviceId": device_id,
        "netType": "wifi",
        "wifiName": "",
        "timestamp": int(time.time()),
        "token": token,
        "timezone": "Europe/Berlin",
        "language": "German",
    }
    return {"Content-Type": "application/json",
            "Accept": "application/json",
            "systemData": json.dumps(header, separators=(",", ":"))}


async def _post(path: str, payload: dict, token: str | None = None,
                device_id: str | None = None) -> dict:
    if not path.startswith("/") or ".." in path:
        raise ValueError("Invalid API route")
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(BASE + path, json=payload,
                                headers=_headers(token, device_id=device_id),
                                ssl=True) as response:
            response.raise_for_status()
            result = await response.json(content_type=None)
    if not isinstance(result, dict):
        raise ValueError("Invalid vendor API response")
    return result


async def _login() -> str:
    global _token, _login_at
    if _token and time.monotonic() - _login_at < 240:
        return _token
    result = await _post("/ulogin/mailLogin/v1", {
        "email": os.environ["GC_MARS_CLOUD_EMAIL"].strip(),
        "password": os.environ["GC_MARS_CLOUD_PASSWORD"],
        "loginMethod": "1",
    })
    token = result.get("data", {}).get("token") if isinstance(result.get("data"), dict) else None
    if not isinstance(token, str) or len(token) < 12:
        raise ValueError("Vendor login refused")
    _token, _login_at = token, time.monotonic()
    return token


async def _fan_details(token: str) -> dict[str, Any]:
    result = await _post("/udm/getDeviceList/v1", {
        "currentPage": 0, "type": None, "productType": "WIND",
    }, token)
    if str(result.get("code")) != "000":
        raise ValueError("Fan device list unavailable")
    data = result.get("data") or {}
    rows = data.get("list", []) if isinstance(data, dict) else []
    expected = os.getenv("GC_MARS_CLOUD_FAN_ID", "").strip()
    matches = [row for row in rows if isinstance(row, dict)
               and (str(row.get("id")) == expected if expected else True)]
    if len(matches) != 1:
        raise ValueError("Configured fan not found in authenticated account")
    return matches[0]


def normalized_fan(row: dict) -> dict:
    """Expose selected safe fields only; never leak cloud IDs or tokens."""
    level = row.get("deviceLightRate")
    try:
        percent = int(level)
    except (ValueError, TypeError):
        percent = None
    if percent is not None and not 0 <= percent <= 100:
        percent = None
    return {
        "name": str(row.get("deviceName") or "Mars Hydro Fan")[:80],
        "speed_percent": percent,
        "is_close_vendor": row.get("isClose") if isinstance(row.get("isClose"), bool) else None,
        "source": "mars_hydro_legacy_cloud",
        "bluetooth_fan_state_is_independent": True,
    }


@router.get("/status")
async def status():
    return {"configured": configured(), "control_available": configured(),
            "session_active": bool(_token),
            "vendor_app_may_be_logged_out": True,
            "status": "optional_cloud_control",
            "note": "No vendor authentication occurs on this status request."}


@router.post("/fan/read")
async def fan_read():
    if not configured():
        raise HTTPException(503, "Mars Hydro Cloud-Fan-Zugang noch nicht eingerichtet.")
    async with _lock:
        try:
            token = await _login()
            fan = await _fan_details(token)
            return {"ok": True, "fan": normalized_fan(fan)}
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
            raise HTTPException(502, "Mars Hydro Cloud-Anmeldung/Abfrage fehlgeschlagen.") from None


@router.post("/fan/control")
async def fan_control(body: FanControl):
    if not configured():
        raise HTTPException(503, "Mars Hydro Cloud-Fan-Zugang noch nicht eingerichtet.")
    if not body.confirm:
        raise HTTPException(428, "Manuelle Bestätigung des Lüfterbefehls erforderlich.")
    if body.action == "speed" and not 25 <= body.value <= 100:
        raise HTTPException(422, "Drehzahl nur 25 bis 100 Prozent.")
    if body.action == "power" and body.value not in (0, 1):
        raise HTTPException(422, "Ein/Aus nur 0 oder 1.")
    async with _lock:
        try:
            token = await _login()
            before = await _fan_details(token)
            device_id = str(before["id"])
            if body.action == "speed":
                route, data = "/udm/adjustLight/v1", {
                    "light": body.value, "deviceId": device_id, "groupId": None}
            else:
                route, data = "/udm/lampSwitch/v1", {
                    "isClose": body.value == 0, "deviceId": device_id, "groupId": None}
            result = await _post(route, data, token, device_id)
            accepted = str(result.get("code")) == "000"
            if not accepted:
                raise ValueError("Vendor rejected fan command")
            after = await _fan_details(token)
            state = normalized_fan(after)
            if body.action == "speed":
                confirmed = state["speed_percent"] == body.value
            else:
                closed = state.get("is_close_vendor")
                confirmed = closed is not None and closed == (body.value == 0)
            return {
                "command_accepted": True, "readback_matches": confirmed,
                "action": body.action, "requested_value": body.value,
                "current": state, "retry_attempted": False,
                "physical_effect_verified": False,
            }
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
            raise HTTPException(502, "Lüftersteuerung nicht bestätigt; nicht erneut automatisch gesendet.") from None
