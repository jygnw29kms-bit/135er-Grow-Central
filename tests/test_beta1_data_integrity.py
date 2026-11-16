"""Beta 1.0 read-only storage auditor tests (synthetic data only)."""
import json
import sqlite3

from scripts.check_beta1_data_integrity import audit


def _fixture(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    state = {
        "rooms": [{"id": "room1", "name": "Testzelt"}],
        "archived_rooms": [],
        "plants": [{"id": "plant1", "room_id": "room1"}],
        "assignments": {"device1": "room1"},
        "sensor_history": [{"room_id": "room1", "timestamp": "2026-11-16T08:00:00+01:00"}],
        "room_journal": [{"room_id": "room1", "plant_id": "plant1"}],
        "plant_journal": [], "grow_events": [],
    }
    (root / "rooms.json").write_text(json.dumps(state))
    with sqlite3.connect(root / "history.sqlite3") as con:
        con.execute("CREATE TABLE samples (value INTEGER)")
        con.execute("INSERT INTO samples VALUES (1)")
        con.commit()
    return root, state


def test_valid_data_passes_without_writes(tmp_path):
    root, state = _fixture(tmp_path)
    prior = (root / "rooms.json").read_bytes()
    result = audit(root)
    assert result["ok"]
    assert result["counts"]["db_checked"] == 1
    assert result["counts"]["plants"] == 1
    assert (root / "rooms.json").read_bytes() == prior


def test_invalid_plant_room_is_a_release_blocker(tmp_path):
    root, state = _fixture(tmp_path)
    state["plants"][0]["room_id"] = "other"
    (root / "rooms.json").write_text(json.dumps(state))
    result = audit(root)
    assert not result["ok"]
    assert any("plant references missing room" in x for x in result["errors"])


def test_duplicate_rooms_and_unknown_roles_fail(tmp_path):
    root, state = _fixture(tmp_path)
    state["rooms"].append({"id": "room1"})
    (root / "rooms.json").write_text(json.dumps(state))
    (root / "room-sharing.json").write_text(json.dumps({
        "members": [{"id": "m1", "room_id": "room1", "role": "owner"}],
        "invitations": [], "sessions": {},
    }))
    result = audit(root)
    assert not result["ok"]
    assert any("duplicate" in x for x in result["errors"])
    assert any("unknown member role" in x for x in result["errors"])


def test_photo_symlink_and_invalid_sqlite_detected(tmp_path):
    root, _ = _fixture(tmp_path)
    (root / "grow-photos").mkdir()
    (root / "grow-photos" / "escape").symlink_to(root / "rooms.json")
    (root / "sensor-calibration.db").write_bytes(b"Not a SQLite database")
    result = audit(root)
    assert not result["ok"]
    assert any("symlink" in x for x in result["errors"])
    assert any("sensor-calibration.db" in x for x in result["errors"])


def test_missing_required_rooms_file_fails(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    result = audit(root)
    assert not result["ok"]
    assert "rooms.json: missing" in result["errors"]
