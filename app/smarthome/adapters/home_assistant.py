"""Restricted Home Assistant REST bridge.

The connector intentionally supports a narrow switch command surface only; it is
not an arbitrary Home Assistant service proxy.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Any

import httpx

from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter


class HomeAssistantSwitchAdapter(SwitchAdapter):
    def __init__(self, device: DeviceConfig):
        self.device = device
        self.url = os.getenv("GC_HA_URL", "").rstrip("/")
        self.token = os.getenv("GC_HA_TOKEN", "")
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
            raise AdapterError("GC_HA_URL must be a plain http(s) origin")
        if not self.token:
            raise AdapterError("GC_HA_TOKEN is not configured")
        if not device.native_id.startswith("switch."):
            raise AdapterError("Home Assistant smart-plug entities must use the switch domain")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def read_state(self) -> dict[str, Any]:
        endpoint = f"{self.url}/api/states/{self.device.native_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._headers()) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError("Home Assistant state request failed") from exc
        attrs = data.get("attributes", {}) if isinstance(data.get("attributes"), dict) else {}
        return {
            "on": data.get("state") == "on",
            "online": data.get("state") not in {"unavailable", "unknown", None},
            "power_w": _first_number(attrs, "power", "current_power_w", "active_power"),
            "voltage_v": _first_number(attrs, "voltage", "voltage_v"),
            "current_a": _first_number(attrs, "current", "current_a"),
            "frequency_hz": _first_number(attrs, "frequency", "frequency_hz"),
            "energy_wh": _energy_wh(attrs),
            "temperature_c": _first_number(attrs, "temperature", "temperature_c"),
            "source": "home_assistant",
            "native": {"state": data.get("state"), "attributes": attrs},
        }

    async def set_switch(self, on: bool) -> dict[str, Any]:
        if os.getenv("GC_HA_READ_ONLY", "true").lower() == "true":
            raise AdapterError("Home Assistant connector is read-only")
        service = "turn_on" if on else "turn_off"
        endpoint = f"{self.url}/api/services/switch/{service}"
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._headers()) as client:
                response = await client.post(endpoint, json={"entity_id": self.device.native_id})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AdapterError("Home Assistant switch command failed") from exc
        return await self.read_state()


def _first_number(attrs: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = attrs.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _energy_wh(attrs: dict[str, Any]) -> float | None:
    value = _first_number(attrs, "energy_wh", "total_consumption_wh")
    if value is not None:
        return value
    value = _first_number(attrs, "energy", "total_consumption")
    unit = str(attrs.get("unit_of_measurement", "")).lower()
    if value is not None and unit == "kwh":
        return value * 1000.0
    return value
