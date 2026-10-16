import asyncio
from pathlib import Path

import app.rooms as rooms


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    rooms.save_state(state)


def test_today_checkin_aggregates_tasks_events_and_targets(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    profile = asyncio.run(rooms.create_grow_profile(rooms.GrowProfileCreate(
        name="Heute Profil",
        phases=[rooms.GrowProfilePhase(
            phase="vegetative",
            expected_days=28,
            targets=rooms.GrowTargets(vpd_kpa_min=0.8, vpd_kpa_max=1.2),
        )],
        tasks=[{"title": "Blätter prüfen", "phase": "vegetative"}],
    )))
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(
        name="Plant 1", phase="vegetative", profile_id=profile["id"]
    )))
    with rooms.edit_state() as state:
        rooms.append_sensor(state, "room_1", {"temperature_c": 24.0, "humidity_percent": 60.0, "source": "assigned-devices"})
    asyncio.run(rooms.add_plant_event(
        "room_1", plant["id"], rooms.GrowEventCreate(type="watering", note="500 ml")
    ))

    today = asyncio.run(rooms.today_checkin())

    assert today["event_count"] >= 1
    assert today["task_count"] == 1
    assert today["rooms"][0]["tasks"][0]["title"] == "Blätter prüfen"
    assert today["rooms"][0]["plants"][0]["vpd"]["status"] in {"low", "target", "high"}
    assert today["rooms"][0]["sensor_snapshot"]["temperature_c"] == 24.0


def test_photo_journal_is_valid_quick_log_and_creates_photo_event(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    row = asyncio.run(rooms.add_room_journal(
        "room_1", rooms.JournalEntry(category="photo", title="Foto", text="")
    ))

    assert row["category"] == "photo"
    event = rooms.load_state()["grow_events"][-1]
    assert event["type"] == "photo"
    assert event["payload"]["journal_entry_id"] == row["id"]


def test_daily_checkin_is_wired_into_final_master_growlog():
    js = Path("web/menu-live.js").read_text(encoding="utf-8")
    assert "/api/v1/rooms/today" in js
    assert "gc-quick-log" in js
    assert "Gießen" in js
    assert "Düngen" in js
    assert "Foto" in js
    assert "Beobachtung" in js
