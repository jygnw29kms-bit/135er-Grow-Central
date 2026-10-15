from __future__ import annotations

import asyncio
import json
import math
import os
import secrets
import ssl
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
from .gc_identity import verify_message
from .gc_trust import TrustStore
from .gc_calibration import CalibrationStore
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


class GrowCentralEsp32Provider(DeviceProvider):
    def __init__(self) -> None:
        descriptor = provider_by_id("growcentral_esp32")
        if descriptor is None:
            raise RuntimeError("growcentral_esp32 provider missing from catalog")
        self.descriptor = descriptor
        self.host = os.getenv("GC_MQTT_HOST", "127.0.0.1")
        self.tls = os.getenv("GC_MQTT_TLS", "false").lower() == "true"
        self.port = int(os.getenv("GC_MQTT_PORT", "8883" if self.tls else "1883"))
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
            timeout=self.command_timeout,
            max_queued_incoming_messages=64,
            tls_context=ssl.create_default_context(cafile=os.getenv("GC_MQTT_CA_FILE") or None) if self.tls else None,
        )

    async def _one(self, topic: str, timeout: float) -> bytes:
        async with self._client() as client:
            await client.subscribe(topic)
            async with asyncio.timeout(timeout):
                async for message in client.messages:
                    if str(message.topic) == topic:
                        return bytes(message.payload)
        raise TimeoutError(f"no retained MQTT message for {topic}")

    def _decode_announcement(self, payload):
        if len(payload) > 8192:
            raise ValueError("sensor announcement too large")
        envelope = json.loads(payload)
        signed = verify_message(payload, kind="announce") if isinstance(envelope, dict) and "algorithm" in envelope else None
        announce = parse_announcement(json.dumps(signed.body) if signed else payload)
        return announce, signed

    async def prove_identity(self, native_id: str):
        record = TrustStore().get(native_id)
        if not record or not record["identity_verified"]:
            raise PermissionError("sensor needs signed identity firmware")
        nonce = secrets.token_hex(32)
        proof_topic = device_topic(self.root, native_id, "proof")
        async with self._client() as client:
            await client.subscribe(proof_topic)
            await client.publish(device_topic(self.root, native_id, "challenge"),
                                 payload=json.dumps({"nonce": nonce}), qos=1, retain=False)
            async with asyncio.timeout(self.command_timeout):
                async for message in client.messages:
                    if str(message.topic) != proof_topic:
                        continue
                    try:
                        proof = verify_message(bytes(message.payload), kind="proof", device_id=native_id)
                    except ValueError:
                        continue
                    if proof.public_key == record["public_key"] and proof.body.get("nonce") == nonce:
                        return proof
        raise TimeoutError("live sensor identity proof timed out")

    async def _announcement(self, native_id: str, timeout: float = 2.0) -> Esp32Announcement:
        payload = await self._one(device_topic(self.root, native_id, "announce"), timeout)
        announce, signed = self._decode_announcement(payload)
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
                            announce, signed = self._decode_announcement(bytes(message.payload))
                            if str(message.topic) != device_topic(self.root, announce.id, "announce"):
                                continue
                            trust = TrustStore().discover(announce, signed)
                            if trust["status"] in {"REJECTED", "REVOKED"}:
                                continue
                        except (ValueError, UnicodeDecodeError, PermissionError):
                            continue
                        found[announce.id] = DiscoveredDevice(
                            provider_id=self.descriptor.id,
                            native_id=announce.id,
                            name=trust["name"] or announce.name,
                            device_class=announce.device_class,
                            capabilities=announce.capabilities,
                            transport="mqtt",
                            model=announce.model,
                            manufacturer=self.descriptor.manufacturer,
                            metadata={
                                "protocol": "gc-esp32-mqtt-v1",
                                "firmware": announce.firmware,
                                "trust_status": trust["status"],
                                "identity_verified": trust["identity_verified"],
                                "fingerprint": trust["fingerprint"],
                                "topic_root": self.root,
                            },
                        )
            except TimeoutError:
                pass
        return sorted(found.values(), key=lambda item: (item.name.lower(), item.native_id))

    async def state(self, native_id: str) -> Mapping[str, Any]:
        trusted = TrustStore().require_trusted(native_id)
        proof = await self.prove_identity(native_id)
        TrustStore().receive(proof)
        allowed = tuple(Capability(value) for value in trusted["metadata"]["capabilities"])
        state = normalize_state(json.dumps(proof.body.get("state", {})), allowed)
        moisture = state.get("soil_moisture")
        if moisture is not None and (type(moisture) not in (int, float) or not math.isfinite(moisture) or not 0 <= moisture <= 100):
            raise ValueError("invalid soil moisture engineering percentage")
        diagnostics = proof.body.get("state", {}).get("meta", {})
        if isinstance(diagnostics, dict):
            fields = {"raw", "median", "filtered_raw", "min", "max", "sigma", "quality", "moisture_state", "sensor_ok", "air_raw", "water_raw", "rssi_dbm", "uptime_ms", "firmware"}
            state["meta"] = {k: v for k, v in diagnostics.items() if k in fields and isinstance(v, (str, int, float, bool)) and (not isinstance(v, float) or math.isfinite(v))}
        firmware = state.get('meta', {}).get('firmware') if isinstance(state.get('meta'), dict) else None
        try:
            calibration = CalibrationStore().require_valid(native_id, fingerprint=trusted.get('fingerprint'), public_key=proof.public_key, hardware_uid=proof.body.get('hardware_uid'), firmware_version=firmware)
            if not (proof.body.get('calibration') or {}).get('ready'):
                CalibrationStore().invalidate(native_id, 'sensor reports calibration incomplete')
                raise PermissionError('sensor calibration incomplete')
            state.setdefault('meta', {})['calibration_status'] = 'valid'
            state['meta']['calibrated_at'] = calibration['calibrated_at']
        except PermissionError:
            if 'soil_moisture' in state:
                state['soil_moisture'] = None
            state.setdefault('meta', {})['calibration_status'] = 'required'
        state["online"] = True
        return state

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        TrustStore().require_trusted(native_id)
        raise PermissionError("native sensor pairing grants read-only access; actuator writes need a separate validated policy")

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            TrustStore().require_trusted(native_id)
            proof = await self.prove_identity(native_id)
            TrustStore().receive(proof)
            online = True
            detail = "live cryptographic identity verified"
        except Exception as exc:
            online = False
            detail = f"{type(exc).__name__}: {exc}"
        return DeviceHealth(
            online=online,
            detail=detail,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            transport="mqtt",
        )
