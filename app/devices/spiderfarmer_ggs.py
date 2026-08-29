from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Mapping

from bleak import BleakClient, BleakScanner

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice

GGS_NAME_HINT = "SF-GGS-CB"
GGS_NOTIFY_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
GGS_WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"


def _extract_json_objects(buffer: bytearray) -> list[dict[str, Any]]:
    """Extract complete JSON objects from a noisy/fragmented BLE byte stream."""
    results: list[dict[str, Any]] = []
    while True:
        try:
            start = buffer.index(ord("{"))
        except ValueError:
            buffer.clear()
            break
        if start:
            del buffer[:start]
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index, byte in enumerate(buffer):
            char = chr(byte)
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            break
        raw = bytes(buffer[:end])
        del buffer[:end]
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            results.append(value)
    return results


def normalize_ggs_status(message: Mapping[str, Any]) -> dict[str, Any]:
    if message.get("method") != "getDevSta" or message.get("code") not in (None, 200):
        raise ValueError("not a GGS status message")
    data = message.get("data", {})
    if not isinstance(data, Mapping):
        raise ValueError("GGS status missing data")
    state: dict[str, Any] = {"online": True}
    sensor = data.get("sensor", {})
    if isinstance(sensor, Mapping):
        if isinstance(sensor.get("temp"), (int, float)):
            state[Capability.TEMPERATURE.value] = float(sensor["temp"])
        if isinstance(sensor.get("humi"), (int, float)):
            state[Capability.HUMIDITY.value] = float(sensor["humi"])
        if isinstance(sensor.get("vpd"), (int, float)):
            state[Capability.VPD.value] = float(sensor["vpd"])
    fan = data.get("fan", {})
    if isinstance(fan, Mapping):
        if "on" in fan:
            state["fan_power"] = bool(fan.get("on"))
        if isinstance(fan.get("level"), (int, float)):
            # GGS fan level is observed as 0..10. Normalize to gc-device percent.
            state[Capability.FAN_SPEED.value] = max(0, min(100, int(round(float(fan["level"]) * 10))))
    light = data.get("light", {})
    if isinstance(light, Mapping):
        if "on" in light:
            state["light_power"] = bool(light.get("on"))
        if isinstance(light.get("level"), (int, float)):
            state[Capability.BRIGHTNESS.value] = max(0, min(100, int(round(float(light["level"])))))
    return state


class SpiderFarmerGgsProvider(DeviceProvider):
    """Local Spider Farmer GGS BLE telemetry provider.

    The public reverse-engineering work documents FF01 telemetry and FF02 command
    transport, but firmware compatibility has open questions. Grow Central starts
    read-only: telemetry is useful immediately and writes remain blocked until we
    validate commands on our own hardware/firmware combination.
    """

    def __init__(self) -> None:
        descriptor = provider_by_id("spider_farmer")
        if descriptor is None:
            raise RuntimeError("spider_farmer provider missing from catalog")
        self.descriptor = descriptor
        self.state_timeout = max(2.0, min(float(os.getenv("GC_SPIDERFARMER_STATE_TIMEOUT", "8")), 20.0))

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        timeout = max(1.0, min(timeout, 15.0))
        found = await BleakScanner.discover(timeout=timeout, return_adv=True)
        devices: list[DiscoveredDevice] = []
        for address, pair in found.items():
            device, adv = pair
            name = (adv.local_name or device.name or "").strip()
            if GGS_NAME_HINT.lower() not in name.lower():
                continue
            devices.append(DiscoveredDevice(
                provider_id=self.descriptor.id,
                native_id=address,
                name=name or "Spider Farmer GGS",
                device_class=DeviceClass.CONTROLLER,
                capabilities=(Capability.TEMPERATURE, Capability.HUMIDITY, Capability.VPD, Capability.FAN_SPEED, Capability.BRIGHTNESS),
                transport="ble",
                model="GGS Controller",
                manufacturer="Spider Farmer",
                signal=getattr(adv, "rssi", None),
                metadata={
                    "protocol": "ggs-ble-ff00-v1",
                    "write_state": "blocked_until_hardware_validation",
                    "notify_uuid": GGS_NOTIFY_UUID,
                },
            ))
        return sorted(devices, key=lambda item: (-(item.signal or -999), item.native_id))

    async def state(self, native_id: str) -> Mapping[str, Any]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=4)
        buffer = bytearray()

        def on_notify(_sender: Any, payload: bytearray) -> None:
            buffer.extend(payload)
            for message in _extract_json_objects(buffer):
                if message.get("method") == "getDevSta":
                    try:
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        pass

        async with BleakClient(native_id) as client:
            await client.start_notify(GGS_NOTIFY_UUID, on_notify)
            try:
                message = await asyncio.wait_for(queue.get(), timeout=self.state_timeout)
                return normalize_ggs_status(message)
            finally:
                try:
                    await client.stop_notify(GGS_NOTIFY_UUID)
                except Exception:
                    pass

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        del native_id, capability, value
        raise PermissionError("Spider Farmer GGS writes are blocked until model/firmware hardware validation")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            state = await self.state(native_id)
            return DeviceHealth(bool(state.get("online")), "telemetry received", round((time.perf_counter() - started) * 1000, 2), "ble")
        except Exception as exc:
            return DeviceHealth(False, f"{type(exc).__name__}: {exc}", round((time.perf_counter() - started) * 1000, 2), "ble")
