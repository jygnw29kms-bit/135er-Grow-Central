import asyncio
import base64
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

import app.grow_photos as photos
import app.rooms as rooms


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode("ascii")


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    monkeypatch.setattr(photos, "PHOTO_DIR", tmp_path / "grow-photos")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    state["plants"].append({
        "id": "plant_1",
        "room_id": "room_1",
        "name": "Plant 1",
        "phase": "flowering",
        "start_date": (date.today() - timedelta(days=20)).isoformat(),
    })
    rooms.append_sensor(state, "room_1", {
        "temperature_c": 25.0,
        "humidity_percent": 55.0,
        "soil_moisture_percent": 42.0,
        "source": "assigned-devices",
    })
    rooms.save_state(state)


def test_photo_is_stored_with_plant_phase_cycle_day_and_sensor_snapshot(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)

    row = asyncio.run(photos.create_grow_photo(photos.GrowPhotoCreate(
        room_id="room_1",
        plant_id="plant_1",
        title="Blütetag",
        note="Kontrollfoto",
        tags=["oben", "blüte", "oben"],
        image_data_url=PNG_DATA_URL,
    )))

    assert row["category"] == "photo"
    assert row["phase"] == "flowering"
    assert row["cycle_day"] == 21
    assert row["tags"] == ["oben", "blüte"]
    assert row["sensor_snapshot"]["temperature_c"] == 25.0
    assert row["sensor_snapshot"]["soil_moisture_percent"] == 42.0
    assert row["photo_bytes"] == len(PNG_1X1)
    assert (photos.PHOTO_DIR / f"{row['photo_id']}.png").is_file()

    state = rooms.load_state()
    assert state["plant_journal"][-1]["photo_id"] == row["photo_id"]
    event = state["grow_events"][-1]
    assert event["type"] == "photo"
    assert event["plant_id"] == "plant_1"
    assert event["payload"]["photo_id"] == row["photo_id"]
    assert event["sensor_snapshot"]["temperature_c"] == 25.0


def test_photo_list_and_delete_use_canonical_journal_state(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    row = asyncio.run(photos.create_grow_photo(photos.GrowPhotoCreate(
        room_id="room_1",
        image_data_url=PNG_DATA_URL,
    )))

    listing = asyncio.run(photos.list_grow_photos(room_id="room_1", plant_id=None, limit=100))
    assert [item["photo_id"] for item in listing["photos"]] == [row["photo_id"]]

    result = asyncio.run(photos.delete_grow_photo(row["photo_id"]))
    assert result["ok"] is True
    assert not (photos.PHOTO_DIR / f"{row['photo_id']}.png").exists()
    state = rooms.load_state()
    assert not any(item.get("photo_id") == row["photo_id"] for item in state["room_journal"])
    assert not any((event.get("payload") or {}).get("photo_id") == row["photo_id"] for event in state["grow_events"])


def test_photo_rejects_mismatched_image_content(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    fake = "data:image/png;base64," + base64.b64encode(b"not-a-png").decode("ascii")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(photos.create_grow_photo(photos.GrowPhotoCreate(
            room_id="room_1",
            image_data_url=fake,
        )))

    assert exc.value.status_code == 415
