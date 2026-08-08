"""135er GrowControl Local API.

DE:
    Lokaler Raspberry-Pi-Dienst für BLE-Discovery, GATT-Analyse und
    experimentelle DF100M-Kommunikation.

EN:
    Local Raspberry Pi service for BLE discovery, GATT inspection and
    experimental DF100M communication.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from bleak import BleakClient, BleakScanner
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# DE: Gerätekonfiguration aus Umgebungsvariablen laden.
# EN: Load device configuration from environment variables.
NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "83677baa-3eb8-4866-b6b6-96e5ed5cc48d")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="135er GrowControl Local", version="0.4.1")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# DE: Für die frühe Testversion wird genau eine aktive BLE-Verbindung verwaltet.
# EN: The early test build manages exactly one active BLE connection.
client: BleakClient | None = None
current_address: str | None = None
notifications: list[dict[str, Any]] = []


class ConnectBody(BaseModel):
    """DE: BLE-Adresse. EN: BLE address."""
    address: str


class SpeedBody(BaseModel):
    """DE: Experimenteller Prozentwert. EN: Experimental percentage."""
    percent: int


class RawBody(BaseModel):
    """DE: Rohes GATT-Testpaket. EN: Raw GATT test packet."""
    uuid: str
    hex: str
    response: bool = True


def speed_payload(percent: int) -> bytes:
    """Experimentelles Speed-Payload / Experimental speed payload.

    DE: Das echte DF100M-Frameformat ist noch nicht validiert.
    EN: The actual DF100M frame format has not yet been validated.
    """
    if not 0 <= percent <= 100:
        raise ValueError("percent must be 0..100")
    if SPEED_MODE == "byte":
        return bytes([percent])
    if SPEED_MODE == "ascii":
        return str(percent).encode("ascii")
    if SPEED_MODE == "hexprefix":
        return bytes([0x01, percent])
    raise ValueError(f"unknown speed mode: {SPEED_MODE}")


@app.get("/")
async def index():
    """DE: Lokales HUD ausliefern. EN: Serve the local HUD."""
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health():
    """DE: Service-Healthcheck. EN: Service health check."""
    return {"ok": True, "service": "135er GrowControl Local", "version": "0.4.1"}


@app.get("/api/config")
async def config():
    """DE: Aktuelle Testkonfiguration. EN: Current test configuration."""
    return {
        "name_hint": NAME_HINT,
        "write_uuid": WRITE_UUID,
        "notify_uuid": NOTIFY_UUID,
        "speed_mode": SPEED_MODE,
        "allow_writes": ALLOW_WRITES,
    }


@app.get("/api/status")
async def status():
    """DE: BLE-Status und letzte Notifications. EN: BLE state and recent notifications."""
    return {
        "connected": bool(client and client.is_connected),
        "address": current_address,
        "notifications": notifications[-20:],
    }


@app.get("/api/discover")
async def discover(timeout: float = 7.0):
    """DE: BLE-Geräte suchen. EN: Discover BLE devices."""
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
    # DE: Relevante Geräte zuerst, danach stärkstes Signal.
    # EN: Relevant devices first, then strongest signal.
    rows.sort(key=lambda item: (not item["preferred"], -(item["rssi"] or -999)))
    return {"devices": rows}


@app.post("/api/connect")
async def connect(body: ConnectBody):
    """DE: BLE verbinden. EN: Connect over BLE."""
    global client, current_address
    try:
        if client and client.is_connected:
            await client.disconnect()
        client = BleakClient(body.address)
        await client.connect()
        current_address = body.address
        return {"ok": True, "connected": client.is_connected, "address": current_address}
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/disconnect")
async def disconnect():
    """DE: BLE trennen. EN: Disconnect BLE."""
    global client, current_address
    if client:
        try:
            await client.disconnect()
        except Exception:
            # DE: Ein Disconnect-Fehler darf den Dienst nicht blockieren.
            # EN: A disconnect error must not block the service.
            pass
    client = None
    current_address = None
    return {"ok": True}


@app.get("/api/services")
async def services():
    """DE: GATT-Struktur lesen. EN: Read the GATT structure."""
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    result = []
    for service in client.services:
        chars = []
        for characteristic in service.characteristics:
            chars.append({
                "uuid": characteristic.uuid,
                "properties": list(characteristic.properties),
                "handle": characteristic.handle,
            })
        result.append({"uuid": service.uuid, "characteristics": chars})
    return {"services": result}


@app.post("/api/notify/start")
async def notify_start(uuid: str = NOTIFY_UUID):
    """DE: Notifications abonnieren. EN: Subscribe to notifications."""
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")

    def callback(sender, data: bytearray):
        # DE: HEX und Bytes parallel speichern, um Protokollanalyse zu erleichtern.
        # EN: Store both HEX and bytes to simplify protocol analysis.
        notifications.append({
            "uuid": str(sender.uuid),
            "hex": bytes(data).hex(" "),
            "bytes": list(data),
        })
        if len(notifications) > 200:
            del notifications[:-200]

    try:
        await client.start_notify(uuid, callback)
        return {"ok": True, "uuid": uuid}
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/notify/stop")
async def notify_stop(uuid: str = NOTIFY_UUID):
    """DE: Notifications stoppen. EN: Stop notifications."""
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        await client.stop_notify(uuid)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/speed")
async def speed(body: SpeedBody):
    """DE: Experimentellen Speed-Befehl senden. EN: Send an experimental speed command."""
    if not ALLOW_WRITES:
        raise HTTPException(403, "writes disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = speed_payload(body.percent)
        await client.write_gatt_char(WRITE_UUID, payload, response=True)
        return {
            "ok": True,
            "percent": body.percent,
            "uuid": WRITE_UUID,
            "hex": payload.hex(" "),
            "mode": SPEED_MODE,
        }
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/raw")
async def raw(body: RawBody):
    """DE: Rohes HEX-Testpaket schreiben. EN: Write a raw HEX test packet."""
    if not ALLOW_WRITES:
        raise HTTPException(403, "writes disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = bytes.fromhex(body.hex)
        await client.write_gatt_char(body.uuid, payload, response=body.response)
        return {"ok": True, "uuid": body.uuid, "hex": payload.hex(" ")}
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
