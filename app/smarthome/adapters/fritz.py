"""Native FRITZ!Box AHA smart-home adapter.

Uses AVM's local HTTP smart-home interface. Credentials stay server-side and
are never returned to the browser.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx
from defusedxml import ElementTree as ET

from app.credential_store import get_credentials
from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter


class FritzAhaClient:
    def __init__(self, host: str, username: str, password: str, timeout: float = 6.0):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base = f"http://{host}"
        self.sid: str | None = None

    async def _get_login(self, client: httpx.AsyncClient) -> ET.Element:
        response = await client.get(f"{self.base}/login_sid.lua", params={"version": "2"})
        response.raise_for_status()
        return ET.fromstring(response.text)

    @staticmethod
    def _response(challenge: str, password: str) -> str:
        if challenge.startswith("2$"):
            parts = challenge.split("$")
            if len(parts) != 5:
                raise AdapterError("unsupported FRITZ!Box login challenge")
            _, iter1, salt1, iter2, salt2 = parts
            hash1 = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt1), int(iter1))
            hash2 = hashlib.pbkdf2_hmac("sha256", hash1, bytes.fromhex(salt2), int(iter2))
            return f"{challenge}${hash2.hex()}"
        legacy = f"{challenge}-{password}".encode("utf-16le")
        return f"{challenge}-{hashlib.md5(legacy).hexdigest()}"  # nosec B324 - legacy FRITZ!OS protocol

    async def login(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            root = await self._get_login(client)
            sid = (root.findtext("SID") or "").strip()
            if sid and sid != "0000000000000000":
                self.sid = sid
                return sid
            challenge = (root.findtext("Challenge") or "").strip()
            if not challenge:
                raise AdapterError("FRITZ!Box login challenge missing")
            response_value = self._response(challenge, self.password)
            response = await client.post(f"{self.base}/login_sid.lua", data={"username": self.username, "response": response_value})
            response.raise_for_status()
            logged = ET.fromstring(response.text)
            sid = (logged.findtext("SID") or "").strip()
            if not sid or sid == "0000000000000000":
                raise AdapterError("FRITZ!Box authentication failed")
            self.sid = sid
            return sid

    async def command(self, switchcmd: str, ain: str | None = None) -> str:
        sid = self.sid or await self.login()
        params: dict[str, str] = {"sid": sid, "switchcmd": switchcmd}
        if ain:
            params["ain"] = ain
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base}/webservices/homeautoswitch.lua", params=params)
            if response.status_code in {401, 403}:
                self.sid = None
                params["sid"] = await self.login()
                response = await client.get(f"{self.base}/webservices/homeautoswitch.lua", params=params)
            response.raise_for_status()
            text = response.text.strip()
            if text.lower().startswith("inval"):
                raise AdapterError(f"FRITZ!Box rejected command {switchcmd}")
            return text

    async def list_devices(self) -> list[dict[str, Any]]:
        xml_text = await self.command("getdevicelistinfos")
        root = ET.fromstring(xml_text)
        rows: list[dict[str, Any]] = []
        for node in root.findall(".//device"):
            ain = (node.attrib.get("identifier") or "").strip()
            if not ain:
                continue
            switch = node.find("switch")
            if switch is None:
                continue
            rows.append({
                "ain": ain,
                "name": (node.findtext("name") or ain).strip(),
                "present": (node.findtext("present") or "0").strip() == "1",
                "product": (node.attrib.get("productname") or "FRITZ! Smart Home").strip(),
            })
        return rows


class FritzSwitchAdapter(SwitchAdapter):
    def __init__(self, device: DeviceConfig):
        if not device.host:
            raise AdapterError("FRITZ!Box host missing")
        username = os.getenv(device.username_env or "GC_FRITZ_USERNAME", "").strip()
        password = os.getenv(device.password_env or "GC_FRITZ_PASSWORD", "")
        if not username or not password:
            stored = get_credentials("fritz")
            if stored:
                username, password = stored
        if not username or not password:
            raise AdapterError("FRITZ!Box credentials are not configured")
        self.device = device
        self.ain = device.native_id
        self.client = FritzAhaClient(device.host, username, password)

    async def read_state(self) -> dict[str, Any]:
        try:
            present_raw = await self.client.command("getswitchpresent", self.ain)
            state_raw = await self.client.command("getswitchstate", self.ain)
            power_raw = await self.client.command("getswitchpower", self.ain)
            energy_raw = await self.client.command("getswitchenergy", self.ain)
            name = await self.client.command("getswitchname", self.ain)
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            raise AdapterError(f"FRITZ!Box read failed ({type(exc).__name__})") from exc
        present = present_raw == "1"
        on = state_raw == "1"
        power_w = float(power_raw) / 1000.0 if power_raw.lstrip("-").isdigit() and int(power_raw) >= 0 else None
        energy_wh = float(energy_raw) if energy_raw.lstrip("-").isdigit() and int(energy_raw) >= 0 else None
        return {
            "online": present,
            "on": on,
            "power_w": power_w,
            "energy_wh": energy_wh,
            "voltage_v": None,
            "current_a": None,
            "frequency_hz": None,
            "native_name": name,
            "ain": self.ain,
            "transport": "local-fritz-aha",
        }

    async def set_switch(self, on: bool) -> dict[str, Any]:
        command = "setswitchon" if on else "setswitchoff"
        try:
            result = await self.client.command(command, self.ain)
        except httpx.HTTPError as exc:
            raise AdapterError(f"FRITZ!Box switch failed ({type(exc).__name__})") from exc
        if result not in {"0", "1"}:
            raise AdapterError("FRITZ!Box returned an unexpected switch result")
        return await self.read_state()
