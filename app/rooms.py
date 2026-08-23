"""Room organization, sensor history and grow journals for Grow Central."""
from __future__ import annotations

import asyncio
import fcntl
import json
import math
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app.smarthome.registry import DeviceRegistry
from app.smarthome.router import device_overview

DATA_FILE = Path(os.getenv("GC_ROOMS_FILE", "/var/lib/135er-grow-central/rooms.json"))
CAPTURE_INTERVAL_SECONDS = max(60, int(os.getenv("GC_ROOM_CAPTURE_INTERVAL", "300")))
router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])
_capture_task: asyncio.Task | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def empty_state() -> dict[str, Any]:
    return {"rooms": [], "assignments": {}, "room_journal": [], "plants": [], "plant_journal": [], "sensor_history": []}


def load_state() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return empty_state()
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid rooms database") from exc
    base = empty_state()
    if isinstance(raw, dict):
        for key in base:
            if key in raw:
                base[key] = raw[key]
    return base


def save_state(state: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = DATA_FILE.with_name(f".{DATA_FILE.name}.lock")
    fd_lock = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd_lock, 0o600)
        fcntl.flock(fd_lock, fcntl.LOCK_EX)
        fd, temp = tempfile.mkstemp(prefix=f".{DATA_FILE.name}-", dir=DATA_FILE.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, DATA_FILE)
            os.chmod(DATA_FILE, 0o600)
        finally:
            Path(temp).unlink(missing_ok=True)
    finally:
        fcntl.flock(fd_lock, fcntl.LOCK_UN)
        os.close(fd_lock)


def room_or_404(state: dict[str, Any], room_id: str) -> dict[str, Any]:
    row = next((r for r in state["rooms"] if r["id"] == room_id), None)
    if not row:
        raise HTTPException(404, "Raum nicht gefunden")
    return row


def plant_or_404(state: dict[str, Any], plant_id: str) -> dict[str, Any]:
    row = next((r for r in state["plants"] if r["id"] == plant_id), None)
    if not row:
        raise HTTPException(404, "Pflanze nicht gefunden")
    return row


def calc_vpd(temp_c: float | None, rh: float | None) -> float | None:
    if temp_c is None or rh is None or not (0 <= rh <= 100):
        return None
    saturation = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    return round(saturation * (1 - rh / 100), 3)


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["grow_tent", "grow_room", "drying", "storage", "other"] = "grow_tent"
    description: str = Field(default="", max_length=1000)
    target_temperature_c: float | None = Field(default=None, ge=0, le=60)
    target_humidity_percent: float | None = Field(default=None, ge=0, le=100)
    light_cycle: str = Field(default="", max_length=32)


class RoomUpdate(RoomCreate):
    pass


class DeviceAssignment(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)


class JournalEntry(BaseModel):
    category: Literal["note", "watering", "feeding", "training", "defoliation", "pest", "flowering", "harvest", "other"] = "note"
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(default="", max_length=5000)


class PlantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    strain: str = Field(default="", max_length=120)
    plant_type: Literal["automatic", "feminized", "mother", "clone", "other"] = "other"
    start_date: str = Field(default="", max_length=32)
    phase: Literal["germination", "vegetative", "flowering", "flush", "harvest", "other"] = "vegetative"
    notes: str = Field(default="", max_length=2000)


class SensorSample(BaseModel):
    temperature_c: float | None = Field(default=None, ge=-30, le=80)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    co2_ppm: float | None = Field(default=None, ge=0, le=100000)
    soil_moisture_percent: float | None = Field(default=None, ge=0, le=100)
    power_w: float | None = Field(default=None, ge=0)
    energy_wh: float | None = Field(default=None, ge=0)
    source: str = Field(default="manual", max_length=100)


@router.get("")
async def list_rooms():
    state = load_state()
    counts: dict[str, int] = {}
    for device_id, room_id in state["assignments"].items():
        counts[room_id] = counts.get(room_id, 0) + 1
    result = []
    for room in state["rooms"]:
        latest = next((x for x in reversed(state["sensor_history"]) if x["room_id"] == room["id"]), None)
        result.append({**room, "device_count": counts.get(room["id"], 0), "plant_count": sum(1 for p in state["plants"] if p["room_id"] == room["id"]), "latest_sensor": latest})
    return {"rooms": result}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_room(body: RoomCreate):
    state = load_state()
    row = {"id": new_id("room"), **body.model_dump(), "created_at": now_iso(), "updated_at": now_iso()}
    state["rooms"].append(row)
    save_state(state)
    return row


@router.put("/{room_id}", dependencies=[Depends(require_write_auth)])
async def update_room(room_id: str, body: RoomUpdate):
    state = load_state(); row = room_or_404(state, room_id)
    row.update(body.model_dump()); row["updated_at"] = now_iso(); save_state(state)
    return row


@router.delete("/{room_id}", dependencies=[Depends(require_write_auth)])
async def delete_room(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    state["rooms"] = [r for r in state["rooms"] if r["id"] != room_id]
    state["assignments"] = {d: r for d, r in state["assignments"].items() if r != room_id}
    plant_ids = {p["id"] for p in state["plants"] if p["room_id"] == room_id}
    state["plants"] = [p for p in state["plants"] if p["room_id"] != room_id]
    state["room_journal"] = [e for e in state["room_journal"] if e["room_id"] != room_id]
    state["plant_journal"] = [e for e in state["plant_journal"] if e["plant_id"] not in plant_ids]
    state["sensor_history"] = [e for e in state["sensor_history"] if e["room_id"] != room_id]
    save_state(state); return {"ok": True}


@router.get("/{room_id}/devices")
async def room_devices(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    devices = DeviceRegistry.from_env().list()
    return {"devices": [{"id": d.id, "name": d.name, "adapter": d.adapter, "assigned": state["assignments"].get(d.id) == room_id, "room_id": state["assignments"].get(d.id)} for d in devices]}


@router.post("/{room_id}/devices", dependencies=[Depends(require_write_auth)])
async def assign_device(room_id: str, body: DeviceAssignment):
    state = load_state(); room_or_404(state, room_id)
    try: DeviceRegistry.from_env().get(body.device_id)
    except KeyError as exc: raise HTTPException(404, "Gerät nicht gefunden") from exc
    state["assignments"][body.device_id] = room_id; save_state(state)
    return {"ok": True, "device_id": body.device_id, "room_id": room_id}


@router.delete("/{room_id}/devices/{device_id}", dependencies=[Depends(require_write_auth)])
async def unassign_device(room_id: str, device_id: str):
    state = load_state(); room_or_404(state, room_id)
    if state["assignments"].get(device_id) == room_id: state["assignments"].pop(device_id, None); save_state(state)
    return {"ok": True}


@router.get("/{room_id}/journal")
async def room_journal(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    return {"entries": [e for e in reversed(state["room_journal"]) if e["room_id"] == room_id]}


@router.post("/{room_id}/journal", dependencies=[Depends(require_write_auth)])
async def add_room_journal(room_id: str, body: JournalEntry):
    state = load_state(); room_or_404(state, room_id)
    row = {"id": new_id("entry"), "room_id": room_id, **body.model_dump(), "created_at": now_iso()}; state["room_journal"].append(row); save_state(state); return row


@router.get("/{room_id}/plants")
async def list_plants(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    return {"plants": [p for p in state["plants"] if p["room_id"] == room_id]}


@router.post("/{room_id}/plants", dependencies=[Depends(require_write_auth)])
async def create_plant(room_id: str, body: PlantCreate):
    state = load_state(); room_or_404(state, room_id)
    row = {"id": new_id("plant"), "room_id": room_id, **body.model_dump(), "created_at": now_iso(), "updated_at": now_iso()}; state["plants"].append(row); save_state(state); return row


@router.put("/{room_id}/plants/{plant_id}", dependencies=[Depends(require_write_auth)])
async def update_plant(room_id: str, plant_id: str, body: PlantCreate):
    state = load_state(); room_or_404(state, room_id); row = plant_or_404(state, plant_id)
    if row["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
    row.update(body.model_dump()); row["updated_at"] = now_iso(); save_state(state); return row


@router.delete("/{room_id}/plants/{plant_id}", dependencies=[Depends(require_write_auth)])
async def delete_plant(room_id: str, plant_id: str):
    state = load_state(); room_or_404(state, room_id); row = plant_or_404(state, plant_id)
    if row["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
    state["plants"] = [p for p in state["plants"] if p["id"] != plant_id]; state["plant_journal"] = [e for e in state["plant_journal"] if e["plant_id"] != plant_id]; save_state(state); return {"ok": True}


@router.get("/{room_id}/plants/{plant_id}/journal")
async def plant_journal(room_id: str, plant_id: str):
    state = load_state(); room_or_404(state, room_id); plant = plant_or_404(state, plant_id)
    if plant["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
    return {"entries": [e for e in reversed(state["plant_journal"]) if e["plant_id"] == plant_id]}


@router.post("/{room_id}/plants/{plant_id}/journal", dependencies=[Depends(require_write_auth)])
async def add_plant_journal(room_id: str, plant_id: str, body: JournalEntry):
    state = load_state(); room_or_404(state, room_id); plant = plant_or_404(state, plant_id)
    if plant["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
    row = {"id": new_id("entry"), "plant_id": plant_id, "room_id": room_id, **body.model_dump(), "created_at": now_iso()}; state["plant_journal"].append(row); save_state(state); return row


def append_sensor(state: dict[str, Any], room_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = {"id": new_id("sample"), "room_id": room_id, "timestamp": now_iso(), **payload}
    row["vpd_kpa"] = calc_vpd(row.get("temperature_c"), row.get("humidity_percent"))
    state["sensor_history"].append(row)
    state["sensor_history"] = state["sensor_history"][-50000:]
    return row


@router.get("/{room_id}/sensors")
async def sensor_history(room_id: str, limit: int = 500):
    state = load_state(); room_or_404(state, room_id); limit = min(max(limit, 1), 5000)
    rows = [e for e in state["sensor_history"] if e["room_id"] == room_id][-limit:]
    return {"samples": rows}


@router.post("/{room_id}/sensors", dependencies=[Depends(require_write_auth)])
async def add_sensor_sample(room_id: str, body: SensorSample):
    state = load_state(); room_or_404(state, room_id); row = append_sensor(state, room_id, body.model_dump()); save_state(state); return row


async def capture_room_sensors_once() -> int:
    state = load_state()
    if not state["rooms"] or not state["assignments"]: return 0
    overview = await device_overview(refresh=True)
    by_id = {d["id"]: d for d in overview.get("devices", [])}
    count = 0
    for room in state["rooms"]:
        rows = [by_id[d] for d, rid in state["assignments"].items() if rid == room["id"] and d in by_id]
        states = [r.get("state") or {} for r in rows if r.get("online")]
        temps = [float(s["temperature_c"]) for s in states if s.get("temperature_c") is not None]
        humidity = [float(s["humidity_percent"]) for s in states if s.get("humidity_percent") is not None]
        powers = [float(s["power_w"]) for s in states if s.get("power_w") is not None]
        energies = [float(s["energy_wh"]) for s in states if s.get("energy_wh") is not None]
        if not (temps or humidity or powers or energies): continue
        append_sensor(state, room["id"], {"temperature_c": round(sum(temps)/len(temps),2) if temps else None, "humidity_percent": round(sum(humidity)/len(humidity),2) if humidity else None, "co2_ppm": None, "soil_moisture_percent": None, "power_w": round(sum(powers),3) if powers else None, "energy_wh": round(sum(energies),3) if energies else None, "source": "assigned-devices"}); count += 1
    if count: save_state(state)
    return count


@router.post("/capture", dependencies=[Depends(require_write_auth)])
async def capture_now():
    return {"ok": True, "rooms_captured": await capture_room_sensors_once()}


async def _capture_loop() -> None:
    while True:
        try: await capture_room_sensors_once()
        except Exception: pass
        await asyncio.sleep(CAPTURE_INTERVAL_SECONDS)


def install(app) -> None:
    @app.on_event("startup")
    async def start_room_capture() -> None:
        global _capture_task
        if _capture_task is None or _capture_task.done(): _capture_task = asyncio.create_task(_capture_loop(), name="grow-central-room-history")

    @app.on_event("shutdown")
    async def stop_room_capture() -> None:
        global _capture_task
        if _capture_task:
            _capture_task.cancel()
            try: await _capture_task
            except asyncio.CancelledError: pass
            _capture_task = None
