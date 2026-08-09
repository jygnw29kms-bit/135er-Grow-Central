"""Configuration-backed device registry."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .models import DeviceConfig


class DeviceRegistry:
    def __init__(self, devices: list[DeviceConfig]):
        self._devices = {device.id: device for device in devices}
        if len(self._devices) != len(devices):
            raise ValueError("duplicate smart-home device id")

    @classmethod
    def from_env(cls) -> "DeviceRegistry":
        path = Path(os.getenv("GC_SMARTHOME_DEVICE_CONFIG", "/etc/135er-growcontrol/devices.json"))
        if not path.exists():
            return cls([])
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw.get("devices", raw) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            raise ValueError("device config must contain a device list")
        return cls([DeviceConfig.model_validate(row) for row in rows])

    def list(self) -> list[DeviceConfig]:
        return sorted(self._devices.values(), key=lambda item: item.id)

    def get(self, device_id: str) -> DeviceConfig:
        try:
            return self._devices[device_id]
        except KeyError as exc:
            raise KeyError(f"unknown device: {device_id}") from exc
