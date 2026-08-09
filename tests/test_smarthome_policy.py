import os

import pytest

from app.smarthome.models import DeviceConfig
from app.smarthome.policy import PolicyDenied, assert_switch_write_allowed


def device(**overrides):
    data = {
        "id": "test-plug",
        "name": "Test Plug",
        "adapter": "shelly",
        "native_id": "switch:0",
        "host": "192.168.1.10",
        "approved": True,
        "writable": True,
    }
    data.update(overrides)
    return DeviceConfig.model_validate(data)


def test_writes_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GC_SMARTHOME_ENABLED", raising=False)
    with pytest.raises(PolicyDenied):
        assert_switch_write_allowed(device())


def test_unapproved_device_is_denied(monkeypatch):
    monkeypatch.setenv("GC_SMARTHOME_ENABLED", "true")
    with pytest.raises(PolicyDenied):
        assert_switch_write_allowed(device(approved=False))


def test_read_only_device_is_denied(monkeypatch):
    monkeypatch.setenv("GC_SMARTHOME_ENABLED", "true")
    with pytest.raises(PolicyDenied):
        assert_switch_write_allowed(device(writable=False))


def test_approved_write_requires_global_enable(monkeypatch):
    monkeypatch.setenv("GC_SMARTHOME_ENABLED", "true")
    assert_switch_write_allowed(device())
