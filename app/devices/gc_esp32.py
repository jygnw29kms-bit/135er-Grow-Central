from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any, Mapping

import aiomqtt

from .catalog import provider_by_id
from .gc_esp32_protocol import (
    DEFAULT_ROOT,
    Esp32Announcement,
    device_topic,
    encode_command,
    normalize_state,
    parse_announcement,
    validate_ack,
    wildcard_topic,
)
from .models import Capability
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


class GrowCentralEsp32Provider(DeviceProvider):
    def __init__(self) -> None:
        descriptor = provider_by_id("growcentral_esp32")
        if descriptor is None:
            raise RuntimeError("growcentral_esp32 provider missing from catalog")
        self.descriptor = descriptor
        self.host = os.getenv("GC_MQTT_HOST", "127.0.0.1")
        self.port = int(os.getenv("GC_MQTT_PORT", "1883"))
        self.username = os.getenv("GC_MQTT_USERNAME") or None
        self.password = os.getenv("GC_MQTT_PASSWORD") or None
        self.root = os.getenv("GC_MQTT_PREFIX", DEFAULT_ROOT).strip("/")
        self.command_timeout = max(0.5, min(float(os.getenv("GC_MQTT_COMMAND_TIMEOUT", "5")), 30.0))

    def _client(self) -> aiomqtt.Client:
        return aiomqtt.Client(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    async def _one(self, topic: str, timeout: float) -> bytes:
        async with self._client() as client:
            await client.subscribe(topic)
            async with asyncio.timeout(timeout):
                async for message in client.messages:
                    if str(message.topic) == topic:
                        return bytes(message.payload)
        raise TimeoutError(f"no retained MQTT message for {topic}")

    async def _announcement(self, native_id: str, timeout: float = 2.0) -> Esp32Announcement:
        payload = await self._one(device_topic(self.root, native_id, "announce"), timeout)
        announce = parse_announcement(payload)
        if announce.id != native_id:
            raise ValueError("announcement id does not match MQTT topic")
        return announce

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        timeout = max(0.1, min(timeout, 15.0))
        topic = wildcard_topic(self.root, "announce")
        found: dict[str, DiscoveredDevice] = {}
        async with self._client() as client:
            await client.subscribe(topic)
            try:
                async with asyncio.timeout(timeout):
                    async for message in client.messages:
                        try:
                            announce = parse_announcement(bytes(message.payload))
                        except (ValueError, UnicodeDecodeError):
                            continue
                        found[announce.id] = DiscoveredDevice(
                            provider_id=self.descriptor.id,
                            native_id=announce.id,
                            name=announce.name,
                            device_class=announce.device_class,
                            capabilities=announce.capabilities,
                            transport="mqtt",
                            model=announce.model,
                            manufacturer=self.descriptor.manufacturer,
                            metadata={
                                "protocol": "gc-esp32-mqtt-v1",
                                "firmware": announce.firmware,
                                "topic_root": self.root,
                            },
                        )
            except TimeoutError:
                pass
        return sorted(found.values(), key=lambda item: (item.name.lower(), item.native_id))

    async def state(self, native_id: str) -> Mapping[str, Any]:
        announce = await self._announcement(native_id)
        payload = await self._one(device_topic(self.root, native_id, "state"), 2.0)
        state = normalize_state(payload, announce.capabilities)
        state["online"] = True
        return state

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        announce = await self._announcement(native_id)
        if capability not in announce.capabilities:
            raise ValueError(f"device does not declare capability: {capability.value}")

        command_id = uuid.uuid4().hex
        set_topic = device_topic(self.root, native_id, "set")
        ack_topic = device_topic(self.root, native_id, "ack")
        payload = encode_command(command_id, capability, value)

        async with self._client() as client:
            # Subscribe before publishing so a fast ESP32 ACK cannot race us.
            await client.subscribe(ack_topic)
            await client.publish(set_topic, payload=payload, qos=1, retain=False)
            async with asyncio.timeout(self.command_timeout):
                async for message in client.messages:
                    if str(message.topic) != ack_topic:
                        continue
                    try:
                        ack_state = validate_ack(bytes(message.payload), command_id)
                    except ValueError:
                        # ACK for an older/different command; keep waiting.
                        continue
                    normalized = normalize_state(json.dumps(dict(ack_state)), announce.capabilities)
                    normalized.setdefault(capability.value, value)
                    normalized["online"] = True
                    return normalized
        raise TimeoutError("device command acknowledgement timed out")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            availability = await self._one(device_topic(self.root, native_id, "availability"), 1.5)
            online = availability.decode("utf-8", errors="replace").strip().lower() == "online"
            detail = "online" if online else "device reported offline"
        except Exception as exc:
            online = False
            detail = f"{type(exc).__name__}: {exc}"
        return DeviceHealth(
            online=online,
            detail=detail,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            transport="mqtt",
        )
