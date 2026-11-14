"""Archive and restore rooms without losing grow data or sensor enrollment."""
import asyncio
import pytest
from fastapi import HTTPException
from app import rooms


@pytest.fixture
def room_store(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"] = [{"id": "room_a", "name": "Zelt A"}, {"id": "room_b", "name": "Zelt B"}]
    state["assignments"] = {"mars-hydro:fc3000": "room_a", "mars-hydro:df150m": "room_b", "growcentral_esp32:gc-soil-aaaaaa": "room_a"}
    state["plants"] = [{"id": "plant_1", "room_id": "room_a", "name": "Tomate"}]
    state["room_journal"] = [{"id": "journal_1", "room_id": "room_a", "title": "Foto"}]
    state["plant_journal"] = [{"id": "entry_1", "plant_id": "plant_1", "room_id": "room_a"}]
    state["grow_events"] = [{"id": "event_1", "room_id": "room_a"}]
    state["sensor_history"] = [{"id": "measurement_1", "room_id": "room_a", "soil_moisture_percent": 42}]
    rooms.save_state(state)
    return state


def test_archive_releases_hardware_without_deleting_grow_records(room_store, monkeypatch):
    updates = []
    class FakeTrust:
        def set_room_id(self, device_id, room_id, **kwargs):
            updates.append((device_id, room_id, kwargs))
    monkeypatch.setattr(rooms, "TrustStore", FakeTrust)
    response = asyncio.run(rooms.delete_room("room_a"))
    state = rooms.load_state()
    assert response["archived"] is True
    assert set(response["released_devices"]) == {"mars-hydro:fc3000", "growcentral_esp32:gc-soil-aaaaaa"}
    assert [r["id"] for r in state["rooms"]] == ["room_b"]
    assert [r["id"] for r in state["archived_rooms"]] == ["room_a"]
    assert state["assignments"] == {"mars-hydro:df150m": "room_b"}
    for key in ("plants", "room_journal", "plant_journal", "grow_events", "sensor_history"):
        assert len(state[key]) == 1
    assert updates == [("gc-soil-aaaaaa", None, {"previous_room_id": "room_a"})]


def test_restore_keeps_original_room_id_and_historical_data(room_store, monkeypatch):
    monkeypatch.setattr(rooms, "TrustStore", lambda: type("Trust", (), {"set_room_id": lambda *args, **kwargs: True})())
    asyncio.run(rooms.delete_room("room_a"))
    response = asyncio.run(rooms.restore_room("room_a"))
    state = rooms.load_state()
    assert response["room"]["id"] == "room_a"
    assert response["devices_unassigned"] is True
    assert state["archived_rooms"] == []
    assert "mars-hydro:fc3000" not in state["assignments"]
    assert state["plants"][0]["room_id"] == "room_a"
    assert state["room_journal"][0]["id"] == "journal_1"
    assert state["sensor_history"][0]["soil_moisture_percent"] == 42
    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.restore_room("room_a"))
    assert error.value.status_code == 409


def test_room_archive_unknown_id_is_safe(room_store):
    before = rooms.load_state()
    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.delete_room("missing"))
    assert error.value.status_code == 404
    assert rooms.load_state() == before


def test_explicit_unassignment_cannot_remove_other_room_device(room_store):
    result = asyncio.run(rooms.unassign_device("room_a", "mars-hydro:df150m"))
    assert result["unassigned"] is False
    assert rooms.load_state()["assignments"]["mars-hydro:df150m"] == "room_b"
    result = asyncio.run(rooms.unassign_device("room_a", "mars-hydro:fc3000"))
    assert result["unassigned"] is True
    assert "mars-hydro:fc3000" not in rooms.load_state()["assignments"]
