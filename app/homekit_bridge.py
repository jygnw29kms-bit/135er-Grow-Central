from __future__ import annotations

import asyncio
import json
import os
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


def _latest_room_values() -> list[dict[str, Any]]:
    from app.rooms import load_state
    try:
        state = load_state()
    except Exception:
        return []
    result = []
    for room in state.get("rooms", []):
        latest = next((x for x in reversed(state.get("sensor_history", [])) if x.get("room_id") == room.get("id")), None)
        if latest:
            result.append({"id": room.get("id"), "name": room.get("name") or room.get("id"), "latest": latest})
    return result


def _selected_switches():
    from app.smarthome.ha_bridge import _allowed, _writable
    from app.smarthome.registry import DeviceRegistry
    selected = _allowed("GC_HA_EXPORT_DEVICE_IDS")
    return [
        device for device in DeviceRegistry.from_env().list()
        if device.approved and device.id in selected and device.adapter != "home_assistant" and _writable(device)
    ]


def run_bridge() -> None:
    from pyhap.accessory import Accessory, Bridge
    from pyhap.accessory_driver import AccessoryDriver
    import pyqrcode

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)

    class RoomAccessory(Accessory):
        category = 10

        def __init__(self, *args, room_id: str, **kwargs):
            super().__init__(*args, **kwargs)
            self.room_id = room_id
            temperature = self.add_preload_service("TemperatureSensor")
            self.temperature_char = temperature.configure_char("CurrentTemperature", value=20.0)
            humidity = self.add_preload_service("HumiditySensor")
            self.humidity_char = humidity.configure_char("CurrentRelativeHumidity", value=50.0)
            soil = self.add_preload_service("HumiditySensor", chars=["Name"])
            soil.configure_char("Name", value=f"{self.display_name} Bodenfeuchte")
            self.soil_char = soil.configure_char("CurrentRelativeHumidity", value=50.0)

        def _update(self):
            row = {item["id"]: item for item in _latest_room_values()}.get(self.room_id)
            if not row:
                return
            latest = row["latest"]
            temperature = latest.get("temperature_c")
            humidity = latest.get("humidity_percent")
            soil = latest.get("soil_moisture_percent")
            if isinstance(temperature, (int, float)):
                self.temperature_char.set_value(max(-270, min(100, float(temperature))))
            if isinstance(humidity, (int, float)):
                self.humidity_char.set_value(max(0, min(100, float(humidity))))
            if isinstance(soil, (int, float)):
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
        async def run(self):
            while True:
                paired = bool(self.driver.state.paired_clients)
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
    bridge = GrowCentralBridge(driver, "Grow-Central")
    for row in _latest_room_values():
        try:
            bridge.add_accessory(RoomAccessory(driver, row["name"], room_id=row["id"]))
        except Exception:
            continue
    for device in _selected_switches():
        try:
            bridge.add_accessory(SwitchAccessory(driver, device.name, device=device))
        except Exception:
            continue
    driver.add_accessory(accessory=bridge)
    driver.start()


if __name__ == "__main__":
    run_bridge()