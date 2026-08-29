from __future__ import annotations

import json

import pytest

from app.devices.gc_esp32_protocol import (
    PROTOCOL,
    SCHEMA,
    device_topic,
    encode_command,
    normalize_state,
    parse_announcement,
    validate_ack,
)
from app.devices.models import Capability, DeviceClass


def test_announcement_parses_gc_device_contract():
    announce = parse_announcement(
        json.dumps(
            {
                "schema": SCHEMA,
                "protocol": PROTOCOL,
                "id": "soil-01",
                "name": "Substrat Sensor 1",
                "device_class": "sensor",
                "model": "GC-SOIL-ESP32",
                "firmware": "0.1.0",
                "capabilities": ["soil_moisture", "soil_temperature", "ec"],
            }
        )
    )
    assert announce.id == "soil-01"
    assert announce.device_class is DeviceClass.SENSOR
    assert announce.capabilities == (
        Capability.SOIL_MOISTURE,
        Capability.SOIL_TEMPERATURE,
        Capability.EC,
    )


def test_state_rejects_undeclared_capability():
    with pytest.raises(ValueError, match="undeclared"):
        normalize_state(
            '{"soil_moisture":48.2,"ph":6.2}',
            (Capability.SOIL_MOISTURE,),
        )


def test_command_and_ack_are_correlated():
    payload = json.loads(encode_command("abc123", Capability.POWER, True))
    assert payload == {"command_id": "abc123", "capability": "power", "value": True}
    state = validate_ack('{"command_id":"abc123","ok":true,"state":{"power":true}}', "abc123")
    assert state == {"power": True}


def test_ack_mismatch_is_not_accepted():
    with pytest.raises(ValueError, match="mismatch"):
        validate_ack('{"command_id":"old","ok":true}', "new")


def test_topic_builder_rejects_unsafe_ids():
    assert device_topic("growcentral/v1", "soil-01", "state") == "growcentral/v1/devices/soil-01/state"
    with pytest.raises(ValueError):
        device_topic("growcentral/v1", "../bad", "state")
