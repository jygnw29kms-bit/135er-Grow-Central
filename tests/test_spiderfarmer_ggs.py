import asyncio

import pytest

from app.devices.models import Capability
from app.devices.spiderfarmer_ggs import SpiderFarmerGgsProvider, _extract_json_objects, normalize_ggs_status


def test_fragmented_noisy_json_stream_is_reassembled():
    buffer = bytearray(b"\x00\xffjunk{\"method\":\"getDevSta\",\"code\":200,\"data\":{\"sensor\":{\"temp\":23.3")
    assert _extract_json_objects(buffer) == []
    buffer.extend(b",\"humi\":37.7,\"vpd\":1.78},\"fan\":{\"on\":1,\"level\":5},\"light\":{\"on\":1,\"level\":26}}}")
    messages = _extract_json_objects(buffer)
    assert len(messages) == 1
    state = normalize_ggs_status(messages[0])
    assert state[Capability.TEMPERATURE.value] == 23.3
    assert state[Capability.HUMIDITY.value] == 37.7
    assert state[Capability.VPD.value] == 1.78
    assert state[Capability.FAN_SPEED.value] == 50
    assert state[Capability.BRIGHTNESS.value] == 26
    assert state["fan_power"] is True
    assert state["light_power"] is True


def test_non_status_message_is_rejected():
    with pytest.raises(ValueError):
        normalize_ggs_status({"method": "other", "code": 200, "data": {}})


def test_writes_are_intentionally_blocked():
    provider = SpiderFarmerGgsProvider()
    with pytest.raises(PermissionError, match="hardware validation"):
        asyncio.run(provider.command("AA:BB:CC:DD:EE:FF", Capability.FAN_SPEED, 60))
