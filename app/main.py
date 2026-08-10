"""135er-Grow Central Local API alpha-0.7.1.

DE: Lokaler Raspberry-Pi-Dienst für DF100M BLE-Forschung, sichere
Smart-Home-Adapter und die lokale Weboberfläche.

EN: Local Raspberry Pi service for DF100M BLE research, secured smart-home
adapters and the local web UI.
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
from app.smarthome.router import router as smarthome_router

NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "83677baa-3eb8-4866-b6b6-96e5ed5cc48d")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "false").lower() == "true"
ALLOW_RAW_WRITES = os.getenv("DF100M_ALLOW_RAW_WRITES", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="135er-Grow Central Local", version="0.7.1")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(smarthome_router)
app.include_router(diagnostics_router)

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
    """Build an experimental payload; protocol is not validated yet."""
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
    }


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "135er-Grow Central Local", "version": "0.7.1"}


@app.get("/api/config")
async def config():
    """Return non-secret runtime configuration only."""
    return {
        "name_hint": NAME_HINT,
        "write_uuid": WRITE_UUID,
        "notify_uuid": NOTIFY_UUID,
        "speed_mode": SPEED_MODE,
        "allow_writes": ALLOW_WRITES,
        "allow_raw_writes": ALLOW_RAW_WRITES,
        "smarthome_enabled": os.getenv("GC_SMARTHOME_ENABLED", "false").lower() == "true",
        "cloud_enabled": os.getenv("GC_CLOUD_ENABLED", "false").lower() == "true",
    }


@app.get("/api/status")
async def status():
    return _status_payload()


@app.get("/api/discover", dependencies=[Depends(require_write_auth)])
async def discover(timeout: float = 7.0):
    timeout = min(max(timeout, 1.0), 15.0)
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    rows = []
    for address, pair in found.items():
        dev, adv = pair
        name = dev.name or adv.local_name or ""
        rows.append({
            "name": name,
            "address": address,
            "rssi": adv.rssi,
            "preferred": NAME_HINT.lower() in name.lower() or "mzf" in name.lower() or "mars" in name.lower(),
        })
    rows.sort(key=lambda item: (not item["preferred"], -(item["rssi"] or -999)))
    return {"devices": rows}


async def _connect(address: str):
    global client, current_address
    try:
        if client and client.is_connected:
            await client.disconnect()
        client = BleakClient(address)
        await client.connect()
        current_address = address
        return {"ok": True, "connected": client.is_connected, "address": current_address}
    except Exception as exc:
        raise HTTPException(502, "BLE connection failed") from exc


@app.post("/api/connect", dependencies=[Depends(require_write_auth)])
async def connect(body: ConnectBody):
    return await _connect(body.address)


@app.post("/api/disconnect", dependencies=[Depends(require_write_auth)])
async def disconnect():
    global client, current_address
    if client:
        try:
            await client.disconnect()
        except Exception as exc:
            logger.warning("BLE disconnect failed: %s", type(exc).__name__)
    client = None
    current_address = None
    return {"ok": True}


@app.get("/api/services", dependencies=[Depends(require_write_auth)])
async def services():
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    result = []
    for service in client.services:
        chars = [{"uuid": c.uuid, "properties": list(c.properties), "handle": c.handle} for c in service.characteristics]
        result.append({"uuid": service.uuid, "characteristics": chars})
    return {"services": result}


@app.post("/api/notify/start", dependencies=[Depends(require_write_auth)])
async def notify_start(uuid: str = NOTIFY_UUID):
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")

    def callback(sender, data: bytearray):
        notifications.append({"uuid": str(sender.uuid), "hex": bytes(data).hex(" "), "bytes": list(data)})
        if len(notifications) > 200:
            del notifications[:-200]

    try:
        await client.start_notify(uuid, callback)
        return {"ok": True, "uuid": uuid}
    except Exception as exc:
        raise HTTPException(409, "notification subscription failed") from exc


@app.post("/api/notify/stop", dependencies=[Depends(require_write_auth)])
async def notify_stop(uuid: str = NOTIFY_UUID):
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        await client.stop_notify(uuid)
        return {"ok": True, "uuid": uuid}
    except Exception as exc:
        raise HTTPException(409, "notification unsubscribe failed") from exc


@app.post("/api/speed", dependencies=[Depends(require_write_auth)])
async def speed(body: SpeedBody):
    if not ALLOW_WRITES:
        raise HTTPException(403, "DF100M writes are disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = speed_payload(body.percent)
        await client.write_gatt_char(WRITE_UUID, payload, response=True)
        return {"ok": True, "percent": body.percent, "uuid": WRITE_UUID, "hex": payload.hex(" "), "mode": SPEED_MODE}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(409, "DF100M write failed") from exc


@app.post("/api/raw", dependencies=[Depends(require_write_auth)])
async def raw(body: RawBody):
    if not ALLOW_WRITES:
        raise HTTPException(403, "DF100M writes are disabled")
    if not ALLOW_RAW_WRITES:
        raise HTTPException(403, "raw DF100M writes are disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = bytes.fromhex(body.hex)
        if len(payload) > 128:
            raise HTTPException(413, "raw payload too large")
        await client.write_gatt_char(body.uuid, payload, response=body.response)
        return {"ok": True, "uuid": body.uuid, "hex": payload.hex(" ")}
    except ValueError as exc:
        raise HTTPException(422, "invalid hex payload") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(409, "raw BLE write failed") from exc


# Compatibility API for the current local HUD. New integrations should prefer
# the stable /api/v1/* namespaces where available.
@app.get("/api/df100m/status")
async def df100m_status_alias():
    return _status_payload()


@app.get("/api/df100m/discover", dependencies=[Depends(require_write_auth)])
async def df100m_discover_alias(timeout: float = 7.0):
    return await discover(timeout)


@app.post("/api/df100m/connect", dependencies=[Depends(require_write_auth)])
async def df100m_connect_alias(address: str):
    return await _connect(address)


@app.get("/api/df100m/services", dependencies=[Depends(require_write_auth)])
async def df100m_services_alias():
    return await services()


@app.post("/api/df100m/speed", dependencies=[Depends(require_write_auth)])
async def df100m_speed_alias(percent: int):
    return await speed(SpeedBody(percent=percent))
