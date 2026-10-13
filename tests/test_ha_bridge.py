import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.smarthome import ha_bridge
from app.auth_middleware import GuiAuthMiddleware

TOKEN = 'bridge-' + 'a' * 40


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    monkeypatch.setenv('GC_HA_EXPORT_ENABLED', 'true')
    monkeypatch.setenv('GC_HA_BRIDGE_TOKEN', TOKEN)
    monkeypatch.setenv('GC_SMARTHOME_ENABLED', 'true')
    monkeypatch.setenv('GC_HA_EXPORT_DEVICE_IDS', 'lamp,mirror,growcentral_esp32:soil-1')
    monkeypatch.setenv('GC_HA_EXPORT_SWITCH_IDS', 'lamp,mirror')
    path = tmp_path / 'devices.json'
    path.write_text(json.dumps({'devices': [
        {'id': 'lamp', 'name': 'Lamp', 'adapter': 'shelly', 'native_id': 'switch:0', 'approved': True, 'writable': True},
        {'id': 'mirror', 'name': 'Mirror', 'adapter': 'home_assistant', 'native_id': 'switch.mirror', 'approved': True, 'writable': True},
        {'id': 'hidden', 'name': 'Hidden', 'adapter': 'shelly', 'native_id': 'switch:1', 'approved': True, 'writable': True},
    ]}))
    monkeypatch.setenv('GC_SMARTHOME_DEVICE_CONFIG', str(path))
    calls = []

    class Adapter:
        async def read_state(self):
            return {'online': True, 'on': False, 'power_w': 30, 'voltage_v': float('nan'), 'current_a': True}

        async def set_switch(self, on):
            calls.append(on)
            return {'online': True, 'on': on}

    monkeypatch.setattr(ha_bridge, 'build_switch_adapter', lambda _: Adapter())

    async def native():
        return [{'id': 'growcentral_esp32:soil-1', 'name': 'Soil', 'online': True, 'state': {'soil_moisture': 42}},
                {'id': 'growcentral_esp32:other', 'name': 'Other', 'online': True, 'state': {'soil_moisture': 43}}]

    monkeypatch.setattr(ha_bridge, '_native_gc_devices', native)
    app = FastAPI()
    app.include_router(ha_bridge.router)
    return TestClient(app), calls, app


def headers():
    return {'Authorization': 'Bearer ' + TOKEN}


def test_snapshot_scoped_and_finite(bridge):
    client, _, _ = bridge
    assert client.get('/api/v1/home-assistant/snapshot').status_code == 401
    result = client.get('/api/v1/home-assistant/snapshot', headers=headers()).json()
    assert result['schema'] == 1
    assert [r['id'] for r in result['devices']] == ['lamp', 'growcentral_esp32:soil-1']
    assert result['devices'][0]['measurements'] == {'power_w': {'value': 30, 'unit': 'W', 'device_class': 'power'}}
    assert result['devices'][1]['writable'] is False


@pytest.mark.parametrize('setting,value', [('GC_HA_EXPORT_ENABLED','false'), ('GC_HA_BRIDGE_TOKEN','short')])
def test_disabled_or_weak_token_fails_closed(bridge, monkeypatch, setting, value):
    client, _, _ = bridge
    monkeypatch.setenv(setting, value)
    assert client.get('/api/v1/home-assistant/snapshot', headers=headers()).status_code == 401


def test_switch_requires_both_allowlists_and_policy(bridge, monkeypatch):
    client, calls, _ = bridge
    url = '/api/v1/home-assistant/devices/lamp/switch'
    assert client.post(url, headers=headers(), json={'on': True}).status_code == 200
    assert calls == [True]
    for setting in ['GC_HA_EXPORT_SWITCH_IDS', 'GC_HA_EXPORT_DEVICE_IDS']:
        with monkeypatch.context() as patch:
            patch.setenv(setting, '')
            assert client.post(url, headers=headers(), json={'on': False}).status_code == 403
    monkeypatch.setenv('GC_SMARTHOME_ENABLED', 'false')
    assert client.post(url, headers=headers(), json={'on': False}).status_code == 403
    assert calls == [True]


def test_no_import_export_loop_or_hidden_control(bridge):
    client, calls, _ = bridge
    for identifier in ['mirror', 'hidden']:
        assert client.post(f'/api/v1/home-assistant/devices/{identifier}/switch', headers=headers(), json={'on': True}).status_code == 403
    assert not calls


def test_bridge_token_cannot_bypass_appliance_auth(bridge, monkeypatch):
    client, _, app = bridge
    monkeypatch.setattr('app.auth_middleware.configured', lambda: True)
    monkeypatch.setattr('app.auth_middleware.authenticated', lambda _: False)
    monkeypatch.setattr('app.auth_middleware.api_token_authenticated', lambda _: False)
    app.add_middleware(GuiAuthMiddleware)

    @app.get('/api/admin')
    async def admin():
        return {'secret': True}

    assert client.get('/api/v1/home-assistant/snapshot', headers=headers()).status_code == 200
    assert client.get('/api/admin', headers=headers()).status_code == 401
    assert client.get('/api/v1/home-assistant/snapshot', headers={'Authorization': 'Bearer wrong'}).status_code == 401


def test_revocation_removes_export(bridge, monkeypatch):
    client, _, _ = bridge
    assert len(client.get('/api/v1/home-assistant/snapshot', headers=headers()).json()['devices']) == 2
    monkeypatch.setenv('GC_HA_EXPORT_DEVICE_IDS', '')
    assert client.get('/api/v1/home-assistant/snapshot', headers=headers()).json()['devices'] == []


def test_runtime_sensors_are_explicit_and_read_only(bridge, monkeypatch):
    from types import SimpleNamespace
    client, _, _ = bridge
    monkeypatch.setenv('GC_HA_EXPORT_DEVICE_IDS', 'zigbee:climate')
    monkeypatch.setenv('GC_HA_EXPORT_SWITCH_IDS', 'zigbee:climate')
    calls = []

    class Provider:
        async def health(self, native_id):
            calls.append(native_id)
            return SimpleNamespace(online=True)

        async def state(self, native_id):
            return {'temperature': 24, 'humidity': 65, 'power': True}

    monkeypatch.setattr(ha_bridge.runtime, 'get', lambda _: Provider())
    result = client.get('/api/v1/home-assistant/snapshot', headers=headers()).json()['devices']
    assert calls == ['climate']
    assert len(result) == 1 and result[0]['writable'] is False
    assert result[0]['measurements']['temperature']['value'] == 24
    assert result[0]['measurements']['humidity']['unit'] == '%'
    assert result[0]['on'] is None
    assert client.post('/api/v1/home-assistant/devices/zigbee:climate/switch', headers=headers(), json={'on': True}).status_code == 404
