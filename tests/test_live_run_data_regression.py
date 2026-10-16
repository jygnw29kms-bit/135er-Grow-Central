import asyncio
import json

import pytest

import app.rooms as rooms


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_legacy_rooms_state_is_extended_without_losing_existing_data(tmp_path, monkeypatch):
    data_file = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", data_file)
    legacy = {
        "rooms": [{"id": "room_1", "name": "Zelt 1", "kind": "grow_tent"}],
        "assignments": {"growcentral_esp32:sensor_1": "room_1"},
        "room_journal": [{"id": "entry_1", "room_id": "room_1", "category": "note", "title": "Altbestand"}],
        "plants": [{"id": "plant_1", "room_id": "room_1", "name": "Pflanze 1", "phase": "vegetative"}],
        "plant_journal": [{"id": "entry_2", "plant_id": "plant_1", "room_id": "room_1", "category": "watering"}],
        "sensor_history": [{"id": "sample_1", "room_id": "room_1", "temperature_c": 24.5, "humidity_percent": 58.0}],
    }
    _write(data_file, legacy)

    state = rooms.load_state()

    for key in legacy:
        assert state[key] == legacy[key]
    assert state["grow_events"] == []
    assert state["grow_profiles"] == []

    with rooms.edit_state() as editable:
        editable["grow_profiles"].append({"id": "profile_1", "name": "Neu"})

    persisted = json.loads(data_file.read_text(encoding="utf-8"))
    for key in legacy:
        assert persisted[key] == legacy[key]
    assert persisted["grow_profiles"] == [{"id": "profile_1", "name": "Neu"}]


def test_invalid_rooms_database_fails_closed_instead_of_resetting_data(tmp_path, monkeypatch):
    data_file = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", data_file)
    original = '{"rooms": [{"id": "room_1"}], BROKEN'
    data_file.write_text(original, encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid rooms database"):
        rooms.load_state()

    assert data_file.read_text(encoding="utf-8") == original


def test_grow_event_keeps_immutable_sensor_snapshot(tmp_path, monkeypatch):
    data_file = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", data_file)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    state["plants"].append({"id": "plant_1", "room_id": "room_1", "name": "Pflanze 1", "phase": "vegetative"})
    rooms.append_sensor(state, "room_1", {"temperature_c": 23.0, "humidity_percent": 60.0, "soil_moisture_percent": 41.0, "source": "assigned-devices"})
    rooms.save_state(state)

    event = asyncio.run(rooms.add_plant_event(
        "room_1",
        "plant_1",
        rooms.GrowEventCreate(type="observation", note="Vor Änderung"),
    ))
    assert event["sensor_snapshot"]["temperature_c"] == 23.0
    assert event["sensor_snapshot"]["soil_moisture_percent"] == 41.0

    with rooms.edit_state() as current:
        rooms.append_sensor(current, "room_1", {"temperature_c": 27.0, "humidity_percent": 48.0, "soil_moisture_percent": 19.0, "source": "assigned-devices"})

    persisted = rooms.load_state()
    stored = next(item for item in persisted["grow_events"] if item["id"] == event["id"])
    assert stored["sensor_snapshot"]["temperature_c"] == 23.0
    assert stored["sensor_snapshot"]["soil_moisture_percent"] == 41.0
    assert persisted["sensor_history"][-1]["temperature_c"] == 27.0


def test_co2_stays_hidden_by_default_in_final_master():
    html = open("web/platform.html", encoding="utf-8").read()
    assert 'data-optional-metric="co2" hidden' in html
