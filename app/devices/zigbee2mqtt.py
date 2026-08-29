from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Iterable, Mapping

import aiomqtt

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


_PROPERTY_CAPABILITIES: dict[str, Capability] = {
    "state": Capability.POWER,
    "brightness": Capability.BRIGHTNESS,
    "temperature": Capability.TEMPERATURE,
    "humidity": Capability.HUMIDITY,
    "soil_moisture": Capability.SOIL_MOISTURE,
    "moisture": Capability.SOIL_MOISTURE,
    "soil_temperature": Capability.SOIL_TEMPERATURE,
    "conductivity": Capability.EC,
    "ec": Capability.EC,
    "ph": Capability.PH,
    "power": Capability.POWER_METER,
    "energy": Capability.ENERGY,
    "voltage": Capability.VOLTAGE,
    "current": Capability.CURRENT,
}

_STATE_ALIASES = {
    Capability.POWER: ("state",),
    Capability.BRIGHTNESS: ("brightness",),
    Capability.TEMPERATURE: ("temperature",),
    Capability.HUMIDITY: ("humidity",),
    Capability.SOIL_MOISTURE: ("soil_moisture", "moisture"),
    Capability.SOIL_TEMPERATURE: ("soil_temperature",),
    Capability.EC: ("ec", "conductivity"),
    Capability.PH: ("ph",),
    Capability.POWER_METER: ("power",),
    Capability.ENERGY: ("energy",),
    Capability.VOLTAGE: ("voltage",),
    Capability.CURRENT: ("current",),
}


def _walk_exposes(exposes: Iterable[Any]):
    for expose in exposes:
        if not isinstance(expose, dict):
            continue
        yield expose
        features = expose.get("features")
        if isinstance(features, list):
            yield from _walk_exposes(features)


def capabilities_from_exposes(exposes: Iterable[Any]) -> tuple[Capability, ...]:
    capabilities: list[Capability] = []
    for expose in _walk_exposes(exposes):
        names = (expose.get("property"), expose.get("name"))
        for raw_name in names:
            name = str(raw_name or "").strip().lower()
            capability = _PROPERTY_CAPABILITIES.get(name)
            if capability is not None:
                capabilities.append(capability)
    return tuple(dict.fromkeys(capabilities))


def infer_device_class(capabilities: tuple[Capability, ...]) -> DeviceClass:
    capset = set(capabilities)
    if Capability.BRIGHTNESS in capset:
        return DeviceClass.LIGHT
    if Capability.POWER in capset and len(capset) <= 4:
        return DeviceClass.SWITCH
    return DeviceClass.SENSOR


def normalize_zigbee_state(raw: Mapping[str, Any], capabilities: tuple[Capability, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {"online": True}
    for capability in capabilities:
        for key in _STATE_ALIASES.get(capability, ()): 
            if key not in raw or raw[key] is None:
                continue
            value = raw[key]
            if capability is Capability.POWER:
                if isinstance(value, str):
                    lowered = value.strip().lower()
                    if lowered in {"on", "true", "1"}:
                        value = True
                    elif lowered in {"off", "false", "0"}:
                        value = False
            result[capability.value] = value
            break
    return result


class Zigbee2MqttProvider(DeviceProvider):
    def __init__(self) -> None:
        descriptor = provider_by_id("zigbee")
        if descriptor is None:
            raise RuntimeError("zigbee provider missing from catalog")
        self.descriptor = descriptor
        self.host = os.getenv("GC_MQTT_HOST", "127.0.0.1")
        self.port = int(os.getenv("GC_MQTT_PORT", "1883"))
        self.username = os.getenv("GC_MQTT_USERNAME") or None
        self.password = os.getenv("GC_MQTT_PASSWORD") or None
        self.prefix = os.getenv("GC_Z2M_PREFIX", "zigbee2mqtt").strip("/")
        self.confirm_timeout = max(0.5, min(float(os.getenv("GC_Z2M_CONFIRM_TIMEOUT", "4")), 20.0))

    def _client(self) -> aiomqtt.Client:
        return aiomqtt.Client(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    async def _one(self, topic: str, timeout: float = 2.0) -> bytes:
        async with self._client() as client:
            await client.subscribe(topic)
            async with asyncio.timeout(timeout):
                async for message in client.messages:
                    if str(message.topic) == topic:
                        return bytes(message.payload)
        raise TimeoutError(f"no MQTT message for {topic}")

    async def _bridge_devices(self, timeout: float = 2.0) -> list[dict[str, Any]]:
        payload = await self._one(f"{self.prefix}/bridge/devices", timeout)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, list):
            raise ValueError("Zigbee2MQTT bridge/devices payload is not a list")
        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def _native_id(row: Mapping[str, Any]) -> str:
        return str(row.get("friendly_name") or row.get("ieee_address") or "").strip()

    @staticmethod
    def _definition(row: Mapping[str, Any]) -> Mapping[str, Any]:
        definition = row.get("definition")
        return definition if isinstance(definition, dict) else {}

    async def _device_info(self, native_id: str) -> tuple[dict[str, Any], tuple[Capability, ...]]:
        for row in await self._bridge_devices():
            if self._native_id(row) == native_id:
                definition = self._definition(row)
                exposes = definition.get("exposes") if isinstance(definition.get("exposes"), list) else []
                return row, capabilities_from_exposes(exposes)
        raise KeyError(f"unknown Zigbee device: {native_id}")

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        rows = await self._bridge_devices(max(0.2, min(timeout, 5.0)))
        result: list[DiscoveredDevice] = []
        for row in rows:
            if str(row.get("type") or "").lower() == "coordinator":
                continue
            native_id = self._native_id(row)
            if not native_id:
                continue
            definition = self._definition(row)
            exposes = definition.get("exposes") if isinstance(definition.get("exposes"), list) else []
            capabilities = capabilities_from_exposes(exposes)
            if not capabilities:
                continue
            model = str(definition.get("model") or row.get("model_id") or "") or None
            vendor = str(definition.get("vendor") or "") or None
            result.append(
                DiscoveredDevice(
                    provider_id="zigbee",
                    native_id=native_id,
                    name=native_id,
                    device_class=infer_device_class(capabilities),
                    capabilities=capabilities,
                    transport="zigbee",
                    model=model,
                    manufacturer=vendor,
                    metadata={
                        "ieee_address": row.get("ieee_address"),
                        "network_address": row.get("network_address"),
                        "description": definition.get("description"),
                        "source": "zigbee2mqtt",
                    },
                )
            )
        return sorted(result, key=lambda item: item.name.lower())

    async def state(self, native_id: str) -> Mapping[str, Any]:
        _, capabilities = await self._device_info(native_id)
        payload = await self._one(f"{self.prefix}/{native_id}")
        raw = json.loads(payload.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Zigbee device state is not a JSON object")
        return normalize_zigbee_state(raw, capabilities)

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        _, capabilities = await self._device_info(native_id)
        if capability not in capabilities:
            raise ValueError(f"device does not declare capability: {capability.value}")
        if capability is Capability.POWER:
            body = {"state": "ON" if bool(value) else "OFF"}
        elif capability is Capability.BRIGHTNESS:
            numeric = int(value)
            if not 0 <= numeric <= 254:
                raise ValueError("Zigbee brightness must be 0..254")
            body = {"brightness": numeric}
        else:
            raise ValueError(f"Zigbee write not enabled for capability: {capability.value}")

        state_topic = f"{self.prefix}/{native_id}"
        set_topic = f"{state_topic}/set"
        async with self._client() as client:
            # Subscribe before set. A successful write must be observed back in
            # the device state; publishing alone is never treated as success.
            await client.subscribe(state_topic)
            await client.publish(set_topic, json.dumps(body), qos=1, retain=False)
            async with asyncio.timeout(self.confirm_timeout):
                async for message in client.messages:
                    if str(message.topic) != state_topic:
                        continue
                    raw = json.loads(bytes(message.payload).decode("utf-8"))
                    if not isinstance(raw, dict):
                        continue
                    normalized = normalize_zigbee_state(raw, capabilities)
                    observed = normalized.get(capability.value)
                    expected = bool(value) if capability is Capability.POWER else int(value)
                    if observed == expected:
                        return normalized
        raise TimeoutError("Zigbee command was not confirmed by device state")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            row, _ = await self._device_info(native_id)
            disabled = bool(row.get("disabled", False))
            online = not disabled
            detail = "registered" if online else "disabled in Zigbee2MQTT"
        except Exception as exc:
            online = False
            detail = f"{type(exc).__name__}: {exc}"
        return DeviceHealth(
            online=online,
            detail=detail,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            transport="zigbee",
        )
