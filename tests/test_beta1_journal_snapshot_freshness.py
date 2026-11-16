"""Historical growbook readings are labelled by age, never upgraded into live data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import rooms

ROOT = Path(__file__).resolve().parents[1]


def snapshot(delta):
    state = rooms.empty_state()
    state["sensor_history"].append({
        "room_id": "room_test",
        "timestamp": (datetime.now(timezone.utc) - delta).isoformat(),
        "temperature_c": 24.5,
        "humidity_percent": 58.0,
        "soil_moisture_percent": 42.0,
    })
    return rooms.live_room_snapshot("room_test", state)


def test_fresh_and_old_archive_samples_are_distinct():
    fresh = snapshot(timedelta(seconds=40))
    old = snapshot(timedelta(hours=2))
    assert fresh["historical_fresh"] is True
    assert fresh["historical_age_seconds"] >= 0
    assert old["historical_fresh"] is False
    assert old["historical_age_seconds"] > 600
    assert old["historical_snapshot"]["soil_moisture_percent"] == 42.0


def test_missing_archive_is_never_shown_as_live():
    result = rooms.live_room_snapshot("room_test", rooms.empty_state())
    assert result["historical_fresh"] is False
    assert result["historical_age_seconds"] is None


def test_local_and_cloud_display_same_stale_sample_warning():
    local = (ROOT / "web/gc-final.js").read_text(encoding="utf-8")
    cloud = (ROOT / "cloud/portal/gc-final-cloud.js").read_text(encoding="utf-8")
    key = "function journalSnapshotMarkup(row){"
    assert key in local and key in cloud
    local_fragment = local.split(key, 1)[1].split("function journalEntryDetail(row)", 1)[0]
    cloud_fragment = cloud.split(key, 1)[1].split("function journalEntryDetail(row)", 1)[0]
    assert local_fragment == cloud_fragment
    assert "veraltet/ungeprüft" in local_fragment
    assert "historical_age_seconds" in local_fragment
