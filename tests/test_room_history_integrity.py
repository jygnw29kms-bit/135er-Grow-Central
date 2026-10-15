import asyncio
import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import rooms


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    target = tmp_path / 'rooms.json'
    monkeypatch.setattr(rooms, 'DATA_FILE', target)
    state = rooms.empty_state()
    state['rooms'] = [{'id': 'r1', 'name': 'Zelt'}]
    state['assignments'] = {'plug1': 'r1'}
    rooms.save_state(state)
    return target


def test_capture_preserves_edits_completed_during_device_read(state_file, monkeypatch):
    async def overview(*, refresh):
        await rooms.update_room('r1', rooms.RoomUpdate(name='Geänderter Raum'))
        await rooms.add_room_journal('r1', rooms.JournalEntry(title='Nicht verlieren'))
        return {'devices': [{'id': 'plug1', 'online': True, 'state': {'power_w': 0}}]}
    async def native(timeout): return []
    monkeypatch.setattr(rooms, 'device_overview', overview)
    monkeypatch.setattr(rooms, '_native_gc_devices', native)
    assert asyncio.run(rooms.capture_room_sensors_once()) == 1
    state = rooms.load_state()
    assert state['rooms'][0]['name'] == 'Geänderter Raum'
    assert state['room_journal'][0]['title'] == 'Nicht verlieren'
    assert state['sensor_history'][0]['power_w'] == 0


def test_capture_does_not_restore_deleted_room(state_file, monkeypatch):
    async def overview(*, refresh):
        await rooms.delete_room('r1')
        return {'devices': [{'id': 'plug1', 'online': True, 'state': {'power_w': 12}}]}
    async def native(timeout): return []
    monkeypatch.setattr(rooms, 'device_overview', overview)
    monkeypatch.setattr(rooms, '_native_gc_devices', native)
    assert asyncio.run(rooms.capture_room_sensors_once()) == 0
    assert rooms.load_state()['rooms'] == []


def test_concurrent_transactions_preserve_all_journal_entries(state_file):
    def add(index):
        asyncio.run(rooms.add_room_journal('r1', rooms.JournalEntry(title=str(index))))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(add, range(30)))
    assert {row['title'] for row in rooms.load_state()['room_journal']} == {str(i) for i in range(30)}
    before = state_file.read_bytes()
    with pytest.raises(ValueError):
        with rooms.edit_state() as state:
            state['rooms'].clear()
            raise ValueError('abort')
    assert state_file.read_bytes() == before


@pytest.mark.parametrize('payload', [[], {'rooms': {}}, {'sensor_history': ['invalid']}])
def test_corrupted_schema_is_not_overwritten(state_file, payload):
    state_file.write_text(json.dumps(payload))
    before = state_file.read_bytes()
    with pytest.raises(RuntimeError):
        asyncio.run(rooms.create_room(rooms.RoomCreate(name='Must not replace existing data')))
    assert state_file.read_bytes() == before


def test_capture_ignores_invalid_metrics_and_supports_legacy_aliases(state_file, monkeypatch):
    async def overview(*, refresh):
        return {'devices': [{'id': 'plug1', 'online': True, 'state': {
            'temperature': '24.5', 'humidity': 0, 'soil_moisture': 120,
            'power_w': float('inf'), 'energy_wh': -1, 'co2_ppm': True,
        }}]}
    async def native(timeout): return []
    monkeypatch.setattr(rooms, 'device_overview', overview)
    monkeypatch.setattr(rooms, '_native_gc_devices', native)
    assert asyncio.run(rooms.capture_room_sensors_once()) == 1
    sample = rooms.load_state()['sensor_history'][0]
    assert sample['temperature_c'] == 24.5 and sample['humidity_percent'] == 0
    assert all(sample[k] is None for k in ['soil_moisture_percent', 'power_w', 'energy_wh', 'co2_ppm'])
    with pytest.raises(ValidationError):
        rooms.SensorSample(power_w=float('inf'))


def test_sensor_csv_is_scoped_bounded_and_formula_safe(state_file):
    with rooms.edit_state() as state:
        rooms.append_sensor(state, 'other-room', {'temperature_c': 99})
        rooms.append_sensor(state, 'r1', {'temperature_c': 22, 'source': 'older'})
        rooms.append_sensor(state, 'r1', {'power_w': 0, 'soil_moisture_percent': 42.5, 'source': '=1+1'})
    app = FastAPI()
    app.include_router(rooms.router)
    client = TestClient(app)
    response = client.get('/api/v1/rooms/r1/sensors.csv?limit=1')
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1 and rows[0]['power_w'] == '0'
    assert rows[0]['temperature_c'] == ''
    assert rows[0]['source'] == "'=1+1"
    assert rows[0]['soil_moisture_percent'] == '42.5'
    assert rows[0]['soil_calibration_status'] == 'calibration_required'
    assert response.headers['cache-control'] == 'no-store'
    assert 'attachment' in response.headers['content-disposition']
    assert client.get('/api/v1/rooms/r1/sensors.csv?limit=50001').status_code == 422
    assert client.get('/api/v1/rooms/missing/sensors.csv').status_code == 404
