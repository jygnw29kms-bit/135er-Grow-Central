"""TP-Link Tapo/Kasa smart-plug adapter.

Uses python-kasa for authenticated local control. Account credentials stay
server-side. WAN/cloud capability is modeled separately; this adapter never
pretends a local device path is cloud-backed.
"""
from __future__ import annotations

import os
from typing import Any

from kasa import Credentials, Device

from app.credential_store import get_credentials
from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter


class TapoSwitchAdapter(SwitchAdapter):
    def __init__(self, device: DeviceConfig):
        if not device.host:
            raise AdapterError("Tapo host missing")
        username = os.getenv(device.username_env or "GC_TAPO_USERNAME", "").strip()
        password = os.getenv(device.password_env or "GC_TAPO_PASSWORD", "")
        if not username or not password:
            stored = get_credentials("tapo")
            if stored:
                username, password = stored
        if not username or not password:
            raise AdapterError("Tapo credentials are not configured")
        self.device = device
        self.host = device.host
        self.credentials = Credentials(username, password)

    async def _device(self):
        try:
            dev = await Device.connect(host=self.host, credentials=self.credentials)
            await dev.update()
            return dev
        except Exception as exc:
            raise AdapterError(f"Tapo local connection failed ({type(exc).__name__})") from exc

    @staticmethod
    def _energy_value(dev: Any, key: str) -> float | None:
        energy = getattr(dev, "energy", None)
        value = getattr(energy, key, None) if energy is not None else None
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def read_state(self) -> dict[str, Any]:
        dev = await self._device()
        try:
            on = bool(getattr(dev, "is_on"))
        except Exception:
            on = None
        power_w = self._energy_value(dev, "current_consumption")
        total_kwh = self._energy_value(dev, "today_energy")
        if total_kwh is None:
            total_kwh = self._energy_value(dev, "month_energy")
        return {
            "online": True,
            "on": on,
            "power_w": power_w,
            "energy_wh": total_kwh * 1000.0 if total_kwh is not None else None,
            "voltage_v": None,
            "current_a": None,
            "frequency_hz": None,
            "native_name": str(getattr(dev, "alias", None) or getattr(dev, "model", None) or self.device.name),
            "model": str(getattr(dev, "model", "")),
            "transport": "local",
            "wan_capable": True,
        }

    async def set_switch(self, on: bool) -> dict[str, Any]:
        dev = await self._device()
        try:
            if on:
                await dev.turn_on()
            else:
                await dev.turn_off()
            await dev.update()
        except Exception as exc:
            raise AdapterError(f"Tapo local switch failed ({type(exc).__name__})") from exc
        return await self.read_state()
