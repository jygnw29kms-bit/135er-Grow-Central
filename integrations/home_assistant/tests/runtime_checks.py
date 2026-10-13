"""Run in an isolated environment containing real Home Assistant, not stubs."""
import importlib
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
import aiohttp
from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'custom_components'))
from grow_central import GrowCentralCoordinator
from grow_central.api import GrowCentralAPI, validate_url
from grow_central.sensor import GrowCentralSensor
from grow_central.switch import GrowCentralSwitch


@pytest.mark.parametrize('url', ['http://user:pw@host', 'https://host/path', 'file:///tmp/a', 'http://host?token=x', 'http://host#x'])
def test_url_rejects_credentials_and_paths(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.asyncio
async def test_real_coordinator_entities_and_commands(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    calls = []
    snapshot = {'schema': 1, 'devices': [{'id': 'lamp', 'name': 'Lamp', 'online': True,
        'writable': True, 'on': False, 'measurements': {'power_w': {'value': 30, 'unit': 'W', 'device_class': 'power'}}}]}
    auth_allowed = True

    async def handler(request):
        if not auth_allowed or request.headers.get('Authorization') != 'Bearer secret':
            return web.Response(status=401)
        return web.json_response(snapshot)

    async def command(request):
        body = await request.json()
        calls.append(body['on'])
        snapshot['devices'][0]['on'] = body['on']
        return web.json_response({'ok': True})

    app = web.Application()
    app.router.add_get('/api/v1/home-assistant/snapshot', handler)
    app.router.add_post('/api/v1/home-assistant/devices/lamp/switch', command)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            coordinator = GrowCentralCoordinator(hass, GrowCentralAPI(session, f'http://127.0.0.1:{port}', 'secret'))
            coordinator.async_set_updated_data(await coordinator._async_update_data())
            entry = SimpleNamespace(entry_id='test-entry')
            sensor = GrowCentralSensor(coordinator, entry, 'lamp', 'power_w')
            switch = GrowCentralSwitch(coordinator, entry, 'lamp')
            assert sensor.native_value == 30
            assert sensor.device_class == 'power'
            assert sensor.available and switch.available
            await switch.async_turn_on()
            assert calls == [True] and switch.is_on
            # Removal of permission takes effect before another command.
            snapshot['devices'][0]['writable'] = False
            coordinator.async_set_updated_data(await coordinator._async_update_data())
            assert not switch.available
            with pytest.raises(HomeAssistantError):
                await switch.async_turn_off()
            assert calls == [True]
            snapshot['devices'][0]['online'] = False
            coordinator.async_set_updated_data(await coordinator._async_update_data())
            assert not sensor.available
            snapshot['devices'] = []
            coordinator.async_set_updated_data(await coordinator._async_update_data())
            assert not sensor.available and sensor.native_value is None
            auth_allowed = False
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()
    finally:
        await runner.cleanup()
        await hass.async_stop()


@pytest.mark.asyncio
async def test_platform_adds_new_entities_once_and_marks_removed_unavailable(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    coordinator = GrowCentralCoordinator(hass, None)
    coordinator.async_set_updated_data({})
    hass.data['grow_central'] = {'entry': coordinator}
    unload = []
    entry = SimpleNamespace(entry_id='entry', async_on_unload=unload.append)
    sensors, switches = [], []
    await importlib.import_module('grow_central.sensor').async_setup_entry(hass, entry, sensors.extend)
    await importlib.import_module('grow_central.switch').async_setup_entry(hass, entry, switches.extend)
    row = {'id': 'new', 'name': 'New', 'online': True, 'writable': True, 'on': False,
           'measurements': {'soil_moisture': {'value': 42, 'unit': '%', 'device_class': 'moisture'}}}
    coordinator.async_set_updated_data({'new': row})
    coordinator.async_set_updated_data({'new': row})
    assert len(sensors) == len(switches) == 1
    assert sensors[0].native_value == 42
    coordinator.async_set_updated_data({})
    assert not sensors[0].available and not switches[0].available
    for callback in unload:
        callback()
    await hass.async_stop()


@pytest.mark.asyncio
async def test_installation_config_flow_and_real_platform_setup(tmp_path):
    """Install the actual component and use HA's config-entry/platform machinery."""
    import shutil
    from homeassistant import loader
    from homeassistant.auth import auth_manager_from_config
    from homeassistant.config_entries import ConfigEntries
    from homeassistant.helpers import frame
    from homeassistant.setup import async_setup_component
    from homeassistant.helpers import entity_registry, device_registry, area_registry

    config = tmp_path / 'ha'
    component = config / 'custom_components' / 'grow_central'
    shutil.copytree(Path(__file__).resolve().parents[1] / 'custom_components' / 'grow_central', component)
    hass = HomeAssistant(str(config))
    loader.async_setup(hass)
    if hasattr(frame, 'async_setup'):
        frame.async_setup(hass)
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    if hasattr(device_registry, 'async_setup'):
        device_registry.async_setup(hass)
    await device_registry.async_load(hass)
    await area_registry.async_load(hass)
    await entity_registry.async_load(hass)
    hass.auth = await auth_manager_from_config(hass, [], [])
    assert await async_setup_component(hass, 'network', {})
    token = 't' * 40

    async def handler(request):
        if request.headers.get('Authorization') != 'Bearer ' + token:
            return web.Response(status=401)
        return web.json_response({'schema': 1, 'devices': [{'id': 'lamp', 'name': 'Lamp', 'online': True,
            'writable': True, 'on': False, 'measurements': {'power_w': {'value': 30, 'unit': 'W', 'device_class': 'power'}}}]})

    app = web.Application()
    app.router.add_get('/api/v1/home-assistant/snapshot', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    try:
        result = await hass.config_entries.flow.async_init('grow_central', context={'source': 'user'})
        assert result['type'] == 'form'
        invalid = await hass.config_entries.flow.async_configure(result['flow_id'], {'url': url, 'token': 'wrong' * 8})
        assert invalid['errors']['base'] == 'invalid_auth'
        valid = await hass.config_entries.flow.async_configure(result['flow_id'], {'url': url, 'token': token})
        assert valid['type'] == 'create_entry'
        await hass.async_block_till_done()
        entry = valid['result']
        assert entry.state.value == 'loaded'
        assert any(s.state == '30' for s in hass.states.async_all('sensor'))
        assert any(s.state == 'off' for s in hass.states.async_all('switch'))
        assert await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await runner.cleanup()
        await hass.async_stop()
