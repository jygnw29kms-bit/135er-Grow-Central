from datetime import datetime, timedelta, timezone
from pathlib import Path
import asyncio

import app.rooms as rooms


def _sample(at, ppfd):
    return {"timestamp": at.isoformat(), "ppfd_umol_m2_s": ppfd}


def test_dli_integrates_continuous_ppfd_history():
    start = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
    samples = [_sample(start + timedelta(minutes=5*i), 500.0) for i in range(4)]
    result = rooms.calculate_daily_dli(samples, 18.0)
    assert result["estimated"] is False
    assert result["quality"] == "continuous"
    assert result["sample_count"] == 4
    assert result["coverage_seconds"] == 900.0
    assert abs(result["dli_mol_m2_day"] - 0.45) < 0.001


def test_dli_drops_large_gaps_and_marks_partial():
    start = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
    samples = [
        _sample(start, 500.0),
        _sample(start + timedelta(minutes=5), 500.0),
        _sample(start + timedelta(hours=2), 500.0),
    ]
    result = rooms.calculate_daily_dli(samples, 18.0)
    assert result["quality"] == "partial"
    assert result["dropped_segments"] == 1
    assert result["coverage_seconds"] == 300.0


def test_single_ppfd_is_clearly_marked_as_estimate():
    now = datetime.now(timezone.utc)
    result = rooms.calculate_daily_dli([_sample(now, 600.0)], 18.0)
    assert result["estimated"] is True
    assert result["quality"] == "estimate"
    assert result["assumed_light_hours"] == 18.0
    assert abs(result["dli_mol_m2_day"] - 38.88) < 0.001


def test_light_cycle_parser_uses_on_hours():
    assert rooms._parse_light_hours("18/6") == 18.0
    assert rooms._parse_light_hours("12/12") == 12.0
    assert rooms._parse_light_hours("bad", 16.0) == 16.0


def test_today_checkin_exposes_room_dli(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt", "light_cycle": "18/6"})
    rooms.append_sensor(state, "room_1", {"ppfd_umol_m2_s": 600.0, "source": "test"})
    rooms.save_state(state)

    today = asyncio.run(rooms.today_checkin())

    assert today["rooms"][0]["dli"]["estimated"] is True
    assert today["rooms"][0]["dli"]["dli_mol_m2_day"] is not None


def test_daily_checkin_ui_labels_dli_estimates():
    js = Path("web/menu-live.js").read_text(encoding="utf-8")
    assert "DLI:" in js
    assert "(Schätzung)" in js
    assert "(Teilwerte)" in js
