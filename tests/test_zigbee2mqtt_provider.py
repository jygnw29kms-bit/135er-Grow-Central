from __future__ import annotations

from app.devices.models import Capability, DeviceClass
from app.devices.zigbee2mqtt import capabilities_from_exposes, infer_device_class, normalize_zigbee_state


def test_zigbee_exposes_are_mapped_conservatively():
    exposes = [
        {
            "type": "light",
            "features": [
                {"property": "state", "type": "binary"},
                {"property": "brightness", "type": "numeric"},
            ],
        },
        {"property": "power", "type": "numeric"},
        {"property": "energy", "type": "numeric"},
        {"property": "linkquality", "type": "numeric"},
    ]
    capabilities = capabilities_from_exposes(exposes)
    assert capabilities == (
        Capability.POWER,
        Capability.BRIGHTNESS,
        Capability.POWER_METER,
        Capability.ENERGY,
    )
    assert infer_device_class(capabilities) is DeviceClass.LIGHT


def test_zigbee_soil_sensor_mapping():
    exposes = [
        {"property": "temperature"},
        {"property": "humidity"},
        {"property": "soil_moisture"},
        {"property": "conductivity"},
        {"property": "ph"},
    ]
    capabilities = capabilities_from_exposes(exposes)
    assert capabilities == (
        Capability.TEMPERATURE,
        Capability.HUMIDITY,
        Capability.SOIL_MOISTURE,
        Capability.EC,
        Capability.PH,
    )
    assert infer_device_class(capabilities) is DeviceClass.SENSOR


def test_zigbee_state_normalizes_on_off_and_measurements():
    capabilities = (
        Capability.POWER,
        Capability.POWER_METER,
        Capability.VOLTAGE,
        Capability.CURRENT,
    )
    state = normalize_zigbee_state(
        {"state": "ON", "power": 44.2, "voltage": 230.8, "current": 0.2, "linkquality": 120},
        capabilities,
    )
    assert state == {
        "online": True,
        "power": True,
        "power_meter": 44.2,
        "voltage": 230.8,
        "current": 0.2,
    }


def test_unknown_zigbee_exposes_are_not_guessed():
    capabilities = capabilities_from_exposes(
        [
            {"property": "speed"},
            {"property": "mystery_mode"},
            {"property": "linkquality"},
        ]
    )
    assert capabilities == ()
