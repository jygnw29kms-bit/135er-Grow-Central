import asyncio

import pytest

from app.devices.mars_hydro_marspro import MarsHydroMarsProProvider, normalize_mars_status
from app.devices.models import Capability


def test_mars_status_normalizes_sensor_and_actuators():
    state = normalize_mars_status({
        "method": "getDevSta",
        "code": 200,
        "data": {
            "sensor": {"temp": 26.4, "humi": 57.9, "vpd": 1.45, "ppfd": 916, "tempSoil": 26.3, "humiSoil": 68.7, "ECSoil": 0.48},
            "light": {"on": 1, "level": 78},
            "fan": {"on": 1, "level": 10},
            "blower": {"on": 1, "level": 67},
        },
    })
    assert state[Capability.TEMPERATURE.value] == 26.4
    assert state[Capability.HUMIDITY.value] == 57.9
    assert state[Capability.VPD.value] == 1.45
    assert state[Capability.PPFD.value] == 916.0
    assert state[Capability.SOIL_MOISTURE.value] == 68.7
    assert state[Capability.EC.value] == 0.48
    assert state[Capability.BRIGHTNESS.value] == 78
    assert state[Capability.FAN_SPEED.value] == 67
    assert state["light_power"] is True
    assert state["fan_power"] is True


def test_mars_non_status_rejected():
    with pytest.raises(ValueError):
        normalize_mars_status({"method": "getSysSta", "code": 200, "data": {}})


def test_mars_writes_blocked_until_hardware_validation():
    provider = MarsHydroMarsProProvider()
    with pytest.raises(PermissionError, match="hardware validation"):
        asyncio.run(provider.command("tent", Capability.BRIGHTNESS, 70))
