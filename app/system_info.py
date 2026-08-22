"""Read-only appliance, host and network identity for the local GUI."""
from __future__ import annotations

import json
import platform
import socket
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from app.hardware import hardware_identity

router = APIRouter(prefix="/api/v1/system", tags=["system"])
ROOT = Path(__file__).resolve().parent.parent


def _text(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "").strip() or fallback
    except OSError:
        return fallback


def _parse_interfaces(payload: str) -> list[dict[str, Any]]:
    """Normalize `ip -j address` output without exposing routes or secrets."""
    try:
        source = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return []
    rows: list[dict[str, Any]] = []
    for item in source if isinstance(source, list) else []:
        name = str(item.get("ifname") or "").strip()
        if not name:
            continue
        addresses = []
        for address in item.get("addr_info") or []:
            family = address.get("family")
            local = str(address.get("local") or "").strip()
            if family not in {"inet", "inet6"} or not local:
                continue
            addresses.append({
                "family": "IPv4" if family == "inet" else "IPv6",
                "address": local,
                "prefix": int(address.get("prefixlen") or 0),
                "scope": str(address.get("scope") or "unknown"),
            })
        rows.append({
            "name": name,
            "state": str(item.get("operstate") or "UNKNOWN").lower(),
            "mac": str(item.get("address") or ""),
            "mtu": int(item.get("mtu") or 0),
            "addresses": addresses,
        })
    return rows


def _interfaces() -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["ip", "-j", "address", "show"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return _parse_interfaces(result.stdout) if result.returncode == 0 else []


def _uptime() -> dict[str, Any]:
    raw = _text(Path("/proc/uptime"), "0").split()[0]
    try:
        seconds = max(0, int(float(raw)))
    except ValueError:
        seconds = 0
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = ([f"{days}d"] if days else []) + ([f"{hours}h"] if hours or days else []) + [f"{minutes}m"]
    return {"seconds": seconds, "display": " ".join(parts)}


def _operating_system() -> str:
    for line in _text(Path("/etc/os-release"), "PRETTY_NAME=Linux").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"') or "Linux"
    return "Linux"


def system_identity() -> dict[str, Any]:
    interfaces = _interfaces()
    usable = [
        address
        for interface in interfaces
        if interface["name"] != "lo"
        for address in interface["addresses"]
        if address["scope"] in {"global", "site"}
    ]
    primary_ipv4 = next((row["address"] for row in usable if row["family"] == "IPv4"), None)
    hardware = hardware_identity()
    return {
        "hostname": socket.gethostname(),
        "model": hardware["model"] if hardware["model"] != "unknown" else platform.machine(),
        "hardware": hardware,
        "version": _text(ROOT / "VERSION", "unknown"),
        "build": _text(ROOT / "BUILD", "development"),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "operating_system": _operating_system(),
        "domain": "135er-Grow-Central.local",
        "primary_ipv4": primary_ipv4,
        "interfaces": interfaces,
        "addresses": usable,
        "uptime": _uptime(),
    }


@router.get("/info")
async def system_info():
    return system_identity()
