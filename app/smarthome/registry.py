"""Configuration-backed device registry."""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
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
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f".{path.name}.lock")
        lock_descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            os.fchmod(lock_descriptor, 0o600)
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            # Reload under the lock so concurrent discovery/import requests do
            # not overwrite devices registered by the other request.
            current = DeviceRegistry.from_env()._devices
            for identifier, existing in self._devices.items():
                current.setdefault(identifier, existing)
            current[device.id] = device
            self._devices = current
            payload = {"devices": [item.model_dump(mode="json") for item in self.list()]}
            descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
                os.chmod(path, 0o600)
                directory_descriptor = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
            finally:
                Path(temporary).unlink(missing_ok=True)
        finally:
            fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
            os.close(lock_descriptor)
