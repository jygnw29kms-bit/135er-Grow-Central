from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .models import Capability, DeviceClass

PROTOCOL = "gc-esp32-mqtt-v1"
SCHEMA = "gc-device-v1"
DEFAULT_ROOT = "growcentral/v1"
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


@dataclass(frozen=True, slots=True)
class Esp32Announcement:
    id: str
    name: str
    device_class: DeviceClass
    capabilities: tuple[Capability, ...]
    model: str | None = None
    firmware: str | None = None


def device_topic(root: str, device_id: str, leaf: str) -> str:
    if not _ID.fullmatch(device_id):
        raise ValueError("invalid Grow Central device id")
    if leaf not in {"announce", "state", "set", "ack", "availability"}:
        raise ValueError("invalid Grow Central MQTT leaf")
    clean_root = root.strip("/")
    if not clean_root:
        raise ValueError("MQTT topic root must not be empty")
    return f"{clean_root}/devices/{device_id}/{leaf}"


def wildcard_topic(root: str, leaf: str) -> str:
    clean_root = root.strip("/")
    if leaf not in {"announce", "state", "availability"}:
        raise ValueError("invalid discovery leaf")
    return f"{clean_root}/devices/+/{leaf}"


def decode_json(payload: bytes | bytearray | str) -> dict[str, Any]:
    raw = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("MQTT payload must be a JSON object")
    return data


def parse_announcement(payload: bytes | bytearray | str) -> Esp32Announcement:
    data = decode_json(payload)
    if data.get("schema") != SCHEMA or data.get("protocol") != PROTOCOL:
        raise ValueError("unsupported Grow Central ESP32 schema/protocol")
    device_id = str(data.get("id") or "")
    if not _ID.fullmatch(device_id):
        raise ValueError("invalid Grow Central device id")
    name = str(data.get("name") or "").strip()
    if not name or len(name) > 120:
        raise ValueError("invalid Grow Central device name")
    try:
        device_class = DeviceClass(str(data["device_class"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("invalid device class") from exc
    raw_caps = data.get("capabilities")
    if not isinstance(raw_caps, list) or not raw_caps:
        raise ValueError("device must declare capabilities")
    try:
        capabilities = tuple(dict.fromkeys(Capability(str(item)) for item in raw_caps))
    except ValueError as exc:
        raise ValueError("unknown capability in announcement") from exc
    return Esp32Announcement(
        id=device_id,
        name=name,
        device_class=device_class,
        capabilities=capabilities,
        model=str(data.get("model") or "") or None,
        firmware=str(data.get("firmware") or "") or None,
    )


def normalize_state(payload: bytes | bytearray | str, allowed: tuple[Capability, ...] | None = None) -> dict[str, Any]:
    data = decode_json(payload)
    allowed_names = {item.value for item in allowed} if allowed is not None else {item.value for item in Capability}
    state: dict[str, Any] = {}
    for key, value in data.items():
        if key in {"ts", "meta"}:
            continue
        if key not in allowed_names:
            raise ValueError(f"state contains undeclared/unknown capability: {key}")
        state[key] = value
    return state


def encode_command(command_id: str, capability: Capability, value: Any) -> str:
    if not command_id or len(command_id) > 128:
        raise ValueError("invalid command id")
    return json.dumps(
        {"command_id": command_id, "capability": capability.value, "value": value},
        separators=(",", ":"),
        ensure_ascii=False,
    )


def validate_ack(payload: bytes | bytearray | str, command_id: str) -> Mapping[str, Any]:
    data = decode_json(payload)
    if data.get("command_id") != command_id:
        raise ValueError("ACK command id mismatch")
    if data.get("ok") is not True:
        raise RuntimeError(str(data.get("error") or "device rejected command"))
    state = data.get("state") or {}
    if not isinstance(state, dict):
        raise ValueError("ACK state must be an object")
    return state
