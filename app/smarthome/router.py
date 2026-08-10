"""Restricted smart-home API router."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.audit import append_audit
from app.security import require_write_auth

from .adapters.base import AdapterError
from .adapters.factory import build_switch_adapter
from .models import PublicDevice, SwitchCommand
from .policy import PolicyDenied, assert_switch_write_allowed, smart_home_enabled
from .registry import DeviceRegistry
from .onboarding import router as onboarding_router

router = APIRouter(prefix="/api/v1/smarthome", tags=["smart-home"])
router.include_router(onboarding_router)


def _registry() -> DeviceRegistry:
    try:
        return DeviceRegistry.from_env()
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "invalid smart-home device configuration") from exc


def _device(device_id: str):
    try:
        return _registry().get(device_id)
    except KeyError as exc:
        raise HTTPException(404, "unknown device") from exc


@router.get("/status")
async def integration_status():
    devices = _registry().list()
    return {
        "enabled": smart_home_enabled(),
        "configured_devices": len(devices),
        "approved_devices": sum(1 for item in devices if item.approved),
        "writable_devices": sum(1 for item in devices if item.approved and item.writable),
    }


@router.get("/devices", response_model=list[PublicDevice])
async def list_devices():
    return [
        PublicDevice(
            id=item.id,
            name=item.name,
            adapter=item.adapter,
            capability=item.capability,
            approved=item.approved,
            writable=item.writable,
            metadata=item.metadata,
        )
        for item in _registry().list()
    ]


async def _overview_row(device):
    base = {
        "id": device.id,
        "name": device.name,
        "adapter": device.adapter,
        "approved": device.approved,
        "writable": device.writable,
        "metadata": device.metadata,
    }
    if not device.approved:
        return {**base, "online": False, "error": "not approved", "state": None}
    try:
        state = await build_switch_adapter(device).read_state()
        return {**base, "online": bool(state.get("online", True)), "error": None, "state": state}
    except AdapterError as exc:
        return {**base, "online": False, "error": str(exc), "state": None}


@router.get("/overview")
async def device_overview():
    """Read all configured smart plugs without exposing credentials or control tokens."""
    devices = _registry().list()
    rows = await asyncio.gather(*(_overview_row(device) for device in devices))
    power_w = sum((row.get("state") or {}).get("power_w") or 0.0 for row in rows)
    energy_wh = sum((row.get("state") or {}).get("energy_wh") or 0.0 for row in rows)
    online = sum(1 for row in rows if row.get("online"))
    switched_on = sum(1 for row in rows if (row.get("state") or {}).get("on") is True)
    return {
        "enabled": smart_home_enabled(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "configured": len(rows),
            "online": online,
            "switched_on": switched_on,
            "power_w": round(power_w, 3),
            "energy_wh": round(energy_wh, 3),
        },
        "devices": rows,
    }


@router.get("/devices/{device_id}/state")
async def read_device_state(device_id: str):
    device = _device(device_id)
    if not device.approved:
        raise HTTPException(403, "device is not approved")
    try:
        state = await build_switch_adapter(device).read_state()
    except AdapterError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"id": device.id, "state": state}


@router.post("/devices/{device_id}/switch", dependencies=[Depends(require_write_auth)])
async def switch_device(device_id: str, command: SwitchCommand):
    device = _device(device_id)
    try:
        assert_switch_write_allowed(device)
    except PolicyDenied as exc:
        append_audit("smarthome.command.denied", device_id=device.id, action="switch", requested=command.on, reason=str(exc))
        raise HTTPException(403, str(exc)) from exc
    try:
        result = await build_switch_adapter(device).set_switch(command.on)
    except AdapterError as exc:
        append_audit("smarthome.command.failed", device_id=device.id, action="switch", requested=command.on, reason=str(exc))
        raise HTTPException(502, str(exc)) from exc
    append_audit("smarthome.command.success", device_id=device.id, action="switch", requested=command.on)
    return {"ok": True, "id": device.id, "state": result}
