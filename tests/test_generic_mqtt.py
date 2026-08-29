import json

import pytest

from app.devices.generic_mqtt import GenericMqttProvider
from app.devices.models import Capability, DeviceClass
from app.devices.runtime import ProviderRuntime


def test_generic_mqtt_config_is_strict_and_normalized():
    config = GenericMqttProvider._parse_config(json.dumps({
        "id": "soil-1",
        "name": "Soil 1",
        "device_class": "sensor",
        "capabilities": ["temperature", "soil_moisture", "ec", "unknown"],
        "manufacturer": "DIY",
    }).encode())
    assert config["id"] == "soil-1"
    assert config["device_class"] is DeviceClass.SENSOR
    assert config["capabilities"] == (Capability.TEMPERATURE, Capability.SOIL_MOISTURE, Capability.EC)


def test_generic_mqtt_state_filters_undeclared_fields():
    state = GenericMqttProvider._normalize_state(
        json.dumps({"temperature": 24.3, "soil_moisture": 48, "dangerous_raw": "ignored", "online": True}).encode(),
        (Capability.TEMPERATURE, Capability.SOIL_MOISTURE),
    )
    assert state == {"temperature": 24.3, "soil_moisture": 48, "online": True}


def test_generic_mqtt_rejects_invalid_config():
    with pytest.raises(ValueError):
        GenericMqttProvider._parse_config(b'{"id":"x","name":"X","capabilities":[]}')


def test_runtime_contains_generic_mqtt():
    assert "mqtt" in ProviderRuntime().ids()
