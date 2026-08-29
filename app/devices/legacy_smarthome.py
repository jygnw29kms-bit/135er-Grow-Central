from __future__ import annotations

import time
from typing import Any, Mapping

from app.smarthome.adapters.base import AdapterError
from app.smarthome.adapters.factory import build_switch_adapter
from app.smarthome.models import DeviceConfig
from app.smarthome.registry import DeviceRegistry

from .catalog import provider_by_id
from .models import Capability, DeviceClass
from .provider import DeviceHealth, DeviceProvider, DiscoveredDevice


class LegacySmartHomeProvider(DeviceProvider):
    """Expose a proven smart-home adapter through gc-device-v1.

    This is intentionally a compatibility bridge, not a second implementation
    of Shelly/Tapo/FRITZ!/Home Assistant protocols. Vendor payloads are
    normalized here and the established adapter remains the transport owner.
    """

    def __init__(self, provider_id: str):
        descriptor = provider_by_id(provider_id)
        if descriptor is None:
            raise ValueError(f"unknown provider: {provider_id}")
        self.descriptor = descriptor
        self.provider_id = provider_id

    def _devices(self) -> list[DeviceConfig]:
        return [row for row in DeviceRegistry.from_env().list() if row.adapter == self.provider_id]

    def _device(self, native_id: str) -> DeviceConfig:
        device = next((row for row in self._devices() if row.id == native_id), None)
        if device is None:
            raise KeyError(f"unknown {self.provider_id} device: {native_id}")
        return device

    @staticmethod
    def _capabilities(device: DeviceConfig) -> tuple[Capability, ...]:
        caps: list[Capability] = [Capability.POWER]
        declared = set(device.metadata.get("capabilities") or [])
        mapping = {
            "power_w": Capability.POWER_METER,
            "energy_wh": Capability.ENERGY,
            "voltage": Capability.VOLTAGE,
            "current": Capability.CURRENT,
            "temperature": Capability.TEMPERATURE,
            "humidity": Capability.HUMIDITY,
        }
        for key, capability in mapping.items():
            if key in declared or capability.value in declared:
                caps.append(capability)
        return tuple(dict.fromkeys(caps))

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        del timeout
        rows: list[DiscoveredDevice] = []
        for device in self._devices():
            rows.append(
                DiscoveredDevice(
                    provider_id=self.provider_id,
                    native_id=device.id,
                    name=device.name,
                    device_class=DeviceClass.SWITCH,
                    capabilities=self._capabilities(device),
                    transport=self.descriptor.transports[0].value,
                    model=str(device.metadata.get("product") or "") or None,
                    manufacturer=self.descriptor.manufacturer,
                    metadata={
                        "configured": True,
                        "approved": device.approved,
                        "writable": device.writable,
                        "adapter": device.adapter,
                        "source_native_id": device.native_id,
                        **device.metadata,
                    },
                )
            )
        return rows

    @staticmethod
    def normalize_state(raw: Mapping[str, Any]) -> dict[str, Any]:
        state: dict[str, Any] = {"online": bool(raw.get("online", True))}
        if "on" in raw:
            state[Capability.POWER.value] = bool(raw["on"])
        aliases = {
            "power_w": Capability.POWER_METER.value,
            "energy_wh": Capability.ENERGY.value,
            "voltage": Capability.VOLTAGE.value,
            "current": Capability.CURRENT.value,
            "temperature": Capability.TEMPERATURE.value,
            "humidity": Capability.HUMIDITY.value,
        }
        for source, target in aliases.items():
            if raw.get(source) is not None:
                state[target] = raw[source]
        return state

    async def state(self, native_id: str) -> Mapping[str, Any]:
        device = self._device(native_id)
        if not device.approved:
            raise PermissionError("device is not approved")
        raw = await build_switch_adapter(device).read_state()
        return self.normalize_state(raw)

    async def command(self, native_id: str, capability: Capability, value: Any) -> Mapping[str, Any]:
        device = self._device(native_id)
        if not device.approved:
            raise PermissionError("device is not approved")
        if not device.writable:
            raise PermissionError("device is read-only")
        if capability is not Capability.POWER:
            raise ValueError(f"unsupported capability for compatibility provider: {capability.value}")
        raw = await build_switch_adapter(device).set_switch(bool(value))
        state = self.normalize_state(raw)
        # A transport may return a partial ACK. Preserve the requested value so
        # callers get deterministic command semantics; health/state can verify.
        state.setdefault(Capability.POWER.value, bool(value))
        return state

    async def health(self, native_id: str) -> DeviceHealth:
        started = time.perf_counter()
        try:
            state = await self.state(native_id)
        except (AdapterError, OSError, PermissionError, ValueError) as exc:
            return DeviceHealth(
                online=False,
                detail=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                transport=self.descriptor.transports[0].value,
            )
        return DeviceHealth(
            online=bool(state.get("online", True)),
            detail="ok",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            transport=self.descriptor.transports[0].value,
        )
