"""Restricted smart-home API router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.audit import append_audit
from app.security import require_write_auth

from .adapters.base import AdapterError
from .adapters.factory import build_switch_adapter
from .models import PublicDevice, SwitchCommand
from .policy import PolicyDenied, assert_switch_write_allowed, smart_home_enabled
from .registry import DeviceRegistry

router = APIRouter(prefix="/api/v1/smarthome", tags=["smart-home"])


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
