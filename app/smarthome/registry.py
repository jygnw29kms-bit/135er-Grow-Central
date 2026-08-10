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
    def config_path(cls) -> Path:
        return Path(os.getenv("GC_SMARTHOME_DEVICE_CONFIG", "/var/lib/135er-grow-central/devices.json"))

    @classmethod
    def from_env(cls) -> "DeviceRegistry":
        path = cls.config_path()
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

    def upsert(self, device: DeviceConfig) -> None:
        self._devices[device.id] = device
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = {"devices": [item.model_dump(mode="json") for item in self.list()]}
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)
