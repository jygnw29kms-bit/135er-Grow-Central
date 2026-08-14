import os
import asyncio
from types import SimpleNamespace

import pytest

from app.smarthome.adapters.factory import build_switch_adapter
from app.smarthome.adapters.fritz import FritzAhaClient, FritzSwitchAdapter
from app.smarthome.adapters.base import AdapterError
from app.smarthome.adapters.tapo import TapoSwitchAdapter
from app.smarthome.models import DeviceConfig


def test_fritz_challenge_response_v2_shape():
    challenge = "2$1000$00112233445566778899aabbccddeeff$1000$ffeeddccbbaa99887766554433221100"
    result = FritzAhaClient._response(challenge, "secret-password")
    assert result.startswith(challenge + "$")
    assert len(result.rsplit("$", 1)[1]) == 64


def test_fritz_login_honors_blocktime_and_known_user(monkeypatch):
    sleeps = []
    responses = iter([
        SimpleNamespace(text="<SessionInfo><SID>0000000000000000</SID><Challenge>abc</Challenge><BlockTime>2</BlockTime><Users><User>growcentral</User></Users></SessionInfo>", raise_for_status=lambda: None),
        SimpleNamespace(text="<SessionInfo><SID>1234567890abcdef</SID></SessionInfo>", raise_for_status=lambda: None),
    ])

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): return next(responses)
        async def post(self, *_args, **_kwargs): return next(responses)

    async def fake_sleep(seconds): sleeps.append(seconds)
    monkeypatch.setattr("app.smarthome.adapters.fritz.httpx.AsyncClient", lambda **_kwargs: Client())
    monkeypatch.setattr("app.smarthome.adapters.fritz.asyncio.sleep", fake_sleep)
    assert asyncio.run(FritzAhaClient("fritz.box", "growcentral", "secret").login()) == "1234567890abcdef"
    assert sleeps == [2]


def test_fritz_login_rejects_unknown_username_before_password_attempt(monkeypatch):
    response = SimpleNamespace(text="<SessionInfo><SID>0000000000000000</SID><Challenge>abc</Challenge><Users><User>different</User></Users></SessionInfo>", raise_for_status=lambda: None)
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): return response
    monkeypatch.setattr("app.smarthome.adapters.fritz.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(AdapterError, match="username is unknown"):
        asyncio.run(FritzAhaClient("fritz.box", "growcentral", "secret").login())


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
