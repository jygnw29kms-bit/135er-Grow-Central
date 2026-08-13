import os

import pytest

from app.smarthome.adapters.factory import build_switch_adapter
from app.smarthome.adapters.fritz import FritzAhaClient, FritzSwitchAdapter
from app.smarthome.adapters.tapo import TapoSwitchAdapter
from app.smarthome.models import DeviceConfig


def test_fritz_challenge_response_v2_shape():
    challenge = "2$1000$00112233445566778899aabbccddeeff$1000$ffeeddccbbaa99887766554433221100"
    result = FritzAhaClient._response(challenge, "secret-password")
    assert result.startswith(challenge + "$")
    assert len(result.rsplit("$", 1)[1]) == 64


def test_factory_builds_fritz(monkeypatch):
    monkeypatch.setenv("GC_FRITZ_USERNAME", "growcentral")
    monkeypatch.setenv("GC_FRITZ_PASSWORD", "secret")
    device = DeviceConfig(id="fritz-plug", name="FRITZ Plug", adapter="fritz", native_id="12345", host="192.168.178.1")
    adapter = build_switch_adapter(device)
    assert isinstance(adapter, FritzSwitchAdapter)


def test_factory_builds_tapo(monkeypatch):
    monkeypatch.setenv("GC_TAPO_USERNAME", "user@example.test")
    monkeypatch.setenv("GC_TAPO_PASSWORD", "secret")
    device = DeviceConfig(id="tapo-plug", name="Tapo Plug", adapter="tapo", native_id="switch:0", host="192.168.178.50")
    adapter = build_switch_adapter(device)
    assert isinstance(adapter, TapoSwitchAdapter)


def test_adapters_fail_closed_without_credentials(monkeypatch):
    for key in ("GC_FRITZ_USERNAME", "GC_FRITZ_PASSWORD", "GC_TAPO_USERNAME", "GC_TAPO_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    fritz = DeviceConfig(id="fritz-plug", name="FRITZ Plug", adapter="fritz", native_id="12345", host="192.168.178.1")
    tapo = DeviceConfig(id="tapo-plug", name="Tapo Plug", adapter="tapo", native_id="switch:0", host="192.168.178.50")
    with pytest.raises(Exception):
        build_switch_adapter(fritz)
    with pytest.raises(Exception):
        build_switch_adapter(tapo)
