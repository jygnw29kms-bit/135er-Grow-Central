"""Native FRITZ!Box AHA smart-home adapter.

Uses AVM's local HTTP smart-home interface. Credentials stay server-side and
are never returned to the browser.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any

import httpx
from defusedxml import ElementTree as ET

from app.credential_store import get_credentials
from ..models import DeviceConfig
from .base import AdapterError, SwitchAdapter


FUNCTION_BITS = {
    0: "HAN-FUN-Gerät",
    2: "Licht",
    4: "Alarmsensor",
    5: "Taster",
    6: "Heizkörperregler",
    7: "Energiemessgerät",
    8: "Temperatursensor",
    9: "Schaltsteckdose",
    10: "DECT-Repeater",
    11: "Mikrofon",
    13: "HAN-FUN-Unit",
    15: "Schaltaktor",
    16: "Levelsteuerung",
    17: "Farbsteuerung",
    18: "Rollladen",
    20: "Luftfeuchtigkeitssensor",
}


def _number(text: str | None, scale: float = 1.0, *, allow_negative: bool = False) -> float | None:
    value = (text or "").strip()
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed < 0 and not allow_negative:
        return None
    return parsed / scale


def _flag(text: str | None) -> bool | None:
    value = (text or "").strip()
    return value == "1" if value in {"0", "1"} else None


def _device_data(node: ET.Element) -> dict[str, Any]:
    """Normalize all plug information published by AVM's device XML."""
    try:
        function_mask = int(node.attrib.get("functionbitmask") or 0)
    except ValueError:
        function_mask = 0
    switch = node.find("switch")
    powermeter = node.find("powermeter")
    temperature = node.find("temperature")
    power_w = _number(powermeter.findtext("power") if powermeter is not None else None, 1000.0)
    voltage_v = _number(powermeter.findtext("voltage") if powermeter is not None else None, 1000.0)
    current_a = power_w / voltage_v if power_w is not None and voltage_v and voltage_v > 0 else None
    return {
        "online": _flag(node.findtext("present")) is True,
        "on": _flag(switch.findtext("state") if switch is not None else None),
        "power_w": power_w,
        "energy_wh": _number(powermeter.findtext("energy") if powermeter is not None else None),
        "voltage_v": voltage_v,
        "current_a": current_a,
        "current_source": "calculated_from_power_and_voltage" if current_a is not None else None,
        "frequency_hz": None,
        "temperature_c": _number(temperature.findtext("celsius") if temperature is not None else None, 10.0, allow_negative=True),
        "temperature_offset_c": _number(temperature.findtext("offset") if temperature is not None else None, 10.0, allow_negative=True),
        "native_name": (node.findtext("name") or node.attrib.get("identifier") or "FRITZ! Smart Home").strip(),
        "ain": (node.attrib.get("identifier") or "").strip(),
        "device_id": (node.attrib.get("id") or "").strip() or None,
        "product_name": (node.attrib.get("productname") or "FRITZ! Smart Home").strip(),
        "manufacturer": (node.attrib.get("manufacturer") or "AVM").strip(),
        "firmware_version": (node.attrib.get("fwversion") or "").strip() or None,
        "function_bitmask": function_mask,
        "functions": [label for bit, label in FUNCTION_BITS.items() if function_mask & (1 << bit)],
        "tx_busy": _flag(node.findtext("txbusy")),
        "battery_percent": _number(node.findtext("battery")),
        "battery_low": _flag(node.findtext("batterylow")),
        "switch_mode": (switch.findtext("mode") or "").strip() or None if switch is not None else None,
        "ui_lock": _flag(switch.findtext("lock") if switch is not None else None),
        "device_lock": _flag(switch.findtext("devicelock") if switch is not None else None),
        "transport": "local-fritz-aha",
        "data_source": "getdeviceinfos",
    }


class FritzLoginError(AdapterError):
    """Safe, machine-readable FRITZ! login failure without credential data."""

    def __init__(self, code: str, message: str, *, retry_after: int = 0):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


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
            # AVM specifies only the dynamic second salt and the second hash as
            # the response. Build 62 incorrectly prefixed the complete challenge,
            # which makes every valid FRITZ!OS 7.24+ login fail.
            return f"{salt2}${hash2.hex()}"
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
                raise FritzLoginError("challenge_missing", "FRITZ!Box login challenge missing")
            known_users = {
                (node.text or "").strip()
                for node in root.findall(".//Users/User")
                if (node.text or "").strip()
            }
            if known_users and self.username not in known_users:
                raise FritzLoginError("unknown_user", "FRITZ!Box username is unknown")
            try:
                block_time = max(0, min(60, int((root.findtext("BlockTime") or "0").strip())))
            except ValueError:
                block_time = 0
            if block_time:
                # Do not leave the GUI request hanging for up to a minute. AVM
                # explicitly reports the remaining lockout time via BlockTime.
                raise FritzLoginError(
                    "blocked",
                    "FRITZ!Box temporarily blocks login attempts",
                    retry_after=block_time,
                )
            response_value = self._response(challenge, self.password)
            response = await client.post(f"{self.base}/login_sid.lua", data={"username": self.username, "response": response_value})
            response.raise_for_status()
            logged = ET.fromstring(response.text)
            sid = (logged.findtext("SID") or "").strip()
            if not sid or sid == "0000000000000000":
                raise FritzLoginError("bad_credentials", "FRITZ!Box authentication failed")
            rights_nodes = logged.findall(".//Rights")
            rights: dict[str, int] = {}
            for rights_node in rights_nodes:
                names = rights_node.findall("Name")
                access_values = rights_node.findall("Access")
                for name_node, access_node in zip(names, access_values):
                    name = (name_node.text or "").strip()
                    try:
                        access = int((access_node.text or "0").strip())
                    except ValueError:
                        access = 0
                    if name:
                        rights[name] = access
            if rights and rights.get("HomeAuto", 0) < 1:
                raise FritzLoginError(
                    "missing_homeauto_permission",
                    "FRITZ!Box user lacks Smart Home permission",
                )
            self.sid = sid
            return sid

    async def command(self, switchcmd: str, ain: str | None = None, **arguments: str | int | bool) -> str:
        sid = self.sid or await self.login()
        params: dict[str, str] = {"sid": sid, "switchcmd": switchcmd}
        if ain:
            params["ain"] = ain
        for key, value in arguments.items():
            params[key] = "1" if value is True else "0" if value is False else str(value)
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
            data = _device_data(node)
            rows.append({"ain": ain, "name": data["native_name"], "present": data["online"], "product": data["product_name"], "details": data})
        return rows

    async def list_automations(self) -> dict[str, list[dict[str, Any]]]:
        """Read the routine and template data exposed by AVM AHA."""
        trigger_xml, template_xml = await asyncio.gather(
            self.command("gettriggerlistinfos"),
            self.command("gettemplatelistinfos"),
        )
        trigger_root = ET.fromstring(trigger_xml)
        template_root = ET.fromstring(template_xml)
        triggers = [{
            "identifier": (node.attrib.get("identifier") or "").strip(),
            "name": (node.findtext("name") or "Unbenannte FRITZ!-Routine").strip(),
            "active": _flag(node.attrib.get("active")) is True,
        } for node in trigger_root.findall(".//trigger") if (node.attrib.get("identifier") or "").strip()]
        templates = []
        for node in template_root.findall(".//template"):
            identifier = (node.attrib.get("identifier") or "").strip()
            if not identifier or node.attrib.get("autocreate") == "1" and node.find("sub_templates") is None:
                continue
            templates.append({
                "identifier": identifier,
                "name": (node.findtext("name") or "Unbenannte FRITZ!-Vorlage").strip(),
                "devices": [(item.attrib.get("identifier") or "").strip() for item in node.findall("./devices/device") if (item.attrib.get("identifier") or "").strip()],
                "actions": [item.tag for item in node.findall("./applymask/*")],
                "scenario": node.find("sub_templates") is not None,
            })
        return {"triggers": triggers, "templates": templates}

    async def set_trigger_active(self, identifier: str, active: bool) -> bool:
        result = await self.command("settriggeractive", identifier, active=active)
        return result not in {"", "0", "inval"} if active else result != "inval"

    async def apply_template(self, identifier: str) -> None:
        await self.command("applytemplate", identifier)


class FritzSwitchAdapter(SwitchAdapter):
    def __init__(self, device: DeviceConfig):
        if not device.host:
            raise AdapterError("FRITZ!Box host missing")
        stored = get_credentials("fritz")
        if stored:
            username, password = stored
        else:
            username = os.getenv(device.username_env or "GC_FRITZ_USERNAME", "").strip()
            password = os.getenv(device.password_env or "GC_FRITZ_PASSWORD", "")
        if not username or not password:
            raise AdapterError("FRITZ!Box credentials are not configured")
        self.device = device
        self.ain = device.native_id
        self.client = FritzAhaClient(device.host, username, password)

    async def read_state(self) -> dict[str, Any]:
        try:
            xml_text = await self.client.command("getdeviceinfos", self.ain)
            node = ET.fromstring(xml_text)
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            raise AdapterError(f"FRITZ!Box read failed ({type(exc).__name__})") from exc
        if node.tag not in {"device", "group"}:
            candidate = next((item for item in node.findall(".//device") if (item.attrib.get("identifier") or "").replace(" ", "") == self.ain.replace(" ", "")), None)
            if candidate is None:
                raise AdapterError("FRITZ!Box device information did not contain the configured AIN")
            node = candidate
        if node.find("switch") is None:
            raise AdapterError("FRITZ!Box device does not expose a switch")
        return _device_data(node)

    async def set_switch(self, on: bool) -> dict[str, Any]:
        command = "setswitchon" if on else "setswitchoff"
        try:
            result = await self.client.command(command, self.ain)
        except httpx.HTTPError as exc:
            raise AdapterError(f"FRITZ!Box switch failed ({type(exc).__name__})") from exc
        if result not in {"0", "1"}:
            raise AdapterError("FRITZ!Box returned an unexpected switch result")
        return await self.read_state()
