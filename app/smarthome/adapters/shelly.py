"""Native local Shelly Gen2+ JSON-RPC switch adapter."""
from __future__ import annotations

import ipaddress
import os
from typing import Any

import httpx

from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter


class ShellySwitchAdapter(SwitchAdapter):
    def __init__(self, device: DeviceConfig):
        if not device.host:
            raise AdapterError("Shelly device requires a host")
        try:
            ip = ipaddress.ip_address(device.host)
        except ValueError as exc:
            raise AdapterError("Shelly host must be a literal LAN IP address") from exc
        if ip.version != 4 or not (ip.is_private or ip.is_link_local) or ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
            raise AdapterError("Shelly host must be a usable private/link-local IPv4 address")
        self.device = device
        self.base_url = f"http://{ip}/rpc"

    def _auth(self) -> httpx.DigestAuth | None:
        if not self.device.username_env and not self.device.password_env:
            return None
        if not self.device.username_env or not self.device.password_env:
            raise AdapterError("both Shelly credential environment names are required")
        username = os.getenv(self.device.username_env, "")
        password = os.getenv(self.device.password_env, "")
        if not username or not password:
            raise AdapterError("Shelly credentials are not configured")
        return httpx.DigestAuth(username, password)

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {"id": 1, "method": method, "params": params}
        try:
            async with httpx.AsyncClient(timeout=5.0, auth=self._auth()) as client:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AdapterError("Shelly RPC request failed") from exc
        if "error" in data:
            raise AdapterError(f"Shelly RPC error code {data['error'].get('code', 'unknown')}")
        return data.get("result", {})

    async def read_state(self) -> dict[str, Any]:
        result = await self._rpc("Switch.GetStatus", {"id": self.device.channel})
        energy_wh = None
        aenergy = result.get("aenergy")
        if isinstance(aenergy, dict):
            total = aenergy.get("total")
            if isinstance(total, (int, float)):
                energy_wh = float(total)
        temperature_c = None
        temperature = result.get("temperature")
        if isinstance(temperature, dict):
            value = temperature.get("tC")
            if isinstance(value, (int, float)):
                temperature_c = float(value)
        return {
            "on": bool(result.get("output", False)),
            "online": True,
            "power_w": _number(result.get("apower")),
            "voltage_v": _number(result.get("voltage")),
            "current_a": _number(result.get("current")),
            "frequency_hz": _number(result.get("freq")),
            "energy_wh": energy_wh,
            "temperature_c": temperature_c,
            "source": "shelly",
            "native": result,
        }

    async def set_switch(self, on: bool) -> dict[str, Any]:
        await self._rpc("Switch.Set", {"id": self.device.channel, "on": bool(on)})
        return await self.read_state()


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
