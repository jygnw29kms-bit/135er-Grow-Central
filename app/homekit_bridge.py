from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

STATE_DIR = Path(os.getenv("GC_HOMEKIT_DIR", "/var/lib/135er-grow-central/homekit"))
STATUS_FILE = STATE_DIR / "status.json"
QR_FILE = STATE_DIR / "pairing.svg"
PERSIST_FILE = STATE_DIR / "accessory.state"
router = APIRouter(prefix="/api/v1/homekit", tags=["homekit"])


def _status() -> dict[str, Any]:
    if not STATUS_FILE.is_file():
        return {"available": False, "running": False, "paired": False, "name": "Grow-Central", "message": "HomeKit-Bridge wurde noch nicht gestartet."}
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return {"available": True, **data}
    except (OSError, ValueError, TypeError):
        return {"available": False, "running": False, "paired": False, "name": "Grow-Central", "message": "HomeKit-Status ist nicht lesbar."}


@router.get("/status")
async def homekit_status():
    return _status()


@router.get("/pairing.svg")
async def homekit_pairing_qr():
    status = _status()
    if status.get("paired"):
        raise HTTPException(409, "Grow-Central ist bereits mit Apple Home gekoppelt.")
    if not QR_FILE.is_file():
        raise HTTPException(503, "HomeKit-QR ist noch nicht verfuegbar.")
    return FileResponse(QR_FILE, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


HOMEKIT_HISTORY_WINDOW = 12
HOMEKIT_FRESH_SECONDS = 15 * 60
_HOMEKIT_METRICS = (("temperature_c", "temperature"), ("humidity_percent", "humidity"), ("soil_moisture_percent", "soil_moisture"))


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(row: dict[str, Any], now: datetime) -> bool:
    timestamp = _timestamp(row.get("timestamp"))
    if timestamp is None:
        return False
    age = (now - timestamp).total_seconds()
    return 0 <= age <= HOMEKIT_FRESH_SECONDS


def _metric_allowed(key: str, row: dict[str, Any]) -> bool:
    if key == "soil_moisture_percent":
        return row.get("soil_calibration_status") == "valid"
    return True


def _stable_aid(kind: str, identifier: str, used: set[int]) -> int:
    salt = 0
    while True:
        material = f"{kind}:{identifier}:{salt}".encode("utf-8")
        aid = 2 + (int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 2_000_000_000)
        if aid != 7 and aid not in used:
            used.add(aid)
            return aid
        salt += 1


def _accessory_aids(room_rows, switches) -> dict[tuple[str, str], int]:
    used: set[int] = {1, 7}
    result: dict[tuple[str, str], int] = {}
    keys = [("room", str(row.get("id") or "")) for row in room_rows]
    keys += [("switch", str(getattr(device, "id", ""))) for device in switches]
    for key in sorted(keys):
        result[key] = _stable_aid(key[0], key[1], used)
    return result


def _room_services(snapshot: dict[str, Any]) -> tuple[str, ...]:
    return tuple(service for key, service in _HOMEKIT_METRICS if _valid_number(snapshot.get(key)))


def _latest_room_values(*, now: datetime | None = None) -> list[dict[str, Any]]:
    from app.rooms import load_state
    try:
        state = load_state()
    except Exception:
        return []
    now = now or datetime.now(timezone.utc)
    history = state.get("sensor_history", [])
    result = []
    for room in state.get("rooms", []):
        room_history = [
            row for row in history
            if row.get("room_id") == room.get("id") and _fresh(row, now)
        ][-HOMEKIT_HISTORY_WINDOW:]
        if not room_history:
            continue
        snapshot = dict(room_history[-1])
        for key, _service in _HOMEKIT_METRICS:
            value = next((
                row.get(key) for row in reversed(room_history)
                if _metric_allowed(key, row) and _valid_number(row.get(key))
            ), None)
            if value is not None:
                snapshot[key] = value
            else:
                snapshot.pop(key, None)
        services = _room_services(snapshot)
        if not services:
            continue
        result.append({"id": room.get("id"), "name": room.get("name") or room.get("id"), "latest": snapshot, "services": services})
    return sorted(result, key=lambda row: str(row.get("id") or ""))


def _selected_switches():
    from app.smarthome.ha_bridge import _allowed, _writable
    from app.smarthome.registry import DeviceRegistry
    selected = _allowed("GC_HA_EXPORT_DEVICE_IDS")
    return sorted(
        [
            device for device in DeviceRegistry.from_env().list()
            if device.approved and device.id in selected and device.adapter != "home_assistant" and _writable(device)
        ],
        key=lambda device: str(device.id),
    )


def _topology_signature(room_rows=None, switches=None):
    room_rows = _latest_room_values() if room_rows is None else room_rows
    switches = _selected_switches() if switches is None else switches
    rooms = tuple(sorted((str(row.get("id") or ""), str(row.get("name") or ""), tuple(row.get("services") or ())) for row in room_rows))
    switch_rows = tuple(sorted((str(getattr(device, "id", "")), str(getattr(device, "name", ""))) for device in switches))
    return rooms, switch_rows


def run_bridge() -> None:
    from pyhap.accessory import Accessory, Bridge
    from pyhap.accessory_driver import AccessoryDriver
    import pyqrcode

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)

    class RoomAccessory(Accessory):
        category = 10

        def __init__(self, *args, room_id: str, initial_latest: dict[str, Any], services: tuple[str, ...], **kwargs):
            super().__init__(*args, **kwargs)
            self.room_id = room_id
            self.temperature_char = None
            self.humidity_char = None
            self.soil_char = None
            if "temperature" in services:
                temperature = self.add_preload_service("TemperatureSensor")
                self.temperature_char = temperature.configure_char("CurrentTemperature", value=max(-270, min(100, float(initial_latest["temperature_c"]))))
            if "humidity" in services:
                humidity = self.add_preload_service("HumiditySensor")
                self.humidity_char = humidity.configure_char("CurrentRelativeHumidity", value=max(0, min(100, float(initial_latest["humidity_percent"]))))
            if "soil_moisture" in services:
                soil = self.add_preload_service("HumiditySensor", chars=["Name"])
                soil.configure_char("Name", value=f"{self.display_name} Bodenfeuchte")
                self.soil_char = soil.configure_char("CurrentRelativeHumidity", value=max(0, min(100, float(initial_latest["soil_moisture_percent"]))))

        def _update(self):
            row = {item["id"]: item for item in _latest_room_values()}.get(self.room_id)
            if not row:
                return
            latest = row["latest"]
            temperature = latest.get("temperature_c")
            humidity = latest.get("humidity_percent")
            soil = latest.get("soil_moisture_percent")
            if self.temperature_char is not None and _valid_number(temperature):
                self.temperature_char.set_value(max(-270, min(100, float(temperature))))
            if self.humidity_char is not None and _valid_number(humidity):
                self.humidity_char.set_value(max(0, min(100, float(humidity))))
            if self.soil_char is not None and _valid_number(soil):
                self.soil_char.set_value(max(0, min(100, float(soil))))

        async def run(self):
            while True:
                try:
                    self._update()
                except Exception:
                    pass
                await asyncio.sleep(15)

    class SwitchAccessory(Accessory):
        category = 8

        def __init__(self, *args, device, **kwargs):
            super().__init__(*args, **kwargs)
            self.device = device
            service = self.add_preload_service("Switch")
            self.on_char = service.configure_char("On", value=False, setter_callback=self._request)

        def _request(self, value):
            self.driver.add_job(self._set(bool(value)))

        async def _set(self, value: bool):
            from app.smarthome.adapters.factory import build_switch_adapter
            try:
                state = await build_switch_adapter(self.device).set_switch(value)
                if isinstance(state.get("on"), bool):
                    self.on_char.set_value(state["on"])
            except Exception:
                pass

        async def run(self):
            from app.smarthome.adapters.factory import build_switch_adapter
            while True:
                try:
                    state = await build_switch_adapter(self.device).read_state()
                    if isinstance(state.get("on"), bool):
                        self.on_char.set_value(state["on"])
                except Exception:
                    pass
                await asyncio.sleep(10)

    class GrowCentralBridge(Bridge):
        def __init__(self, *args, topology_signature, **kwargs):
            super().__init__(*args, **kwargs)
            self.topology_signature = topology_signature

        async def run(self):
            # Bridge.run schedules each child accessory's run() coroutine. Without
            # this call room values and switch readback remain at their initial state.
            await super().run()
            while True:
                paired = bool(self.driver.state.paired_clients)
                if _topology_signature() != self.topology_signature:
                    STATUS_FILE.write_text(json.dumps({
                        "running": True, "paired": paired, "restarting": True,
                        "name": "Grow-Central", "message": "HomeKit-Konfiguration ge\u00e4ndert; Bridge wird neu geladen."
                    }, ensure_ascii=False, indent=2), encoding="utf-8")
                    os.chmod(STATUS_FILE, 0o600)
                    self.driver.stop()
                    return
                payload = {
                    "running": True,
                    "paired": paired,
                    "name": "Grow-Central",
                    "port": self.driver.state.port,
                    "setup_code": None if paired else self.driver.state.pincode.decode(),
                    "setup_uri": None if paired else self.xhm_uri(),
                    "accessories_exported": len(self.accessories),
                    "message": "Mit Apple Home gekoppelt." if paired else "Bereit zum Koppeln mit Apple Home.",
                }
                STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                os.chmod(STATUS_FILE, 0o600)
                if not paired:
                    pyqrcode.create(self.xhm_uri()).svg(str(QR_FILE), scale=8, quiet_zone=4)
                    os.chmod(QR_FILE, 0o600)
                else:
                    QR_FILE.unlink(missing_ok=True)
                await asyncio.sleep(5)

    driver = AccessoryDriver(port=int(os.getenv("GC_HOMEKIT_PORT", "51827")), persist_file=str(PERSIST_FILE))
    room_rows = _latest_room_values()
    selected_switches = _selected_switches()
    bridge = GrowCentralBridge(driver, "Grow-Central", topology_signature=_topology_signature(room_rows, selected_switches))
    aids = _accessory_aids(room_rows, selected_switches)
    for row in room_rows:
        try:
            bridge.add_accessory(RoomAccessory(driver, row["name"], aid=aids[("room", str(row["id"]))], room_id=row["id"], initial_latest=row["latest"], services=tuple(row["services"])))
        except Exception:
            continue
    for device in selected_switches:
        try:
            bridge.add_accessory(SwitchAccessory(driver, device.name, aid=aids[("switch", str(device.id))], device=device))
        except Exception:
            continue
    driver.add_accessory(accessory=bridge)
    driver.start()


if __name__ == "__main__":
    run_bridge()