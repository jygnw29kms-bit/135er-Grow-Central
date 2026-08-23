from pathlib import Path

import app.rooms as rooms


def test_vpd_calculation_is_plausible():
    value = rooms.calc_vpd(25.0, 60.0)
    assert value is not None
    assert 1.2 < value < 1.4


def test_rooms_state_roundtrip(tmp_path, monkeypatch):
    target = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", target)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_test", "name": "Zelt 1"})
    state["assignments"]["plug_1"] = "room_test"
    rooms.save_state(state)
    loaded = rooms.load_state()
    assert loaded["rooms"][0]["name"] == "Zelt 1"
    assert loaded["assignments"]["plug_1"] == "room_test"
    assert target.stat().st_mode & 0o777 == 0o600


def test_sensor_sample_gets_vpd_and_room_id(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    row = rooms.append_sensor(state, "room_1", {"temperature_c": 24.0, "humidity_percent": 55.0, "source": "test"})
    assert row["room_id"] == "room_1"
    assert row["vpd_kpa"] is not None
    assert state["sensor_history"][0]["source"] == "test"


def test_console_contains_room_navigation():
    html = Path("web/console.html").read_text(encoding="utf-8")
    assert "RÄUME & GROW" in html
    assert "Geräte zuordnen" in html
    assert "Growtagebuch" in html
    assert "Pflanzen" in html
