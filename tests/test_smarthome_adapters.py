import os
import asyncio
from types import SimpleNamespace

import pytest

from app.smarthome.adapters.factory import build_switch_adapter
from app.smarthome.adapters.fritz import FritzAhaClient, FritzLoginError, FritzSwitchAdapter, _device_data
from app.smarthome.adapters.base import AdapterError
from app.smarthome.adapters.tapo import TapoSwitchAdapter
from app.smarthome.models import DeviceConfig


def test_fritz_challenge_response_v2_shape():
    challenge = "2$1000$00112233445566778899aabbccddeeff$1000$ffeeddccbbaa99887766554433221100"
    result = FritzAhaClient._response(challenge, "secret-password")
    assert result.startswith("ffeeddccbbaa99887766554433221100$")
    assert len(result.split("$", 1)[1]) == 64
    assert not result.startswith(challenge)


def test_fritz_challenge_response_matches_avm_reference_vector():
    challenge = "2$10000$5A1711$2000$5A1722"
    assert FritzAhaClient._response(challenge, "1example!") == (
        "5A1722$1798a1672bca7c6463d6b245f82b53703b0f50813401b03e4045a5861e689adb"
    )


def test_fritz_login_reports_blocktime_without_hanging(monkeypatch):
    responses = iter([
        SimpleNamespace(text="<SessionInfo><SID>0000000000000000</SID><Challenge>abc</Challenge><BlockTime>2</BlockTime><Users><User>growcentral</User></Users></SessionInfo>", raise_for_status=lambda: None),
        SimpleNamespace(text="<SessionInfo><SID>1234567890abcdef</SID></SessionInfo>", raise_for_status=lambda: None),
    ])

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): return next(responses)
        async def post(self, *_args, **_kwargs): return next(responses)

    monkeypatch.setattr("app.smarthome.adapters.fritz.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(FritzLoginError) as error:
        asyncio.run(FritzAhaClient("fritz.box", "growcentral", "secret").login())
    assert error.value.code == "blocked"
    assert error.value.retry_after == 2


def test_fritz_login_checks_homeauto_right(monkeypatch):
    responses = iter([
        SimpleNamespace(text="<SessionInfo><SID>0000000000000000</SID><Challenge>abc</Challenge><BlockTime>0</BlockTime><Users><User>growcentral</User></Users></SessionInfo>", raise_for_status=lambda: None),
        SimpleNamespace(text="<SessionInfo><SID>1234567890abcdef</SID><Rights><Name>HomeAuto</Name><Access>0</Access></Rights></SessionInfo>", raise_for_status=lambda: None),
    ])

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): return next(responses)
        async def post(self, *_args, **_kwargs): return next(responses)

    monkeypatch.setattr("app.smarthome.adapters.fritz.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(FritzLoginError) as error:
        asyncio.run(FritzAhaClient("fritz.box", "growcentral", "secret").login())
    assert error.value.code == "missing_homeauto_permission"


def test_fritz_login_rejects_unknown_username_before_password_attempt(monkeypatch):
    response = SimpleNamespace(text="<SessionInfo><SID>0000000000000000</SID><Challenge>abc</Challenge><Users><User>different</User></Users></SessionInfo>", raise_for_status=lambda: None)
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): return response
    monkeypatch.setattr("app.smarthome.adapters.fritz.httpx.AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(AdapterError, match="username is unknown"):
        asyncio.run(FritzAhaClient("fritz.box", "growcentral", "secret").login())


def test_fritz_plug_device_xml_exposes_identity_energy_and_temperature():
    from defusedxml import ElementTree as ET

    node = ET.fromstring("""
    <device identifier="08761 0001234" id="17" functionbitmask="896" fwversion="05.26" manufacturer="AVM" productname="FRITZ!DECT 210">
      <present>1</present><txbusy>0</txbusy><name>Grow Lampe</name>
      <switch><state>1</state><mode>manuell</mode><lock>0</lock><devicelock>1</devicelock></switch>
      <powermeter><power>123456</power><energy>9876</energy><voltage>231200</voltage></powermeter>
      <temperature><celsius>237</celsius><offset>-15</offset></temperature>
    </device>
    """)
    state = _device_data(node)
    assert state["product_name"] == "FRITZ!DECT 210"
    assert state["firmware_version"] == "05.26"
    assert state["ain"] == "08761 0001234"
    assert state["on"] is True
    assert state["power_w"] == 123.456
    assert state["energy_wh"] == 9876.0
    assert state["voltage_v"] == 231.2
    assert state["current_a"] == pytest.approx(123.456 / 231.2)
    assert state["temperature_c"] == 23.7
    assert state["temperature_offset_c"] == -1.5
    assert state["ui_lock"] is False
    assert state["device_lock"] is True
    assert "Energiemessgerät" in state["functions"]
    assert "Temperatursensor" in state["functions"]
    assert "Schaltsteckdose" in state["functions"]


def test_fritz_adapter_reads_single_complete_device_response(monkeypatch):
    monkeypatch.setenv("GC_FRITZ_USERNAME", "growcentral")
    monkeypatch.setenv("GC_FRITZ_PASSWORD", "secret")
    device = DeviceConfig(id="fritz-plug", name="FRITZ Plug", adapter="fritz", native_id="08761 0001234", host="fritz.box")
    adapter = FritzSwitchAdapter(device)
    calls = []

    async def command(name, ain=None):
        calls.append((name, ain))
        return '<device identifier="08761 0001234" id="17" functionbitmask="896" fwversion="05.26" manufacturer="AVM" productname="FRITZ!DECT 210"><present>1</present><name>Grow Lampe</name><switch><state>0</state><mode>auto</mode><lock>0</lock><devicelock>0</devicelock></switch><powermeter><power>0</power><energy>42</energy><voltage>230000</voltage></powermeter><temperature><celsius>221</celsius><offset>0</offset></temperature></device>'

    monkeypatch.setattr(adapter.client, "command", command)
    state = asyncio.run(adapter.read_state())
    assert calls == [("getdeviceinfos", "08761 0001234")]
    assert state["temperature_c"] == 22.1
    assert state["switch_mode"] == "auto"


def test_fritz_automation_parser_exposes_routines_and_visible_templates(monkeypatch):
    client = FritzAhaClient("fritz.box", "growcentral", "secret")
    responses = {
        "gettriggerlistinfos": '<triggerlist version="1"><trigger identifier="trg-1" active="1"><name>Lichtzeit</name></trigger></triggerlist>',
        "gettemplatelistinfos": '<templatelist version="1"><template identifier="tmp-1" autocreate="0"><name>Lampe an</name><devices><device identifier="08761 0001"/></devices><sub_templates/><applymask><relay_manual/></applymask></template><template identifier="tmp-hidden" autocreate="1"><name>Intern</name><devices/><applymask><relay_manual/></applymask></template></templatelist>',
    }

    async def command(name, *_args, **_kwargs):
        return responses[name]

    monkeypatch.setattr(client, "command", command)
    result = asyncio.run(client.list_automations())
    assert result["triggers"] == [{"identifier": "trg-1", "name": "Lichtzeit", "active": True}]
    assert result["templates"][0]["devices"] == ["08761 0001"]
    assert result["templates"][0]["actions"] == ["relay_manual"]
    assert [row["identifier"] for row in result["templates"]] == ["tmp-1"]


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
