from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .catalog import provider_by_id, provider_catalog
from .models import Capability, DeviceClass, SupportLevel, Transport

router = APIRouter(prefix="/api/devices", tags=["devices"])


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
    }


@router.get("/providers")
async def providers():
    return {"providers": provider_catalog()}


@router.get("/providers/{provider_id}")
async def provider(provider_id: str):
    item = provider_by_id(provider_id)
    if not item:
        raise HTTPException(404, "unknown provider")
    return item.public()
