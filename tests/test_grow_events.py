import asyncio
import json

import app.rooms as rooms


def _seed_room(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    rooms.save_state(state)
    return state


def test_legacy_rooms_state_migrates_without_losing_data(tmp_path, monkeypatch):
    target = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", target)
    target.write_text(json.dumps({
        "rooms": [{"id": "room_old", "name": "Alt"}],
        "assignments": {},
        "room_journal": [],
        "plants": [{"id": "plant_old", "room_id": "room_old", "name": "Legacy"}],
        "plant_journal": [],
        "sensor_history": [],
    }), encoding="utf-8")

    state = rooms.load_state()

    assert state["rooms"][0]["name"] == "Alt"
    assert state["plants"][0]["name"] == "Legacy"
    assert state["grow_events"] == []
    assert state["grow_profiles"] == []


def test_grow_event_keeps_immutable_sensor_snapshot(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    with rooms.edit_state() as state:
        rooms.append_sensor(state, "room_1", {
            "temperature_c": 24.5,
            "humidity_percent": 58.0,
            "soil_moisture_percent": 41.2,
            "soil_temperature_c": 22.1,
            "ppfd_umol_m2_s": 640.0,
            "ec_ms_cm": 1.4,
            "ph": 6.2,
            "source": "assigned-devices",
        })
        event = rooms._append_grow_event(
            state, "room_1", plant_id=None, event_type="watering", note="gegossen"
        )
        snapshot = dict(event["sensor_snapshot"])
        rooms.append_sensor(state, "room_1", {
            "temperature_c": 29.0,
            "humidity_percent": 40.0,
            "soil_moisture_percent": 80.0,
            "source": "later",
        })

    saved = rooms.load_state()["grow_events"][0]
    assert saved["sensor_snapshot"] == snapshot
    assert saved["sensor_snapshot"]["temperature_c"] == 24.5
    assert saved["sensor_snapshot"]["soil_moisture_percent"] == 41.2
    assert saved["sensor_snapshot"]["ppfd_umol_m2_s"] == 640.0
    assert saved["sensor_snapshot"]["ec_ms_cm"] == 1.4
    assert saved["sensor_snapshot"]["ph"] == 6.2


def test_create_plant_initializes_cycle_and_phase_event(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)

    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(
        name="Pflanze A",
        start_date="2026-10-16",
        phase="seedling",
        expected_phase_days=14,
    )))

    assert plant["phase_started_at"]
    assert plant["expected_phase_days"] == 14
    events = rooms.load_state()["grow_events"]
    assert events[-1]["plant_id"] == plant["id"]
    assert events[-1]["type"] == "phase_changed"
    assert events[-1]["payload"]["phase"] == "seedling"


def test_phase_change_is_persisted_as_timeline_event(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(name="Pflanze B", phase="vegetative")))
    original_started = plant["phase_started_at"]

    updated = asyncio.run(rooms.update_plant("room_1", plant["id"], rooms.PlantCreate(
        name="Pflanze B",
        phase="flowering",
        expected_phase_days=63,
    )))

    assert updated["phase"] == "flowering"
    assert updated["phase_started_at"]
    assert updated["phase_started_at"] >= original_started
    event = rooms.load_state()["grow_events"][-1]
    assert event["type"] == "phase_changed"
    assert event["payload"] == {"from": "vegetative", "to": "flowering"}


def test_plant_journal_gets_snapshot_and_shared_event(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(name="Pflanze C")))
    with rooms.edit_state() as state:
        rooms.append_sensor(state, "room_1", {
            "temperature_c": 25.0,
            "humidity_percent": 60.0,
            "soil_moisture_percent": 36.0,
            "source": "assigned-devices",
        })

    row = asyncio.run(rooms.add_plant_journal(
        "room_1", plant["id"], rooms.JournalEntry(category="watering", title="Gießen", text="500 ml")
    ))

    assert row["sensor_snapshot"]["soil_moisture_percent"] == 36.0
    event = rooms.load_state()["grow_events"][-1]
    assert event["type"] == "watering"
    assert event["payload"]["journal_entry_id"] == row["id"]
    assert event["sensor_snapshot"]["temperature_c"] == 25.0
