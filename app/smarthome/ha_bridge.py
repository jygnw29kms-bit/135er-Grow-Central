"""Scoped, opt-in export to Home Assistant; never an arbitrary service proxy."""
from __future__ import annotations

import asyncio
import math
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request

from app.audit import append_audit
from app.rooms import _native_gc_devices
from app.devices.runtime import runtime
from .adapters.base import AdapterError
from .adapters.factory import build_switch_adapter
from .models import SwitchCommand
from .policy import PolicyDenied, assert_switch_write_allowed
from .registry import DeviceRegistry

PREFIX = '/api/v1/home-assistant'


def bridge_authenticated(request: Request) -> bool:
    if os.getenv('GC_HA_EXPORT_ENABLED', 'false').lower() != 'true':
        return False
    expected = os.getenv('GC_HA_BRIDGE_TOKEN', '').strip()
    header = request.headers.get('authorization', '')
    candidate = header[7:] if header.lower().startswith('bearer ') else ''
    return len(expected) >= 32 and bool(candidate) and secrets.compare_digest(candidate, expected)


def require_bridge_auth(request: Request):
    if not bridge_authenticated(request):
        raise HTTPException(401, 'Home Assistant bridge disabled or invalid credentials')


router = APIRouter(prefix=PREFIX, tags=['home-assistant'], dependencies=[Depends(require_bridge_auth)])
METRICS = {
    'temperature_c': ('temperature', '°C'),
    'temperature': ('temperature', '°C'),
    'soil_temperature': ('temperature', '°C'),
    'humidity': ('humidity', '%'),
    'humidity_percent': ('humidity', '%'),
    'soil_moisture': ('moisture', '%'),
    'power_w': ('power', 'W'),
    'energy_wh': ('energy', 'Wh'),
    'voltage_v': ('voltage', 'V'),
    'current_a': ('current', 'A'),
    'frequency_hz': ('frequency', 'Hz'),
}


def _allowed(variable: str) -> set[str]:
    return {item.strip() for item in os.getenv(variable, '').split(',') if item.strip()}


def _writable(device) -> bool:
    if device.id not in _allowed('GC_HA_EXPORT_SWITCH_IDS'):
        return False
    try:
        assert_switch_write_allowed(device)
    except PolicyDenied:
        return False
    return True


def _export(row: dict, writable: bool = False) -> dict:
    state = row.get('state') or {}
    measurements = {}
    for key, (device_class, unit) in METRICS.items():
        value = state.get(key)
        if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
            measurements[key] = {'value': value, 'device_class': device_class, 'unit': unit}
    return {'id': row['id'], 'name': row['name'], 'online': bool(row.get('online')),
            'writable': writable, 'on': state.get('on') if isinstance(state.get('on'), bool) else None,
            'measurements': measurements}


@router.get('/snapshot')
async def snapshot():
    selected = _allowed('GC_HA_EXPORT_DEVICE_IDS')
    devices = [d for d in DeviceRegistry.from_env().list()
               if d.approved and d.id in selected and d.adapter != 'home_assistant']

    async def read(device):
        try:
            state = await build_switch_adapter(device).read_state()
        except AdapterError:
            state = {'online': False}
        return _export({'id': device.id, 'name': device.name, 'online': state.get('online', True), 'state': state}, _writable(device))

    # Native rows already enforce persistent trust and fresh cryptographic proofs.
    async def read_native():
        if any(identifier.startswith('growcentral_esp32:') for identifier in selected):
            return [_export(row) for row in await _native_gc_devices() if row['id'] in selected]
        return []
    # Other configured providers are exported as measurements only. The explicit
    # ID allowlist is the operator's consent; native trust is never bypassed.
    excluded = {'growcentral_esp32', 'home_assistant', 'shelly', 'tapo', 'fritz'}

    async def read_provider(identifier):
        provider_id, _, native_id = identifier.partition(':')
        if not native_id or provider_id in excluded or provider_id not in runtime.ids():
            return None
        try:
            async with asyncio.timeout(6):
                provider = runtime.get(provider_id)
                health = await provider.health(native_id)
                state = dict(await provider.state(native_id)) if health.online else {}
            return _export({'id': identifier, 'name': native_id, 'online': health.online, 'state': state})
        except Exception:
            return _export({'id': identifier, 'name': native_id, 'online': False, 'state': {}})

    legacy, native, extra = await asyncio.gather(
        asyncio.gather(*(read(d) for d in devices)), read_native(),
        asyncio.gather(*(read_provider(identifier) for identifier in sorted(selected) if ':' in identifier)))
    return {'schema': 1, 'devices': [*legacy, *native, *(row for row in extra if row is not None)]}


@router.post('/devices/{device_id}/switch')
async def switch(device_id: str, command: SwitchCommand):
    try:
        device = DeviceRegistry.from_env().get(device_id)
    except KeyError as exc:
        raise HTTPException(404, 'unknown device') from exc
    if device.id not in _allowed('GC_HA_EXPORT_DEVICE_IDS') or device.adapter == 'home_assistant' or not _writable(device):
        append_audit('home_assistant.command.denied', device_id=device.id, action='switch')
        raise HTTPException(403, 'device not permitted for Home Assistant control')
    try:
        state = await build_switch_adapter(device).set_switch(command.on)
    except AdapterError as exc:
        append_audit('home_assistant.command.failed', device_id=device.id, action='switch')
        raise HTTPException(502, 'device command failed') from exc
    append_audit('home_assistant.command.success', device_id=device.id, action='switch', requested=command.on)
    return {'ok': True, 'state': state}
