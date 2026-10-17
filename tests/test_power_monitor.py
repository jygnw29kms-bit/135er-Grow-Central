from app import power_monitor


def test_first_sample_is_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(power_monitor, "STATE_FILE", tmp_path / "power.json")
    power_monitor._last_current = None
    monkeypatch.setattr(power_monitor, "_flags", lambda: {"under_voltage_now": False, "frequency_capped_now": False, "throttled_now": False, "under_voltage_occurred": True, "frequency_capped_occurred": False, "throttled_occurred": True})
    assert power_monitor.sample() == []
    assert not power_monitor.STATE_FILE.exists()


def test_new_undervoltage_transition_is_recorded(monkeypatch, tmp_path):
    monkeypatch.setattr(power_monitor, "STATE_FILE", tmp_path / "power.json")
    power_monitor._last_current = {"under_voltage_now": False, "frequency_capped_now": False, "throttled_now": False}
    flags = {"under_voltage_now": True, "frequency_capped_now": False, "throttled_now": False, "under_voltage_occurred": True, "frequency_capped_occurred": False, "throttled_occurred": False}
    monkeypatch.setattr(power_monitor, "_flags", lambda: flags)
    monkeypatch.setattr(power_monitor, "_snapshot", lambda event, f: {"event": event, "flags": f})
    events = power_monitor.sample()
    assert events[0]["event"] == "under_voltage_now"
    assert power_monitor._load()["events"][0]["event"] == "under_voltage_now"
