"""Room organization, sensor history and grow journals for Grow Central."""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from contextlib import contextmanager
try:
    import fcntl
except ImportError:  # Windows test/development hosts
    fcntl = None
import json
import math
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.security import require_write_auth
from app.devices.runtime import runtime
from app.devices.gc_trust import TrustStore
from app.devices.gc_calibration import classify_soil_substrate_delta
from app.smarthome.registry import DeviceRegistry
from app.smarthome.router import device_overview

DATA_FILE = Path(os.getenv("GC_ROOMS_FILE", "/var/lib/135er-grow-central/rooms.json"))
CAPTURE_INTERVAL_SECONDS = max(60, int(os.getenv("GC_ROOM_CAPTURE_INTERVAL", "300")))
router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])
_capture_task: asyncio.Task | None = None
_LOCAL_STATE_LOCK = threading.RLock()
logger = logging.getLogger(__name__)


async def _native_gc_devices(timeout: float = 1.0) -> list[dict[str, Any]]:
    """Return native Grow-Central ESP32 devices in the room/overview row shape."""
    try:
        provider = runtime.get("growcentral_esp32")
        discovered = await provider.discover(timeout=max(0.1, min(timeout, 3.0)))
    except Exception:
        return []

    discovered = [device for device in discovered if (TrustStore().get(device.native_id) or {}).get("status") == "TRUSTED"]

    async def resolve(device) -> dict[str, Any]:
        online = False
        state: dict[str, Any] | None = None
        error: str | None = None
        try:
            health = await provider.health(device.native_id)
            online = health.online
            if online:
                state = dict(await provider.state(device.native_id))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        return {
            "id": device.global_id,
            "name": device.name,
            "adapter": device.provider_id,
            "provider_id": device.provider_id,
            "native_id": device.native_id,
            "online": online,
            "error": error,
            "state": state,
            "metadata": dict(device.metadata),
        }

    return list(await asyncio.gather(*(resolve(device) for device in discovered)))


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
    if not isinstance(raw, dict):
        raise RuntimeError("invalid rooms database: expected an object")
    for key, default in base.items():
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, type(default)):
            raise RuntimeError(f"invalid rooms database: {key}")
        if isinstance(value, list) and any(not isinstance(row, dict) for row in value):
            raise RuntimeError(f"invalid rooms database: {key} entries")
        base[key] = value
    return base


@contextmanager
def _state_lock() -> Iterator[None]:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = DATA_FILE.with_name(f".{DATA_FILE.name}.lock")
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        if hasattr(os, 'fchmod'):
            os.fchmod(fd, 0o600)
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        else:
            _LOCAL_STATE_LOCK.acquire()
        yield
    finally:
        if fcntl is None:
            _LOCAL_STATE_LOCK.release()
        os.close(fd)


def _write_state(state: dict[str, Any]) -> None:
    fd, temp = tempfile.mkstemp(prefix=f".{DATA_FILE.name}-", dir=DATA_FILE.parent)
    try:
        if hasattr(os, 'fchmod'):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, DATA_FILE)
    finally:
        Path(temp).unlink(missing_ok=True)


def save_state(state: dict[str, Any]) -> None:
    """Replace a complete snapshot. Production mutations should use edit_state."""
    with _state_lock():
        _write_state(state)


@contextmanager
def edit_state() -> Iterator[dict[str, Any]]:
    """Lock the whole read/modify/write operation; never await inside this scope."""
    with _state_lock():
        state = load_state()
        yield state
        _write_state(state)


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
    model_config = ConfigDict(allow_inf_nan=False)

    temperature_c: float | None = Field(default=None, ge=-30, le=80)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    co2_ppm: float | None = Field(default=None, ge=0, le=100000)
    soil_moisture_percent: float | None = Field(default=None, ge=0, le=100)
    soil_substrate_reference_percent: float | None = Field(default=None, ge=0, le=100)
    soil_substrate_index_percent: float | None = Field(default=None, ge=0)
    soil_substrate_delta_pp: float | None = Field(default=None, ge=-100, le=100)
    soil_substrate_state: Literal["below_reference", "near_reference", "above_reference"] | None = None
    power_w: float | None = Field(default=None, ge=0)
    energy_wh: float | None = Field(default=None, ge=0)
    source: str = Field(default="manual", max_length=100)


@router.get("")
async def list_rooms():
    state = load_state()
    counts: dict[str, int] = {}
    trust = TrustStore()
    for device_id, room_id in state["assignments"].items():
        if device_id.startswith("growcentral_esp32:"):
            native_id = device_id.split(":", 1)[1]
            if (trust.get(native_id) or {}).get("status") != "TRUSTED":
                continue
        counts[room_id] = counts.get(room_id, 0) + 1
    result = []
    for room in state["rooms"]:
        latest = next((x for x in reversed(state["sensor_history"]) if x["room_id"] == room["id"]), None)
        result.append({**room, "device_count": counts.get(room["id"], 0), "plant_count": sum(1 for p in state["plants"] if p["room_id"] == room["id"]), "latest_sensor": latest})
    return {"rooms": result}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_room(body: RoomCreate):
    with edit_state() as state:
        row = {"id": new_id("room"), **body.model_dump(), "created_at": now_iso(), "updated_at": now_iso()}
        state["rooms"].append(row)
        return row


@router.put("/{room_id}", dependencies=[Depends(require_write_auth)])
async def update_room(room_id: str, body: RoomUpdate):
    with edit_state() as state:
        row = room_or_404(state, room_id)
        row.update(body.model_dump()); row["updated_at"] = now_iso()
        return row


@router.delete("/{room_id}", dependencies=[Depends(require_write_auth)])
async def delete_room(room_id: str):
    with edit_state() as state:
        room_or_404(state, room_id)
        state["rooms"] = [r for r in state["rooms"] if r["id"] != room_id]
        state["assignments"] = {d: r for d, r in state["assignments"].items() if r != room_id}
        plant_ids = {p["id"] for p in state["plants"] if p["room_id"] == room_id}
        state["plants"] = [p for p in state["plants"] if p["room_id"] != room_id]
        state["room_journal"] = [e for e in state["room_journal"] if e["room_id"] != room_id]
        state["plant_journal"] = [e for e in state["plant_journal"] if e["plant_id"] not in plant_ids]
        state["sensor_history"] = [e for e in state["sensor_history"] if e["room_id"] != room_id]
        return {"ok": True}


@router.get("/{room_id}/devices")
async def room_devices(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    legacy = [
        {"id": d.id, "name": d.name, "adapter": d.adapter}
        for d in DeviceRegistry.from_env().list() if not d.id.startswith("growcentral_esp32:")
    ]
    native = await _native_gc_devices(timeout=0.8)
    merged: dict[str, dict[str, Any]] = {row["id"]: row for row in legacy}
    for row in native:
        merged[row["id"]] = row
    devices = []
    for row in merged.values():
        device_id = row["id"]
        devices.append({
            **row,
            "assigned": state["assignments"].get(device_id) == room_id,
            "room_id": state["assignments"].get(device_id),
        })
    return {"devices": sorted(devices, key=lambda row: (str(row.get("name") or "").lower(), row["id"]))}


@router.post("/{room_id}/devices", dependencies=[Depends(require_write_auth)])
async def assign_device(room_id: str, body: DeviceAssignment):
    state = load_state(); room_or_404(state, room_id)
    if body.device_id.startswith("growcentral_esp32:"):
        try:
            TrustStore().require_trusted(body.device_id.split(":", 1)[1])
        except PermissionError as exc:
            raise HTTPException(403, "Sensor muss zuerst manuell angenommen werden") from exc
    exists = True
    try:
        DeviceRegistry.from_env().get(body.device_id)
    except KeyError:
        native = await _native_gc_devices(timeout=1.2)
        exists = any(row["id"] == body.device_id for row in native)
    if not exists:
        raise HTTPException(404, "Gerät nicht gefunden")
    with edit_state() as current:
        room_or_404(current, room_id)
        current["assignments"][body.device_id] = room_id
    return {"ok": True, "device_id": body.device_id, "room_id": room_id}


@router.delete("/{room_id}/devices/{device_id}", dependencies=[Depends(require_write_auth)])
async def unassign_device(room_id: str, device_id: str):
    with edit_state() as state:
        room_or_404(state, room_id)
        if state["assignments"].get(device_id) == room_id: state["assignments"].pop(device_id, None)
        return {"ok": True}


@router.get("/{room_id}/journal")
async def room_journal(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    return {"entries": [e for e in reversed(state["room_journal"]) if e["room_id"] == room_id]}


@router.post("/{room_id}/journal", dependencies=[Depends(require_write_auth)])
async def add_room_journal(room_id: str, body: JournalEntry):
    with edit_state() as state:
        room_or_404(state, room_id)
        row = {"id": new_id("entry"), "room_id": room_id, **body.model_dump(), "created_at": now_iso()}; state["room_journal"].append(row); return row


@router.get("/{room_id}/plants")
async def list_plants(room_id: str):
    state = load_state(); room_or_404(state, room_id)
    return {"plants": [p for p in state["plants"] if p["room_id"] == room_id]}


@router.post("/{room_id}/plants", dependencies=[Depends(require_write_auth)])
async def create_plant(room_id: str, body: PlantCreate):
    with edit_state() as state:
        room_or_404(state, room_id)
        row = {"id": new_id("plant"), "room_id": room_id, **body.model_dump(), "created_at": now_iso(), "updated_at": now_iso()}; state["plants"].append(row); return row


@router.put("/{room_id}/plants/{plant_id}", dependencies=[Depends(require_write_auth)])
async def update_plant(room_id: str, plant_id: str, body: PlantCreate):
    with edit_state() as state:
        room_or_404(state, room_id); row = plant_or_404(state, plant_id)
        if row["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
        row.update(body.model_dump()); row["updated_at"] = now_iso(); return row


@router.delete("/{room_id}/plants/{plant_id}", dependencies=[Depends(require_write_auth)])
async def delete_plant(room_id: str, plant_id: str):
    with edit_state() as state:
        room_or_404(state, room_id); row = plant_or_404(state, plant_id)
        if row["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
        state["plants"] = [p for p in state["plants"] if p["id"] != plant_id]; state["plant_journal"] = [e for e in state["plant_journal"] if e["plant_id"] != plant_id]; return {"ok": True}


@router.get("/{room_id}/plants/{plant_id}/journal")
async def plant_journal(room_id: str, plant_id: str):
    state = load_state(); room_or_404(state, room_id); plant = plant_or_404(state, plant_id)
    if plant["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
    return {"entries": [e for e in reversed(state["plant_journal"]) if e["plant_id"] == plant_id]}


@router.post("/{room_id}/plants/{plant_id}/journal", dependencies=[Depends(require_write_auth)])
async def add_plant_journal(room_id: str, plant_id: str, body: JournalEntry):
    with edit_state() as state:
        room_or_404(state, room_id); plant = plant_or_404(state, plant_id)
        if plant["room_id"] != room_id: raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
        row = {"id": new_id("entry"), "plant_id": plant_id, "room_id": room_id, **body.model_dump(), "created_at": now_iso()}; state["plant_journal"].append(row); return row


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


def _csv_cell(value: Any) -> Any:
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        # Prevent user-entered source labels from executing as spreadsheet formulas.
        return "'" + value
    return value


@router.get("/{room_id}/sensors.csv")
async def export_sensor_history(room_id: str, limit: int = Query(default=5000, ge=1, le=50000)):
    state = load_state()
    room_or_404(state, room_id)
    rows = [row for row in state["sensor_history"] if row["room_id"] == room_id][-limit:]
    columns = ["timestamp", "temperature_c", "humidity_percent", "vpd_kpa", "co2_ppm",
               "soil_moisture_percent", "soil_substrate_reference_percent",
               "soil_substrate_index_percent", "soil_substrate_delta_pp", "soil_substrate_state",
               "soil_calibration_status", "power_w", "energy_wh", "source"]
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        export = {**row,
                  "soil_calibration_status": row.get("soil_calibration_status") or ("calibration_required" if row.get("soil_moisture_percent") is not None else "")}
        writer.writerow([_csv_cell(export.get(key)) for key in columns])
    return Response(output.getvalue(), media_type="text/csv", headers={
        "Content-Disposition": 'attachment; filename="grow-central-sensors.csv"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })



@router.post("/{room_id}/sensors", dependencies=[Depends(require_write_auth)])
async def add_sensor_sample(room_id: str, body: SensorSample):
    with edit_state() as state:
        room_or_404(state, room_id); row = append_sensor(state, room_id, body.model_dump()); return row


def _measurement(state: dict[str, Any], key: str, minimum: float, maximum: float | None = None, alias: str | None = None) -> float | None:
    value = state.get(key)
    if value is None and alias:
        value = state.get(alias)
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < minimum or (maximum is not None and number > maximum):
        return None
    return number


async def capture_room_sensors_once() -> int:
    initial = load_state()
    if not initial["rooms"] or not initial["assignments"]:
        return 0
    overview = await device_overview(refresh=True)
    combined_devices = [row for row in overview.get("devices", []) if not str(row.get("id", "")).startswith("growcentral_esp32:")]
    combined_devices.extend(await _native_gc_devices(timeout=0.8))
    by_id = {d["id"]: d for d in combined_devices}
    count = 0
    # Network reads can take seconds. Reload after them so UI edits, deletions,
    # and sensor acceptance completed during the read cannot be overwritten.
    with edit_state() as state:
        for room in state["rooms"]:
            rows = [by_id[d] for d, rid in state["assignments"].items() if rid == room["id"] and d in by_id]
            states = [r.get("state") for r in rows if r.get("online") and isinstance(r.get("state"), dict)]
            measurements = {
                "temperature_c": ("temperature_c", -30, 80, "temperature"),
                "humidity_percent": ("humidity_percent", 0, 100, "humidity"),
                "co2_ppm": ("co2_ppm", 0, 100000, None),
                "soil_moisture_percent": ("soil_moisture", 0, 100, None),
                "soil_substrate_reference_percent": ("soil_substrate_reference_percent", 0, 100, None),
                "soil_substrate_index_percent": ("soil_substrate_index_percent", 0, None, None),
                "soil_substrate_delta_pp": ("soil_substrate_delta_pp", -100, 100, None),
                "power_w": ("power_w", 0, None, None),
                "energy_wh": ("energy_wh", 0, None, None),
            }
            payload: dict[str, Any] = {}
            for target, arguments in measurements.items():
                values = [value for row in states if (value := _measurement(row, *arguments)) is not None]
                total = sum(values)
                payload[target] = round(total if target in {"power_w", "energy_wh"} else total / len(values), 3) if values and math.isfinite(total) else None
            calibration_states = [str((row.get('meta') or {}).get('calibration_status') or '') for row in states if isinstance(row.get('meta'), dict)]
            if payload.get("soil_substrate_delta_pp") is not None:
                payload["soil_substrate_state"] = classify_soil_substrate_delta(float(payload["soil_substrate_delta_pp"]))
            if any(value == 'valid' for value in calibration_states):
                payload['soil_calibration_status'] = 'valid'
            elif any(value == 'required' for value in calibration_states):
                payload['soil_calibration_status'] = 'required'
            if all(value is None for key, value in payload.items() if key != 'soil_calibration_status'):
                continue
            append_sensor(state, room["id"], {**payload, "source": "assigned-devices"})
            count += 1
    return count


@router.post("/capture", dependencies=[Depends(require_write_auth)])
async def capture_now():
    return {"ok": True, "rooms_captured": await capture_room_sensors_once()}


async def _capture_loop() -> None:
    while True:
        try: await capture_room_sensors_once()
        except Exception:
            logger.exception("Room sensor capture failed; next interval will retry")
        await asyncio.sleep(CAPTURE_INTERVAL_SECONDS)


def install(app) -> None:
    async def start_room_capture() -> None:
        global _capture_task
        if _capture_task is None or _capture_task.done():
            _capture_task = asyncio.create_task(_capture_loop(), name="grow-central-room-history")

    async def stop_room_capture() -> None:
        global _capture_task
        if _capture_task:
            _capture_task.cancel()
            try:
                await _capture_task
            except asyncio.CancelledError:
                pass
            _capture_task = None

    app.router.add_event_handler("startup", start_room_capture)
    app.router.add_event_handler("shutdown", stop_room_capture)
