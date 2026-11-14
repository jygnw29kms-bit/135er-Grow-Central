"""135er-Grow Central Local API alpha-0.7.5.

DE: Lokaler Raspberry-Pi-Dienst für Grow Central, Smart Home,
Netzwerkverwaltung, BLE-Diagnose und die lokale Weboberfläche.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

from bleak import BleakClient, BleakScanner
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app.diagnostics import router as diagnostics_router
from app.devices.router import router as devices_router
from app.devices.gc_pairing import router as pairing_router
from app.smarthome.router import router as smarthome_router
from app.smarthome.ha_bridge import router as ha_bridge_router
from app.homekit_bridge import router as homekit_router
from app.provisioning.usb import router as usb_router
from app.provisioning.ble import router as ble_provisioning_router
from app.network import router as network_router
from app.mars_hydro import is_mars_hydro_ble_candidate, public_hardware_profile
from app.mars_hydro_ble import router as mars_hydro_ble_router, adapter_diagnostics
from app.mars_hydro_cloud_fan import router as mars_hydro_cloud_fan_router
from app.system_info import router as system_router

NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "6f588463-f8f1-44f8-bdae-a1272a1b0f6e")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "false").lower() == "true"
ALLOW_RAW_WRITES = os.getenv("DF100M_ALLOW_RAW_WRITES", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="135er-Grow Central Local", version="0.7.5")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(network_router)
app.include_router(devices_router)
app.include_router(pairing_router)
app.include_router(smarthome_router)
app.include_router(ha_bridge_router)
app.include_router(homekit_router)
app.include_router(usb_router)
app.include_router(ble_provisioning_router)
app.include_router(mars_hydro_ble_router)
app.include_router(mars_hydro_cloud_fan_router)
app.include_router(diagnostics_router)
app.include_router(system_router)

client: BleakClient | None = None
current_address: str | None = None
notifications: list[dict[str, Any]] = []
logger = logging.getLogger(__name__)


class ConnectBody(BaseModel):
    address: str = Field(min_length=2, max_length=128)


class SpeedBody(BaseModel):
    percent: int = Field(ge=0, le=100)
class RawBody(BaseModel):
    uuid: str = Field(min_length=4, max_length=64, pattern=r"^[0-9a-fA-F-]+$")
    hex: str = Field(min_length=2, max_length=383, pattern=r"^[0-9a-fA-F\s]+$")
    response: bool = True


def speed_payload(percent: int) -> bytes:
    if not 0 <= percent <= 100:
        raise ValueError("percent must be 0..100")
    if SPEED_MODE == "byte":
        return bytes([percent])
    if SPEED_MODE == "ascii":
        return str(percent).encode("ascii")
    if SPEED_MODE == "hexprefix":
        return bytes([0x01, percent])
    raise ValueError(f"unknown speed mode: {SPEED_MODE}")


def _status_payload() -> dict[str, Any]:
    online = bool(client and client.is_connected)
    return {
        "connected": online,
        "online": online,
        "address": current_address,
        "notifications": notifications[-20:],
        "protocol_validated": False,
        "write_enabled": ALLOW_WRITES,
        "integration_role": "experimental_ble_diagnostics_fallback",
        "vendor_family": "mars_hydro_iconnect",
    }


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "gc-final.html", headers={"Cache-Control":"no-store"})


@app.get("/legacy")
async def legacy_index():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/ui",status_code=308)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(WEB_DIR / "brand-mark.png", media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "135er-Grow Central Local", "version": "0.7.5", "device_api": "gc-device-v1"}


@app.get("/api/config")
async def config():
    return {
        "name_hint": NAME_HINT,
        "write_uuid": WRITE_UUID,
        "notify_uuid": NOTIFY_UUID,
        "speed_mode": SPEED_MODE,
        "allow_writes": ALLOW_WRITES,
        "allow_raw_writes": ALLOW_RAW_WRITES,
        "smarthome_enabled": os.getenv("GC_SMARTHOME_ENABLED", "true").lower() == "true",
        "cloud_enabled": os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true",
        "mars_hydro": public_hardware_profile(),
    }
