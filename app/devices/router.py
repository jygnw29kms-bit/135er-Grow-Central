from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.security import require_write_auth

from .catalog import provider_by_id, provider_catalog
from .models import Capability, DeviceClass, SupportLevel, Transport
from .runtime import runtime

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceCommand(BaseModel):
    capability: Capability
    value: Any


@router.get("/platform")
async def platform_manifest():
    return {
        "api": "gc-device-v1",
        "principle": "local-first",
        "vendor_neutral": True,
        "support_levels": [item.value for item in SupportLevel],
        "device_classes": [item.value for item in DeviceClass],
        "capabilities": [item.value for item in Capability],
        "transports": [item.value for item in Transport],
        "providers": provider_catalog(),
        "runtime_providers": list(runtime.ids()),
    }


@router.get("/providers")
async def providers():
    executable = set(runtime.ids())
    return {
        "providers": [
            {**row, "runtime_available": row["id"] in executable}
            for row in provider_catalog()
        ]
    }


@router.get("/providers/{provider_id}")
async def provider(provider_id: str):
    item = provider_by_id(provider_id)
    if not item:
        raise HTTPException(404, "unknown provider")
    return {**item.public(), "runtime_available": provider_id in runtime.ids()}


@router.get("/runtime")
async def runtime_status():
    rows = []
    for item in runtime.providers():
        try:
            devices = await item.discover(timeout=0)
            error = None
        except Exception as exc:  # Runtime overview must not fail because one provider is unhealthy.
            devices = []
            error = f"{type(exc).__name__}: {exc}"
        rows.append({
            "id": item.descriptor.id,
            "name": item.descriptor.name,
            "support": item.descriptor.support.value,
            "device_count": len(devices),
            "error": error,
        })
    return {"api": "gc-device-v1", "providers": rows}


@router.get("/discover")
async def discover(timeout: float = Query(default=5.0, ge=0.0, le=15.0)):
    providers = runtime.providers()
    results = await asyncio.gather(
        *(item.discover(timeout=timeout) for item in providers),
        return_exceptions=True,
    )
    devices: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item, result in zip(providers, results, strict=True):
        if isinstance(result, Exception):
            errors.append({"provider_id": item.descriptor.id, "error": str(result)})
            continue
        for device in result:
            row = asdict(device)
            row["device_class"] = device.device_class.value
            row["capabilities"] = [cap.value for cap in device.capabilities]
            row["global_id"] = device.global_id
            devices.append(row)
    devices.sort(key=lambda row: (row["provider_id"], row["name"].lower(), row["native_id"]))
    return {"devices": devices, "errors": errors}


def _provider_or_404(provider_id: str):
    try:
        return runtime.get(provider_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{provider_id}/{native_id}/state")
async def device_state(provider_id: str, native_id: str):
    provider_impl = _provider_or_404(provider_id)
    try:
        state = await provider_impl.state(native_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"device state failed: {type(exc).__name__}") from exc
    return {"provider_id": provider_id, "native_id": native_id, "state": dict(state)}


@router.get("/{provider_id}/{native_id}/health")
async def device_health(provider_id: str, native_id: str):
    provider_impl = _provider_or_404(provider_id)
    try:
        health = await provider_impl.health(native_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"provider_id": provider_id, "native_id": native_id, "health": asdict(health)}


@router.post("/{provider_id}/{native_id}/command", dependencies=[Depends(require_write_auth)])
async def device_command(provider_id: str, native_id: str, body: DeviceCommand):
    provider_impl = _provider_or_404(provider_id)
    try:
        state = await provider_impl.command(native_id, body.capability, body.value)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"device command failed: {type(exc).__name__}") from exc
    return {
        "ok": True,
        "provider_id": provider_id,
        "native_id": native_id,
        "capability": body.capability.value,
        "state": dict(state),
    }
