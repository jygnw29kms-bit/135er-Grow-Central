from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

import tinytuya

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


class TuyaLocalProvider(DeviceProvider):
    """Local Tuya provider with explicit per-device DP mappings.

    Grow Central never guesses DP semantics. Each configured device maps known
    gc-device capabilities to Tuya DP numbers and may mark only selected DPs as
    writable. Local keys remain outside the repository in a root-readable file.
    """

    def __init__(self) -> None:
        descriptor = provider_by_id("tuya")
        if descriptor is None:
            raise RuntimeError("tuya provider missing from catalog")
        self.descriptor = descriptor
        self.config_path = Path(os.getenv("GC_TUYA_DEVICE_CONFIG", "/etc/grow-central/tuya-devices.json"))

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
            if not native_id:
                continue
            result[native_id] = row
        return result

    @staticmethod
    def _cap_map(row: Mapping[str, Any]) -> dict[Capability, dict[str, Any]]:
        raw = row.get("dps", {})
        if not isinstance(raw, dict):
            return {}
        result: dict[Capability, dict[str, Any]] = {}
        for name, spec in raw.items():
            try:
                capability = Capability(str(name))
            except ValueError:
                continue
            if isinstance(spec, int) or (isinstance(spec, str) and spec.isdigit()):
                result[capability] = {"dp": str(spec), "scale": 1.0, "writable": False}
                continue
            if not isinstance(spec, dict):
                continue
            dp = str(spec.get("dp", "")).strip()
            if not dp.isdigit():
                continue
            try:
                scale = float(spec.get("scale", 1.0))
            except (TypeError, ValueError):
                scale = 1.0
            if scale == 0:
                scale = 1.0
            result[capability] = {
                "dp": dp,
                "scale": scale,
                "writable": bool(spec.get("writable", False)),
                "invert": bool(spec.get("invert", False)),
            }
        return result

    @staticmethod
    def _decode(value: Any, spec: Mapping[str, Any]) -> Any:
        if spec.get("invert") and isinstance(value, bool):
            value = not value
        scale = float(spec.get("scale", 1.0))
        if scale != 1.0 and isinstance(value, (int, float)) and not isinstance(value, bool):
            return value / scale
        return value

    @staticmethod
    def _encode(value: Any, spec: Mapping[str, Any]) -> Any:
        if spec.get("invert") and isinstance(value, bool):
            value = not value
        scale = float(spec.get("scale", 1.0))
        if scale != 1.0 and isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(round(value * scale))
        return value

    @staticmethod
    def _device(row: Mapping[str, Any]) -> tinytuya.Device:
        device_id = str(row.get("device_id", "")).strip()
        ip = str(row.get("ip", "")).strip() or None
        local_key = str(row.get("local_key", "")).strip()
        if not device_id or not local_key:
            raise ValueError("Tuya device requires device_id and local_key")
        device = tinytuya.Device(device_id, ip, local_key)
        device.set_version(float(row.get("version", 3.3)))
        device.set_socketTimeout(float(row.get("timeout", 3.0)))
        return device

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        del timeout
        found: list[DiscoveredDevice] = []
        for native_id, row in self._load().items():
            try:
                device_class = DeviceClass(str(row.get("device_class", "switch")))
            except ValueError:
                device_class = DeviceClass.SWITCH
            caps = tuple(self._cap_map(row))
            if not caps:
                continue
            found.append(DiscoveredDevice(
                provider_id=self.descriptor.id,
                native_id=native_id,
                name=str(row.get("name") or native_id),
                device_class=device_class,
                capabilities=caps,
                transport="wifi_local",
                model=str(row.get("model") or "") or None,
                manufacturer=str(row.get("manufacturer") or "Tuya"),
                metadata={"protocol": f"tuya-{row.get('version', 3.3)}", "configured": True},
            ))
        return sorted(found, key=lambda item: (item.name.lower(), item.native_id))

    async def _status_raw(self, row: Mapping[str, Any]) -> dict[str, Any]:
        response = await asyncio.to_thread(self._device(row).status)
        if not isinstance(response, dict):
            raise RuntimeError("invalid Tuya status response")
        if "Error" in response or response.get("error"):
            raise RuntimeError(str(response.get("Error") or response.get("error")))
        dps = response.get("dps", {})
        if not isinstance(dps, dict):
            raise RuntimeError("Tuya status missing dps")
        return {str(key): value for key, value in dps.items()}

    async def state(self, native_id: str) -> Mapping[str, Any]:
        row = self._load().get(native_id)
        if row is None:
            raise KeyError(native_id)
        dps = await self._status_raw(row)
        state: dict[str, Any] = {"online": True}
        for capability, spec in self._cap_map(row).items():
            if spec["dp"] in dps:
                state[capability.value] = self._decode(dps[spec["dp"]], spec)
        return state

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        row = self._load().get(native_id)
        if row is None:
            raise KeyError(native_id)
        spec = self._cap_map(row).get(capability)
        if spec is None:
            raise ValueError(f"Tuya capability not mapped: {capability.value}")
        if not spec.get("writable"):
            raise PermissionError(f"Tuya capability is read-only: {capability.value}")
        encoded = self._encode(value, spec)
        device = self._device(row)
        response = await asyncio.to_thread(device.set_value, int(spec["dp"]), encoded)
        if isinstance(response, dict) and ("Error" in response or response.get("error")):
            raise RuntimeError(str(response.get("Error") or response.get("error")))
        # A write is successful only after a fresh status read confirms the value.
        state = dict(await self.state(native_id))
        actual = state.get(capability.value)
        if actual != value:
            if isinstance(actual, (int, float)) and isinstance(value, (int, float)) and abs(float(actual) - float(value)) <= 0.01:
                return state
            raise RuntimeError(f"Tuya write not confirmed for {capability.value}")
        return state

    async def health(self, native_id: str) -> DeviceHealth:
        row = self._load().get(native_id)
        if row is None:
            return DeviceHealth(False, "device not configured", transport="wifi_local")
        started = time.perf_counter()
        try:
            await self._status_raw(row)
            return DeviceHealth(True, "online", round((time.perf_counter() - started) * 1000, 2), "wifi_local")
        except Exception as exc:
            return DeviceHealth(False, f"{type(exc).__name__}: {exc}", round((time.perf_counter() - started) * 1000, 2), "wifi_local")
