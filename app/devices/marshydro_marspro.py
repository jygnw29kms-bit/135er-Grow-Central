from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


_CAPS = (
    Capability.TEMPERATURE, Capability.HUMIDITY, Capability.VPD, Capability.PPFD,
    Capability.SOIL_TEMPERATURE, Capability.SOIL_MOISTURE, Capability.EC,
    Capability.POWER, Capability.BRIGHTNESS, Capability.FAN_SPEED,
)


class MarsHydroMarsProProvider(DeviceProvider):
    """Conservative Mars Hydro MarsPro telemetry adapter.

    The provider intentionally consumes a local telemetry cache written by a
    separately authenticated MarsPro transport bridge. Cloud credentials and
    MQTT session details never enter gc-device-v1. Writes stay disabled until
    a concrete model/firmware pair has passed hardware validation.
    """

    def __init__(self) -> None:
        descriptor = provider_by_id("mars_hydro")
        if descriptor is None:
            raise RuntimeError("mars_hydro provider missing from catalog")
        self.descriptor = descriptor
        self.cache_path = Path(os.getenv("GC_MARSHYDRO_CACHE", "/var/lib/grow-central/marshydro-devices.json"))

    def _load(self) -> list[dict[str, Any]]:
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return []
        rows = raw.get("devices", []) if isinstance(raw, dict) else []
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def normalize_state(raw: Mapping[str, Any]) -> dict[str, Any]:
        aliases = {
            "temperature": Capability.TEMPERATURE.value,
            "temp": Capability.TEMPERATURE.value,
            "humidity": Capability.HUMIDITY.value,
            "rh": Capability.HUMIDITY.value,
            "vpd": Capability.VPD.value,
            "ppfd": Capability.PPFD.value,
            "soil_temperature": Capability.SOIL_TEMPERATURE.value,
            "soil_temp": Capability.SOIL_TEMPERATURE.value,
            "soil_moisture": Capability.SOIL_MOISTURE.value,
            "soil_ec": Capability.EC.value,
            "ec": Capability.EC.value,
            "light_power": Capability.POWER.value,
            "light_level": Capability.BRIGHTNESS.value,
            "fan_level": Capability.FAN_SPEED.value,
        }
        state: dict[str, Any] = {"online": bool(raw.get("online", True))}
        for source, target in aliases.items():
            if source in raw and raw[source] is not None:
                state[target] = raw[source]
        return state

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        del timeout
        found: list[DiscoveredDevice] = []
        for row in self._load():
            native_id = str(row.get("serial") or row.get("id") or "").strip()
            if not native_id:
                continue
            model = str(row.get("model") or "MarsPro controller")
            found.append(DiscoveredDevice(
                provider_id=self.descriptor.id,
                native_id=native_id,
                name=str(row.get("name") or f"Mars Hydro {model}"),
                device_class=DeviceClass.CONTROLLER,
                capabilities=_CAPS,
                transport="cloud_mqtt_bridge",
                model=model,
                manufacturer="Mars Hydro",
                metadata={"read_only": True, "validated_writes": False, "source": "marspro-cache-v1"},
            ))
        return found

    async def state(self, native_id: str) -> Mapping[str, Any]:
        for row in self._load():
            if str(row.get("serial") or row.get("id") or "") == native_id:
                telemetry = row.get("state", row)
                if not isinstance(telemetry, dict):
                    raise ValueError("invalid Mars Hydro telemetry")
                return self.normalize_state(telemetry)
        raise KeyError(f"Mars Hydro device not found: {native_id}")

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        del native_id, capability, value
        raise PermissionError("Mars Hydro writes are locked until model/firmware hardware validation")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            state = await self.state(native_id)
            online = bool(state.get("online", False))
            detail = "telemetry available; writes locked" if online else "device reports offline"
        except Exception as exc:
            online = False
            detail = f"{type(exc).__name__}: {exc}"
        return DeviceHealth(online=online, detail=detail, latency_ms=round((time.perf_counter()-started)*1000, 2), transport="cloud_mqtt_bridge")
