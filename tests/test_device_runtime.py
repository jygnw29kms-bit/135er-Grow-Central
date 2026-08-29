from __future__ import annotations

import asyncio
import json

import pytest

from app.devices.legacy_smarthome import LegacySmartHomeProvider
from app.devices.models import Capability
from app.devices.runtime import ProviderRuntime


def test_runtime_exposes_proven_and_native_providers():
    runtime = ProviderRuntime()
    assert set(runtime.ids()) == {"fritz", "growcentral_esp32", "home_assistant", "mqtt", "shelly", "tapo", "zigbee"}


def test_legacy_state_normalization_is_vendor_neutral():
    state = LegacySmartHomeProvider.normalize_state(
        {
            "online": True,
            "on": True,
            "power_w": 73.5,
            "energy_wh": 1234,
            "voltage": 231.2,
            "current": 0.32,
        }
    )
    assert state == {
        "online": True,
        Capability.POWER.value: True,
        Capability.POWER_METER.value: 73.5,
        Capability.ENERGY.value: 1234,
        Capability.VOLTAGE.value: 231.2,
        Capability.CURRENT.value: 0.32,
    }


def test_compatibility_provider_discovers_registered_devices(tmp_path, monkeypatch):
    path = tmp_path / "devices.json"
    path.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "id": "tent_light",
                        "name": "Growbox Licht",
                        "adapter": "shelly",
                        "native_id": "0",
                        "approved": True,
                        "writable": True,
                        "host": "192.0.2.10",
                        "metadata": {"product": "Shelly Plus 1PM", "capabilities": ["power_w", "energy_wh"]},
                    },
                    {
                        "id": "other",
                        "name": "Other",
                        "adapter": "tapo",
                        "native_id": "other",
                        "approved": True,
                        "writable": False,
                        "host": "192.0.2.11",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(path))

    devices = asyncio.run(LegacySmartHomeProvider("shelly").discover())
    assert len(devices) == 1
    device = devices[0]
    assert device.global_id == "shelly:tent_light"
    assert device.name == "Growbox Licht"
    assert Capability.POWER in device.capabilities
    assert Capability.POWER_METER in device.capabilities
    assert Capability.ENERGY in device.capabilities
    assert device.metadata["approved"] is True
    assert device.metadata["writable"] is True


def test_unapproved_device_cannot_be_read_or_written(tmp_path, monkeypatch):
    path = tmp_path / "devices.json"
    path.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "id": "locked",
                        "name": "Locked",
                        "adapter": "shelly",
                        "native_id": "0",
                        "approved": False,
                        "writable": False,
                        "host": "192.0.2.12",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(path))
    provider = LegacySmartHomeProvider("shelly")

    with pytest.raises(PermissionError, match="not approved"):
        asyncio.run(provider.state("locked"))
    with pytest.raises(PermissionError, match="not approved"):
        asyncio.run(provider.command("locked", Capability.POWER, True))
