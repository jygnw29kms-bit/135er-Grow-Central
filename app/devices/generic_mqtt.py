from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any, Mapping

import aiomqtt

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


class GenericMqttProvider(DeviceProvider):
    """Schema-based MQTT bridge for DIY/community devices.

    Devices publish retained metadata at <root>/<id>/config and retained state at
    <root>/<id>/state. Writes use <root>/<id>/set and must be confirmed on
    <root>/<id>/ack. No arbitrary topic templates are executed.
    """

    def __init__(self) -> None:
        descriptor = provider_by_id("mqtt")
        if descriptor is None:
            raise RuntimeError("mqtt provider missing from catalog")
        self.descriptor = descriptor
        self.host = os.getenv("GC_MQTT_HOST", "127.0.0.1")
        self.port = int(os.getenv("GC_MQTT_PORT", "1883"))
        self.username = os.getenv("GC_MQTT_USERNAME") or None
        self.password = os.getenv("GC_MQTT_PASSWORD") or None
        self.root = os.getenv("GC_GENERIC_MQTT_PREFIX", "growcentral/devices").strip("/")
        self.command_timeout = max(0.5, min(float(os.getenv("GC_MQTT_COMMAND_TIMEOUT", "5")), 30.0))

    def _client(self) -> aiomqtt.Client:
        return aiomqtt.Client(hostname=self.host, port=self.port, username=self.username, password=self.password)

    def _topic(self, native_id: str, leaf: str) -> str:
        if not native_id or "/" in native_id or "+" in native_id or "#" in native_id:
            raise ValueError("invalid MQTT device id")
        return f"{self.root}/{native_id}/{leaf}"

    async def _one(self, topic: str, timeout: float = 2.0) -> bytes:
        async with self._client() as client:
            await client.subscribe(topic)
            async with asyncio.timeout(timeout):
                async for message in client.messages:
                    if str(message.topic) == topic:
                        return bytes(message.payload)
        raise TimeoutError(f"no MQTT message for {topic}")

    @staticmethod
    def _parse_config(payload: bytes) -> dict[str, Any]:
        raw = json.loads(payload.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("MQTT config must be an object")
        native_id = str(raw.get("id", "")).strip()
        name = str(raw.get("name", native_id)).strip()
        try:
            device_class = DeviceClass(str(raw.get("device_class", "sensor")))
        except ValueError as exc:
            raise ValueError("unknown device_class") from exc
        caps_raw = raw.get("capabilities", [])
        if not isinstance(caps_raw, list):
            raise ValueError("capabilities must be a list")
        capabilities: list[Capability] = []
        for value in caps_raw:
            try:
                capability = Capability(str(value))
            except ValueError:
                continue
            if capability not in capabilities:
                capabilities.append(capability)
        if not native_id or not name or not capabilities:
            raise ValueError("config requires id, name and known capabilities")
        return {**raw, "id": native_id, "name": name, "device_class": device_class, "capabilities": tuple(capabilities)}

    @staticmethod
    def _normalize_state(payload: bytes, capabilities: tuple[Capability, ...]) -> dict[str, Any]:
        raw = json.loads(payload.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("MQTT state must be an object")
        allowed = {cap.value for cap in capabilities}
        state = {str(key): value for key, value in raw.items() if str(key) in allowed}
        state["online"] = bool(raw.get("online", True))
        return state

    async def _config(self, native_id: str) -> dict[str, Any]:
        config = self._parse_config(await self._one(self._topic(native_id, "config")))
        if config["id"] != native_id:
            raise ValueError("config id does not match MQTT topic")
        return config

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        timeout = max(0.1, min(timeout, 15.0))
        found: dict[str, DiscoveredDevice] = {}
        async with self._client() as client:
            await client.subscribe(f"{self.root}/+/config")
            try:
                async with asyncio.timeout(timeout):
                    async for message in client.messages:
                        try:
                            config = self._parse_config(bytes(message.payload))
                            topic_id = str(message.topic).split("/")[-2]
                            if config["id"] != topic_id:
                                continue
                        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        found[config["id"]] = DiscoveredDevice(
                            provider_id=self.descriptor.id,
                            native_id=config["id"],
                            name=config["name"],
                            device_class=config["device_class"],
                            capabilities=config["capabilities"],
                            transport="mqtt",
                            model=str(config.get("model") or "") or None,
                            manufacturer=str(config.get("manufacturer") or "Generic MQTT"),
                            metadata={"protocol": "gc-generic-mqtt-v1", "topic_root": self.root},
                        )
            except TimeoutError:
                pass
        return sorted(found.values(), key=lambda item: (item.name.lower(), item.native_id))

    async def state(self, native_id: str) -> Mapping[str, Any]:
        config = await self._config(native_id)
        return self._normalize_state(await self._one(self._topic(native_id, "state")), config["capabilities"])

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        config = await self._config(native_id)
        if capability not in config["capabilities"]:
            raise ValueError(f"device does not declare capability: {capability.value}")
        command_id = uuid.uuid4().hex
        payload = json.dumps({"id": command_id, "capability": capability.value, "value": value}, separators=(",", ":"))
        ack_topic = self._topic(native_id, "ack")
        async with self._client() as client:
            await client.subscribe(ack_topic)
            await client.publish(self._topic(native_id, "set"), payload=payload, qos=1, retain=False)
            async with asyncio.timeout(self.command_timeout):
                async for message in client.messages:
                    if str(message.topic) != ack_topic:
                        continue
                    try:
                        ack = json.loads(bytes(message.payload).decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if not isinstance(ack, dict) or ack.get("id") != command_id:
                        continue
                    if ack.get("ok") is not True:
                        raise RuntimeError(str(ack.get("error") or "device rejected command"))
                    state = ack.get("state", {})
                    if not isinstance(state, dict):
                        state = {}
                    normalized = self._normalize_state(json.dumps(state).encode(), config["capabilities"])
                    normalized.setdefault(capability.value, value)
                    return normalized
        raise TimeoutError("MQTT command acknowledgement timed out")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            raw = (await self._one(self._topic(native_id, "availability"), 1.5)).decode("utf-8", errors="replace").strip().lower()
            online = raw == "online"
            detail = "online" if online else f"reported {raw or 'offline'}"
        except Exception as exc:
            online = False
            detail = f"{type(exc).__name__}: {exc}"
        return DeviceHealth(online=online, detail=detail, latency_ms=round((time.perf_counter() - started) * 1000, 2), transport="mqtt")
