from __future__ import annotations

import asyncio
import json
import os
import ssl
import time
from pathlib import Path
from typing import Any, Mapping

import aiomqtt

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice

MARS_MQTT_HOST = "mars-pro.mqtt.lgledsolutions.com"
MARS_MQTT_PORT = 8883


def normalize_mars_status(message: Mapping[str, Any]) -> dict[str, Any]:
    if message.get("method") != "getDevSta" or message.get("code") not in (None, 200):
        raise ValueError("not a Mars Pro device status message")
    data = message.get("data", {})
    if not isinstance(data, Mapping):
        raise ValueError("Mars status missing data")
    state: dict[str, Any] = {"online": True}
    sensor = data.get("sensor", {})
    if isinstance(sensor, Mapping):
        mapping = {
            "temp": Capability.TEMPERATURE,
            "humi": Capability.HUMIDITY,
            "vpd": Capability.VPD,
            "ppfd": Capability.PPFD,
            "tempSoil": Capability.SOIL_TEMPERATURE,
            "humiSoil": Capability.SOIL_MOISTURE,
            "ECSoil": Capability.EC,
        }
        for source, capability in mapping.items():
            value = sensor.get(source)
            if isinstance(value, (int, float)):
                state[capability.value] = float(value)
    light = data.get("light", {})
    if isinstance(light, Mapping):
        if "on" in light:
            state["light_power"] = bool(light.get("on"))
        if isinstance(light.get("level"), (int, float)):
            state[Capability.BRIGHTNESS.value] = max(0, min(100, int(round(float(light["level"])))))
    # Mars Pro distinguishes oscillating fan (`fan`) and inline exhaust (`blower`).
    blower = data.get("blower", {})
    fan = data.get("fan", {})
    actuator = blower if isinstance(blower, Mapping) and blower else fan
    if isinstance(actuator, Mapping):
        if "on" in actuator:
            state["fan_power"] = bool(actuator.get("on"))
        if isinstance(actuator.get("level"), (int, float)):
            state[Capability.FAN_SPEED.value] = max(0, min(100, int(round(float(actuator["level"])))))
    for key, prefix in (("humidifier", "humidifier"), ("dehumidifier", "dehumidifier")):
        item = data.get(key, {})
        if isinstance(item, Mapping) and "on" in item:
            state[f"{prefix}_power"] = bool(item.get("on"))
    return state


class MarsHydroMarsProProvider(DeviceProvider):
    """Read-only Mars Pro cloud MQTT telemetry for explicitly configured devices.

    Credentials returned by the Mars Pro account flow are kept in an external
    root-readable file. The controller remains EXPERIMENTAL until Grow Central
    validates concrete model/firmware combinations. Writes are deliberately
    blocked even though `setConfigField` is documented by community research.
    """

    def __init__(self) -> None:
        descriptor = provider_by_id("mars_hydro")
        if descriptor is None:
            raise RuntimeError("mars_hydro provider missing from catalog")
        self.descriptor = descriptor
        self.config_path = Path(os.getenv("GC_MARS_DEVICE_CONFIG", "/etc/grow-central/mars-hydro.json"))
        self.timeout = max(2.0, min(float(os.getenv("GC_MARS_MQTT_TIMEOUT", "8")), 20.0))

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.config_path.exists():
            return {}
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        rows = raw.get("devices", []) if isinstance(raw, dict) else []
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            native_id = str(row.get("id", "")).strip()
            if native_id:
                result[native_id] = row
        return result

    @staticmethod
    def _validate(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
        serial = str(row.get("serial", "")).strip()
        model = str(row.get("model", "")).strip().removeprefix("MH-")
        username = str(row.get("mqtt_username", "")).strip()
        password = str(row.get("mqtt_password", "")).strip()
        if not all((serial, model, username, password)):
            raise ValueError("Mars device requires serial, model, mqtt_username and mqtt_password")
        return serial, model, username, password

    @staticmethod
    def _tls_context(row: Mapping[str, Any]) -> ssl.SSLContext:
        context = ssl.create_default_context()
        ca_file = str(row.get("ca_file", "")).strip()
        if ca_file:
            context.load_verify_locations(cafile=ca_file)
        return context

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        del timeout
        devices: list[DiscoveredDevice] = []
        for native_id, row in self._load().items():
            try:
                serial, model, _username, _password = self._validate(row)
            except ValueError:
                continue
            devices.append(DiscoveredDevice(
                provider_id=self.descriptor.id,
                native_id=native_id,
                name=str(row.get("name") or f"Mars Hydro {model}"),
                device_class=DeviceClass.CONTROLLER,
                capabilities=(Capability.TEMPERATURE, Capability.HUMIDITY, Capability.VPD, Capability.PPFD, Capability.SOIL_TEMPERATURE, Capability.SOIL_MOISTURE, Capability.EC, Capability.BRIGHTNESS, Capability.FAN_SPEED),
                transport="cloud_mqtt",
                model=f"MH-{model}",
                manufacturer="Mars Hydro",
                metadata={"protocol": "mars-pro-mqtt-v1", "serial_suffix": serial[-4:], "write_state": "blocked_until_hardware_validation"},
            ))
        return sorted(devices, key=lambda item: (item.name.lower(), item.native_id))

    async def state(self, native_id: str) -> Mapping[str, Any]:
        row = self._load().get(native_id)
        if row is None:
            raise KeyError(native_id)
        serial, model, username, password = self._validate(row)
        up = f"MHPRO/{model}/API/UP/{serial}"
        down = f"MHPRO/{model}/API/DOWN/{serial}"
        request = json.dumps({"method": "getDevSta", "params": {"pid": serial}}, separators=(",", ":"))
        client_id = f"growcentral-{native_id}-{int(time.time())}"
        async with aiomqtt.Client(
            hostname=MARS_MQTT_HOST,
            port=MARS_MQTT_PORT,
            username=username,
            password=password,
            identifier=client_id,
            tls_context=self._tls_context(row),
        ) as client:
            await client.subscribe(up)
            await client.publish(down, payload=request, qos=1, retain=False)
            async with asyncio.timeout(self.timeout):
                async for message in client.messages:
                    if str(message.topic) != up:
                        continue
                    try:
                        payload = json.loads(bytes(message.payload).decode("utf-8"))
                        if isinstance(payload, dict) and payload.get("method") == "getDevSta":
                            return normalize_mars_status(payload)
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                        continue
        raise TimeoutError("Mars Pro telemetry timed out")

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        del native_id, capability, value
        raise PermissionError("Mars Hydro writes are blocked until model/firmware hardware validation")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            state = await self.state(native_id)
            return DeviceHealth(bool(state.get("online")), "Mars Pro telemetry received", round((time.perf_counter() - started) * 1000, 2), "cloud_mqtt")
        except Exception as exc:
            return DeviceHealth(False, f"{type(exc).__name__}: {exc}", round((time.perf_counter() - started) * 1000, 2), "cloud_mqtt")
