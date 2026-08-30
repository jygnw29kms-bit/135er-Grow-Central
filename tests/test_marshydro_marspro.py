from __future__ import annotations

import asyncio
import json

import pytest

from app.devices.marshydro_marspro import MarsHydroMarsProProvider
from app.devices.models import Capability


def test_marshydro_normalizes_known_telemetry_only():
    state = MarsHydroMarsProProvider.normalize_state({
        "online": True,
        "temp": 26.4,
        "rh": 59,
        "vpd": 1.18,
        "ppfd": 620,
        "soil_temp": 23.1,
        "soil_moisture": 48,
        "soil_ec": 1.42,
        "light_level": 70,
        "fan_level": 60,
        "vendor_raw": "ignored",
    })
    assert state == {
        "online": True,
        "temperature": 26.4,
        "humidity": 59,
        "vpd": 1.18,
        "ppfd": 620,
        "soil_temperature": 23.1,
        "soil_moisture": 48,
        "ec": 1.42,
        "brightness": 70,
        "fan_speed": 60,
    }


def test_marshydro_cache_discovery_and_state(tmp_path, monkeypatch):
    cache = tmp_path / "mars.json"
    cache.write_text(json.dumps({"devices": [{
        "serial": "MH123",
        "name": "Growbox Controller",
        "model": "MH-CB43",
        "state": {"online": True, "temperature": 25.8, "humidity": 61},
    }]}), encoding="utf-8")
    monkeypatch.setenv("GC_MARSHYDRO_CACHE", str(cache))
    provider = MarsHydroMarsProProvider()
    devices = asyncio.run(provider.discover())
    assert len(devices) == 1
    assert devices[0].native_id == "MH123"
    state = asyncio.run(provider.state("MH123"))
    assert state["temperature"] == 25.8
    assert state["humidity"] == 61


def test_marshydro_writes_remain_locked():
    provider = MarsHydroMarsProProvider()
    with pytest.raises(PermissionError, match="hardware validation"):
        asyncio.run(provider.command("MH123", Capability.BRIGHTNESS, 50))
