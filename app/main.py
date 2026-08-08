from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bleak import BleakScanner, BleakClient

NAME_HINT = os.getenv("DF100M_NAME_HINT", "MZ_MZF002")
WRITE_UUID = os.getenv("DF100M_WRITE_UUID", "f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d")
NOTIFY_UUID = os.getenv("DF100M_NOTIFY_UUID", "83677baa-3eb8-4866-b6b6-96e5ed5cc48d")
SPEED_MODE = os.getenv("DF100M_SPEED_MODE", "byte")
ALLOW_WRITES = os.getenv("DF100M_ALLOW_WRITES", "true").lower() == "true"

app = FastAPI(title="135er GrowControl Test", version="0.1.0")
client: BleakClient | None = None
current_address: str | None = None
notifications: list[dict[str, Any]] = []

class ConnectBody(BaseModel):
    address: str

class SpeedBody(BaseModel):
    percent: int

class RawBody(BaseModel):
    uuid: str
    hex: str
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

@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent.parent / "web" / "index.html")

@app.get("/api/config")
async def config():
    return {
        "name_hint": NAME_HINT,
        "write_uuid": WRITE_UUID,
        "notify_uuid": NOTIFY_UUID,
        "speed_mode": SPEED_MODE,
        "allow_writes": ALLOW_WRITES,
    }

@app.get("/api/status")
async def status():
    return {
        "connected": bool(client and client.is_connected),
        "address": current_address,
        "notifications": notifications[-20:],
    }

@app.get("/api/discover")
async def discover(timeout: float = 7.0):
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
    rows.sort(key=lambda x: (not x["preferred"], -(x["rssi"] or -999)))
    return {"devices": rows}

@app.post("/api/connect")
async def connect(body: ConnectBody):
    global client, current_address
    try:
        if client and client.is_connected:
            await client.disconnect()
        client = BleakClient(body.address)
        await client.connect()
        current_address = body.address
        return {"ok": True, "connected": client.is_connected, "address": current_address}
    except Exception as e:
        raise HTTPException(502, str(e))

@app.post("/api/disconnect")
async def disconnect():
    global client, current_address
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
    client = None
    current_address = None
    return {"ok": True}

@app.get("/api/services")
async def services():
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    result = []
    for s in client.services:
        chars = []
        for c in s.characteristics:
            chars.append({"uuid": c.uuid, "properties": list(c.properties), "handle": c.handle})
        result.append({"uuid": s.uuid, "characteristics": chars})
    return {"services": result}

@app.post("/api/notify/start")
async def notify_start(uuid: str = NOTIFY_UUID):
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    def cb(sender, data: bytearray):
        notifications.append({"uuid": str(sender.uuid), "hex": bytes(data).hex(" "), "bytes": list(data)})
        if len(notifications) > 200:
            del notifications[:-200]
    try:
        await client.start_notify(uuid, cb)
        return {"ok": True, "uuid": uuid}
    except Exception as e:
        raise HTTPException(409, str(e))

@app.post("/api/notify/stop")
async def notify_stop(uuid: str = NOTIFY_UUID):
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        await client.stop_notify(uuid)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(409, str(e))

@app.post("/api/speed")
async def speed(body: SpeedBody):
    if not ALLOW_WRITES:
        raise HTTPException(403, "writes disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = speed_payload(body.percent)
        await client.write_gatt_char(WRITE_UUID, payload, response=True)
        return {"ok": True, "percent": body.percent, "uuid": WRITE_UUID, "hex": payload.hex(" "), "mode": SPEED_MODE}
    except Exception as e:
        raise HTTPException(409, str(e))

@app.post("/api/raw")
async def raw(body: RawBody):
    if not ALLOW_WRITES:
        raise HTTPException(403, "writes disabled")
    if not client or not client.is_connected:
        raise HTTPException(409, "not connected")
    try:
        payload = bytes.fromhex(body.hex)
        await client.write_gatt_char(body.uuid, payload, response=body.response)
        return {"ok": True, "uuid": body.uuid, "hex": payload.hex(" ")}
    except Exception as e:
        raise HTTPException(409, str(e))
