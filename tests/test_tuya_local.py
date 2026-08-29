import json

import pytest

from app.devices.models import Capability
from app.devices.runtime import ProviderRuntime
from app.devices.tuya_local import TuyaLocalProvider


def test_tuya_dp_map_is_explicit_and_ignores_unknown():
    row = {
        "dps": {
            "power": {"dp": 1, "writable": True},
            "temperature": {"dp": "18", "scale": 10},
            "unknown_capability": {"dp": 99},
        }
    }
    mapping = TuyaLocalProvider._cap_map(row)
    assert set(mapping) == {Capability.POWER, Capability.TEMPERATURE}
    assert mapping[Capability.POWER]["writable"] is True
    assert mapping[Capability.TEMPERATURE]["scale"] == 10.0


def test_tuya_scaling_round_trip():
    spec = {"dp": "18", "scale": 10.0, "writable": True, "invert": False}
    assert TuyaLocalProvider._decode(243, spec) == 24.3
    assert TuyaLocalProvider._encode(24.3, spec) == 243


def test_tuya_config_discovery_without_network(tmp_path, monkeypatch):
    path = tmp_path / "tuya.json"
    path.write_text(json.dumps({"devices": [{
        "id": "humidifier-1",
        "name": "Befeuchter",
        "device_id": "abc",
        "local_key": "secret",
        "ip": "192.0.2.22",
        "version": 3.4,
        "device_class": "humidifier",
        "dps": {"power": {"dp": 1, "writable": True}, "humidity": {"dp": 2, "scale": 1}},
    }]}), encoding="utf-8")
    monkeypatch.setenv("GC_TUYA_DEVICE_CONFIG", str(path))
    provider = TuyaLocalProvider()
    import asyncio
    devices = asyncio.run(provider.discover())
    assert len(devices) == 1
    assert devices[0].native_id == "humidifier-1"
    assert Capability.POWER in devices[0].capabilities
    assert Capability.HUMIDITY in devices[0].capabilities


def test_tuya_write_requires_explicit_writable_mapping():
    mapping = TuyaLocalProvider._cap_map({"dps": {"power": {"dp": 1}}})
    assert mapping[Capability.POWER]["writable"] is False


def test_runtime_contains_tuya():
    assert "tuya" in ProviderRuntime().ids()
