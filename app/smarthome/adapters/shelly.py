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
        if not (ip.is_private or ip.is_link_local):
            raise AdapterError("Shelly host must be a private/link-local IP address")
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
        return {"on": bool(result.get("output", False)), "native": result}

    async def set_switch(self, on: bool) -> dict[str, Any]:
        await self._rpc("Switch.Set", {"id": self.device.channel, "on": bool(on)})
        return await self.read_state()
