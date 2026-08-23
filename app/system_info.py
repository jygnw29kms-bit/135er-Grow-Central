"""Read-only appliance, host, resource and network identity for the local GUI."""
from __future__ import annotations

import json
import os
import platform
import shutil
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
            addresses.append({"family": "IPv4" if family == "inet" else "IPv6", "address": local, "prefix": int(address.get("prefixlen") or 0), "scope": str(address.get("scope") or "unknown")})
        rows.append({"name": name, "state": str(item.get("operstate") or "UNKNOWN").lower(), "mac": str(item.get("address") or ""), "mtu": int(item.get("mtu") or 0), "addresses": addresses})
    return rows


def _interfaces() -> list[dict[str, Any]]:
    try:
        result = subprocess.run(["ip", "-j", "address", "show"], capture_output=True, text=True, timeout=4, check=False)
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


def _memory() -> tuple[int, int]:
    values: dict[str, int] = {}
    for line in _text(Path("/proc/meminfo"), "").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        try:
            values[key] = int(raw.strip().split()[0]) * 1024
        except (ValueError, IndexError):
            pass
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    return total, max(0, total - available)


def _cpu_temperature() -> float | None:
    candidates = [Path("/sys/class/thermal/thermal_zone0/temp")]
    candidates.extend(Path("/sys/class/hwmon").glob("hwmon*/temp1_input"))
    for path in candidates:
        raw = _text(path, "")
        if not raw:
            continue
        try:
            value = float(raw)
            return value / 1000 if value > 500 else value
        except ValueError:
            continue
    return None


def _cpu_percent() -> float | None:
    try:
        first = _text(Path("/proc/stat"), "").splitlines()[0].split()[1:]
        values = [int(v) for v in first]
        total = sum(values)
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        if total <= 0:
            return None
        # This is a boot-to-now utilization indicator. It is stable and dependency-free.
        return max(0.0, min(100.0, (total - idle) * 100.0 / total))
    except (ValueError, IndexError):
        return None


def _resources() -> dict[str, Any]:
    mem_total, mem_used = _memory()
    try:
        disk = shutil.disk_usage("/")
        disk_total, disk_used = disk.total, disk.used
    except OSError:
        disk_total = disk_used = 0
    try:
        load = [round(float(v), 3) for v in os.getloadavg()]
    except OSError:
        load = []
    return {
        "cpu_count": os.cpu_count() or 0,
        "cpu_percent": _cpu_percent(),
        "cpu_temperature_c": _cpu_temperature(),
        "load_average": load,
        "memory_total_bytes": mem_total,
        "memory_used_bytes": mem_used,
        "memory_percent": round(mem_used * 100 / mem_total, 1) if mem_total else None,
        "disk_total_bytes": disk_total,
        "disk_used_bytes": disk_used,
        "disk_percent": round(disk_used * 100 / disk_total, 1) if disk_total else None,
    }


def system_identity() -> dict[str, Any]:
    interfaces = _interfaces()
    usable = [address for interface in interfaces if interface["name"] != "lo" for address in interface["addresses"] if address["scope"] in {"global", "site"}]
    primary_ipv4 = next((row["address"] for row in usable if row["family"] == "IPv4"), None)
    hardware = hardware_identity()
    version = _text(ROOT / "VERSION", "unknown")
    build = _text(ROOT / "BUILD", "development")
    return {
        "hostname": socket.gethostname(),
        "model": hardware["model"] if hardware.get("model") != "unknown" else platform.machine(),
        "hardware": hardware,
        "version": version,
        "api_version": version,
        "build": build,
        "release_channel": "alpha" if "alpha" in version.lower() else "local",
        "build_status": f"Installierter Softwarestand: {version} · Build {build}",
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "operating_system": _operating_system(),
        "domain": "135er-GrowCentral.local",
        "primary_ipv4": primary_ipv4,
        "interfaces": interfaces,
        "addresses": usable,
        "uptime": _uptime(),
        "resources": _resources(),
    }


@router.get("/info")
async def system_info():
    return system_identity()
