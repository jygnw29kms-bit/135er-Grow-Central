"""Vendor integration layer for Spider Farmer, ESP32 bridges and Mars Hydro/iConnect.

The module intentionally keeps vendor-specific protocol assumptions behind a small,
local-first API. Spider Farmer GGS support is modelled from public reverse-engineering
findings, while transport details remain configurable and disabled for writes by default.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security import require_write_auth

router = APIRouter(prefix="/api/vendors", tags=["vendor-integrations"])


@dataclass(frozen=True)
class VendorProfile:
    vendor: str
    family: str
    model: str
    code: str | None
    transport: tuple[str, ...]
    capabilities: tuple[str, ...]
    status: str = "experimental"


PROFILES = (
    VendorProfile(
        vendor="Spider Farmer",
        family="GGS",
        model="Control Box",
        code="1001",
        transport=("mqtt_tls",),
        capabilities=("temperature", "humidity", "vpd", "co2", "ppfd", "soil", "blower", "fan", "climate"),
    ),
    VendorProfile(
        vendor="Spider Farmer",
        family="GGS",
        model="Power Strip 5",
        code="1002",
        transport=("mqtt_tls",),
        capabilities=("outlet_1_5", "light_1_2", "sensors", "blower", "fan"),
    ),
    VendorProfile(
        vendor="Spider Farmer",
        family="GGS",
        model="Light Controller",
        code="1005",
        transport=("mqtt_tls",),
        capabilities=("light_1_2", "brightness", "spectrum", "timeslot", "ppfd_mode"),
    ),
    VendorProfile(
        vendor="Spider Farmer",
        family="GGS",
        model="Power Strip 10",
        code="1007",
        transport=("mqtt_tls",),
        capabilities=("outlet_1_10", "light_1_2", "sensors", "blower", "fan", "heater"),
    ),
    VendorProfile(
        vendor="Mars Hydro",
        family="iConnect/iFresh",
        model="DF100/DF100M family",
        code=None,
        transport=("ble", "local_bridge"),
        capabilities=("fan", "speed", "telemetry", "diagnostics"),
    ),
    VendorProfile(
        vendor="Generic",
        family="ESP32",
        model="GrowControl Bridge",
        code=None,
        transport=("http_json", "mqtt"),
        capabilities=("sensor", "relay", "pwm", "fan", "light", "custom"),
    ),
)

_state_lock = Lock()
_bridge_state: dict[str, dict[str, Any]] = {}


class BridgeTelemetry(BaseModel):
    device_id: str = Field(min_length=2, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    vendor: str = Field(default="ESP32", min_length=2, max_length=64)
    model: str = Field(default="GrowControl Bridge", min_length=2, max_length=96)
    values: dict[str, Any] = Field(default_factory=dict)


class BridgeCommand(BaseModel):
    device_id: str = Field(min_length=2, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    channel: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    value: bool | int | float | str


@router.get("/profiles")
async def profiles() -> dict[str, Any]:
    return {
        "profiles": [asdict(profile) for profile in PROFILES],
        "spider_farmer_transport": {
            "mode": "mqtt_tls_adapter",
            "default_port": 8883,
            "writes_enabled": os.getenv("GC_SPIDER_WRITES", "false").lower() == "true",
            "note": "Protocol adapter remains isolated until validated against real hardware.",
        },
        "esp32": {
            "ingest": "/api/vendors/bridge/telemetry",
            "commands": "/api/vendors/bridge/command",
            "mqtt_enabled": os.getenv("GC_ESP32_MQTT_ENABLED", "false").lower() == "true",
        },
    }


@router.get("/status")
async def vendor_status() -> dict[str, Any]:
    with _state_lock:
        devices = list(_bridge_state.values())
    return {
        "spider_farmer": {
            "enabled": os.getenv("GC_SPIDER_ENABLED", "false").lower() == "true",
            "transport": "mqtt_tls",
            "port": int(os.getenv("GC_SPIDER_MQTT_PORT", "8883")),
            "writes_enabled": os.getenv("GC_SPIDER_WRITES", "false").lower() == "true",
        },
        "mars_hydro": {
            "mode": "existing_ble_diagnostics_plus_bridge",
            "enabled": True,
        },
        "esp32": {
            "enabled": os.getenv("GC_ESP32_ENABLED", "true").lower() == "true",
            "devices": devices,
        },
    }


@router.post("/bridge/telemetry", dependencies=[Depends(require_write_auth)])
async def bridge_telemetry(body: BridgeTelemetry) -> dict[str, Any]:
    clean_values: dict[str, Any] = {}
    for key, value in body.values.items():
        if len(str(key)) > 64:
            continue
        if isinstance(value, (bool, int, float, str)) or value is None:
            clean_values[str(key)] = value
    record = {
        "device_id": body.device_id,
        "vendor": body.vendor,
        "model": body.model,
        "values": clean_values,
        "last_seen": int(time.time()),
        "online": True,
    }
    with _state_lock:
        _bridge_state[body.device_id] = record
    return {"ok": True, "device": record}


@router.post("/bridge/command", dependencies=[Depends(require_write_auth)])
async def bridge_command(body: BridgeCommand) -> dict[str, Any]:
    if os.getenv("GC_ESP32_WRITES", "false").lower() != "true":
        raise HTTPException(403, "ESP32 writes are disabled until explicitly enabled")
    with _state_lock:
        if body.device_id not in _bridge_state:
            raise HTTPException(404, "ESP32 bridge not registered")
    # Transport dispatch is intentionally separated from the API. A validated MQTT or
    # HTTP transport can consume this normalized command without exposing raw packets.
    return {
        "ok": True,
        "queued": True,
        "command": {"device_id": body.device_id, "channel": body.channel, "value": body.value},
    }
