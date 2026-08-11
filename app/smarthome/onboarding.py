"""Local-network device discovery and deliberately restricted onboarding."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import subprocess
import time
from collections.abc import Iterable
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr

from app.audit import append_audit
from app.security import require_write_auth

from .models import DeviceConfig
from .registry import DeviceRegistry

router = APIRouter(prefix="/api/v1/smarthome/onboarding", tags=["smart-home-onboarding"])
Provider = Literal["shelly", "fritz", "tapo", "matter", "unknown"]


class Candidate(BaseModel):
    provider: Provider
    host: str
    name: str
    source: str
    port: int | None = None
    native_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeRequest(BaseModel):
    provider: Provider
    host: str
    port: int | None = None


class RegisterRequest(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    provider: Literal["shelly", "fritz", "tapo", "matter"]
    host: str
    native_id: str = "switch:0"
    channel: int = Field(default=0, ge=0, le=16)


class AccountDiscoveryRequest(BaseModel):
    """Credentials are used for one discovery request and are never persisted."""
    provider: Literal["tapo"]
    username: str = Field(min_length=3, max_length=254)
    password: SecretStr
    timeout: float = Field(default=5.0, ge=1.0, le=10.0)


def _lan_host(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise HTTPException(400, "host must be a literal LAN IP address") from exc
    if address.version != 4 or not (address.is_private or address.is_link_local):
        raise HTTPException(400, "host must be a private or link-local IPv4 address")
    if address.is_loopback or address.is_unspecified or address.is_multicast or address.is_reserved:
        raise HTTPException(400, "host must be a usable LAN address")
    return str(address)


def _deduplicate(rows: Iterable[Candidate]) -> list[Candidate]:
    result: dict[tuple[str, str], Candidate] = {}
    for row in rows:
        result[(row.provider, row.host)] = row
    return sorted(result.values(), key=lambda item: (item.provider, item.host))


def _ipv4_discovery_targets() -> list[tuple[str | None, str]]:
    """Return every usable interface/broadcast pair on a multi-homed Pi."""
    try:
        result = subprocess.run(["ip", "-j", "-4", "address", "show", "up"], capture_output=True, text=True, timeout=3, check=False)
        rows = json.loads(result.stdout) if result.returncode == 0 else []
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        rows = []
    targets: list[tuple[str | None, str]] = []
    for row in rows:
        ifname = row.get("ifname")
        if ifname == "lo":
            continue
        for address in row.get("addr_info", []):
            broadcast = address.get("broadcast")
            if address.get("family") == "inet" and broadcast:
                targets.append((ifname, broadcast))
    return list(dict.fromkeys(targets)) or [(None, "255.255.255.255")]


async def _kasa_candidates(timeout: float) -> list[Candidate]:
    try:
        from kasa import Discover
    except ImportError:
        return []
    try:
        devices = await Discover.discover(timeout=timeout)
    except Exception:
        return []
    rows = []
    for host, device in devices.items():
        alias = getattr(device, "alias", None) or getattr(device, "model", None) or "TP-Link device"
        rows.append(Candidate(provider="tapo", host=host, name=str(alias), source="tp-link-discovery", metadata={"model": getattr(device, "model", None)}))
    return rows


async def _kasa_account_candidates(request: AccountDiscoveryRequest) -> list[Candidate]:
    """Discover Tapo/Kasa devices using credentials without retaining them."""
    try:
        from kasa import Credentials, Discover
    except ImportError as exc:
        raise HTTPException(503, "TP-Link discovery support is not installed") from exc
    try:
        credentials = Credentials(request.username.strip(), request.password.get_secret_value())
        results = await asyncio.gather(*(
            Discover.discover(
                target=target,
                interface=interface,
                credentials=credentials,
                discovery_timeout=int(request.timeout),
                timeout=int(request.timeout),
            )
            for interface, target in _ipv4_discovery_targets()
        ), return_exceptions=True)
    except Exception as exc:
        raise HTTPException(502, f"TP-Link/Tapo-Suche konnte nicht gestartet werden ({type(exc).__name__})") from None
    devices = {}
    errors = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(type(result).__name__)
        else:
            devices.update(result)
    if not devices and errors:
        raise HTTPException(401, "Tapo-Anmeldung oder lokale Erkennung fehlgeschlagen. Tapo-Konto, Passwort und Geräte-WLAN prüfen.")
    rows: list[Candidate] = []
    for host, device in devices.items():
        alias = getattr(device, "alias", None) or getattr(device, "model", None) or "TP-Link device"
        rows.append(Candidate(provider="tapo", host=host, name=str(alias), source="tp-link-account-assisted", native_id=str(getattr(device, "device_id", "") or "") or None, metadata={"model": getattr(device, "model", None), "device_type": str(getattr(device, "device_type", "unknown")), "authentication": "verified-for-this-request"}))
    return rows


def _ssdp_candidates(timeout: float) -> list[Candidate]:
    message = "M-SEARCH * HTTP/1.1\r\nHOST:239.255.255.250:1900\r\nMAN:\"ssdp:discover\"\r\nMX:2\r\nST:ssdp:all\r\n\r\n".encode()
    rows: list[Candidate] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(message, ("239.255.255.250", 1900))
        while True:
            try:
                payload, sender = sock.recvfrom(65535)
            except TimeoutError:
                break
            text = payload.decode("utf-8", "replace")
            lowered = text.lower()
            provider: Provider = "unknown"
            if "fritz" in lowered or "avm" in lowered:
                provider = "fritz"
            elif "shelly" in lowered:
                provider = "shelly"
            if provider != "unknown":
                rows.append(Candidate(provider=provider, host=sender[0], name=f"{provider.title()} device", source="ssdp", metadata={"response": text[:500]}))
    finally:
        sock.close()
    return rows


def _mdns_candidates(timeout: float) -> list[Candidate]:
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        return []
    rows: list[Candidate] = []

    class Listener(ServiceListener):
        def add_service(self, zeroconf, service_type, name):
            info = zeroconf.get_service_info(service_type, name, timeout=1500)
            if not info:
                return
            provider: Provider = "unknown"
            lowered = f"{service_type} {name}".lower()
            if "matter" in lowered:
                provider = "matter"
            elif "shelly" in lowered:
                provider = "shelly"
            if provider == "unknown":
                return
            for address in info.parsed_addresses():
                try:
                    _lan_host(address)
                except HTTPException:
                    continue
                rows.append(Candidate(provider=provider, host=address, port=info.port, name=name.removesuffix(service_type).rstrip("."), source="mdns", metadata={"service": service_type}))

        def update_service(self, zeroconf, service_type, name):
            self.add_service(zeroconf, service_type, name)

        def remove_service(self, zeroconf, service_type, name):
            return None

    zeroconf = Zeroconf()
    try:
        ServiceBrowser(zeroconf, ["_shelly._tcp.local.", "_matter._tcp.local.", "_matterc._udp.local."], Listener())
        time.sleep(timeout)
    finally:
        zeroconf.close()
    return rows


@router.get("/providers")
async def providers():
    return {
        "providers": [
            {"id": "shelly", "discovery": True, "probe": True, "control": True},
            {"id": "fritz", "discovery": True, "probe": True, "control": False, "note": "AHA credentials required next"},
            {"id": "tapo", "discovery": True, "probe": True, "account_assisted": True, "control": False, "note": "TP-Link account-assisted local discovery"},
            {"id": "matter", "discovery": True, "probe": True, "control": False, "note": "commissioning code and Matter fabric required"},
        ]
    }


@router.post("/discover", dependencies=[Depends(require_write_auth)])
async def discover_devices(timeout: float = 4.0):
    timeout = min(max(timeout, 1.0), 10.0)
    ssdp, mdns, kasa = await asyncio.gather(asyncio.to_thread(_ssdp_candidates, timeout), asyncio.to_thread(_mdns_candidates, timeout), _kasa_candidates(timeout))
    rows = _deduplicate([*ssdp, *mdns, *kasa])
    append_audit("smarthome.discovery.completed", found=len(rows), providers=sorted({row.provider for row in rows}))
    return {"devices": [row.model_dump(mode="json") for row in rows], "count": len(rows)}


@router.post("/discover/account", dependencies=[Depends(require_write_auth)])
async def discover_devices_with_account(request: AccountDiscoveryRequest):
    rows = await _kasa_account_candidates(request)
    append_audit("smarthome.account_discovery.completed", provider=request.provider, found=len(rows))
    return {"devices": [row.model_dump(mode="json") for row in rows], "count": len(rows), "credentials_stored": False, "networks_scanned": len(_ipv4_discovery_targets())}


@router.post("/probe", dependencies=[Depends(require_write_auth)])
async def probe_device(request: ProbeRequest):
    host = _lan_host(request.host)
    result: dict[str, Any] = {"provider": request.provider, "host": host, "reachable": False, "ready": False}
    try:
        if request.provider == "shelly":
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(f"http://{host}/rpc", json={"id": 1, "method": "Shelly.GetDeviceInfo"})
                response.raise_for_status()
                result.update(reachable=True, ready=True, details=response.json().get("result", {}))
        elif request.provider == "fritz":
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://{host}:49000/tr64desc.xml")
                response.raise_for_status()
                result.update(reachable=True, ready=False, needs=["username", "password"], details={"tr064": True})
        elif request.provider == "tapo":
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, request.port or 80), 5)
            writer.close(); await writer.wait_closed()
            result.update(reachable=True, ready=False, needs=["tp_link_username", "tp_link_password"])
        elif request.provider == "matter":
            result.update(reachable=True, ready=False, needs=["matter_server", "commissioning_code"], details={"commissioning_required": True})
        else:
            raise HTTPException(400, "unsupported provider")
    except (httpx.HTTPError, OSError, asyncio.TimeoutError) as exc:
        result["error"] = type(exc).__name__
    append_audit("smarthome.probe.completed", provider=request.provider, host=host, reachable=result["reachable"])
    return result


@router.post("/register", dependencies=[Depends(require_write_auth)])
async def register_device(request: RegisterRequest):
    host = _lan_host(request.host)
    registry = DeviceRegistry.from_env()
    device = DeviceConfig(id=request.id, name=request.name, adapter=request.provider, native_id=request.native_id, host=host, channel=request.channel, approved=False, writable=False, metadata={"onboarding": "pending_approval"})
    try:
        registry.upsert(device)
    except OSError as exc:
        raise HTTPException(500, "device registry is not writable") from exc
    append_audit("smarthome.device.registered", device_id=device.id, adapter=device.adapter, host=host)
    return {"ok": True, "device": device.model_dump(mode="json"), "warning": "device remains read-only and unapproved"}
