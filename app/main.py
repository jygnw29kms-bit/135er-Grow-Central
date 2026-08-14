"""135er-Grow Central Local API alpha-0.7.5.

DE: Lokaler Raspberry-Pi-Dienst für Mars Hydro/iConnect, Smart Home,
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
from app.smarthome.router import router as smarthome_router
from app.network import router as network_router
from app.mars_hydro import is_mars_hydro_ble_candidate, public_hardware_profile
from app.system_info import router as system_router

NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "83677baa-3eb8-4866-b6b6-96e5ed5cc48d")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "false").lower() == "true"
ALLOW_RAW_WRITES = os.getenv("DF100M_ALLOW_RAW_WRITES", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="135er-Grow Central Local", version="0.7.5")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(network_router)
app.include_router(smarthome_router)
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
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "135er-Grow Central Local", "version": "0.7.5"}


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


@app.get("/api/status")
async def status():
    return _status_payload()


def _classify_ble_name(name: str) -> str:
    if is_mars_hydro_ble_candidate(name, NAME_HINT):
        return "df100m_candidate"
    return "generic_ble"


BLE_SERVICE_TYPES = {
    "1809": "Thermometer", "180d": "Pulssensor", "1810": "Blutdruckmessgerät",
    "1812": "Eingabegerät", "1816": "Fahrradsensor", "181a": "Umweltsensor",
}
BLE_MANUFACTURERS = {0x0006: "Microsoft", 0x004C: "Apple", 0x0075: "Samsung", 0x00E0: "Google"}


def _short_service_uuid(value: str) -> str:
    normalized = value.lower()
    if normalized.endswith("-0000-1000-8000-00805f9b34fb"):
        return normalized.split("-", 1)[0].lstrip("0") or "0"
    return normalized


def _ble_identity(name: str, service_uuids: list[str], manufacturer_ids: list[int]) -> tuple[str, str, str | None]:
    clean_name = name.strip()
    lowered = clean_name.lower()
    classification = _classify_ble_name(clean_name)
    device_type = "Bluetooth-Gerät"
    type_patterns = (
        (("headphone", "earbud", "buds", "airpods", "kopfhörer"), "Kopfhörer/Headset"),
        (("speaker", "sound", "lautsprecher"), "Lautsprecher"),
        (("watch", "band", "fitbit", "uhr"), "Smartwatch/Fitnessband"),
        (("sensor", "meter", "thermo", "hygro"), "Sensor"),
        (("keyboard", "mouse", "maus", "tastatur"), "Eingabegerät"),
    )
    if classification == "df100m_candidate":
        device_type = "Mars Hydro iFresh/DF100 BLE-Diagnosekandidat"
    else:
        for patterns, label in type_patterns:
            if any(pattern in lowered for pattern in patterns):
                device_type = label
                break
        else:
            for uuid in service_uuids:
                hint = BLE_SERVICE_TYPES.get(_short_service_uuid(uuid))
                if hint:
                    device_type = hint
                    break
    manufacturer = next((BLE_MANUFACTURERS[value] for value in manufacturer_ids if value in BLE_MANUFACTURERS), None)
    if clean_name:
        display_name = clean_name
    elif manufacturer:
        display_name = f"{manufacturer} {device_type}"
    else:
        display_name = f"Unbekanntes Gerät ({device_type})"
    return display_name, device_type, manufacturer


@app.get("/api/discover", dependencies=[Depends(require_write_auth)])
async def discover(timeout: float = 7.0):
    timeout = min(max(timeout, 1.0), 15.0)
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    rows = []
    for address, pair in found.items():
        dev, adv = pair
        name = adv.local_name or dev.name or ""
        classification = _classify_ble_name(name)
        service_uuids = list(adv.service_uuids or [])
        manufacturer_ids = sorted((adv.manufacturer_data or {}).keys())
        display_name, device_type, manufacturer = _ble_identity(name, service_uuids, manufacturer_ids)
        rows.append({
            "name": name, "display_name": display_name, "device_type": device_type,
            "manufacturer": manufacturer, "address": address, "rssi": adv.rssi,
            "service_uuids": service_uuids, "classification": classification,
            "preferred": classification == "df100m_candidate",
            "vendor_family": "mars_hydro_iconnect" if classification == "df100m_candidate" else None,
            "integration_role": "experimental_ble_diagnostics_fallback" if classification == "df100m_candidate" else "generic_ble",
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
        raise HTTPException(502, f"BLE-Verbindung fehlgeschlagen ({type(exc).__name__}). Gerät einschalten, näher heranbringen und eine bestehende App-Verbindung trennen.") from exc


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
    return {"services": [{"uuid": service.uuid, "characteristics": [{"uuid": c.uuid, "properties": list(c.properties), "handle": c.handle} for c in service.characteristics]} for service in client.services]}


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
        raise HTTPException(403, "DF100M BLE diagnostic writes are disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = speed_payload(body.percent)
        await client.write_gatt_char(WRITE_UUID, payload, response=True)
        return {"ok": True, "percent": body.percent, "uuid": WRITE_UUID, "hex": payload.hex(" "), "mode": SPEED_MODE}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(409, "DF100M BLE diagnostic write failed") from exc


@app.post("/api/raw", dependencies=[Depends(require_write_auth)])
async def raw(body: RawBody):
    if not ALLOW_WRITES:
        raise HTTPException(403, "DF100M BLE diagnostic writes are disabled")
    if not ALLOW_RAW_WRITES:
        raise HTTPException(403, "raw DF100M BLE diagnostic writes are disabled")
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
