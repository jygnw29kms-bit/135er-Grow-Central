from types import SimpleNamespace

from app import system_info


def test_power_health_reports_historical_undervoltage_and_throttle(monkeypatch):
    monkeypatch.setattr(system_info.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="throttled=0x50000\n"))
    result = system_info._power_health()
    assert result["status"] == "warning"
    assert result["flags"]["under_voltage_occurred"] is True
    assert result["flags"]["throttled_occurred"] is True
    assert result["flags"]["under_voltage_now"] is False


def test_power_health_reports_current_undervoltage_as_critical(monkeypatch):
    monkeypatch.setattr(system_info.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="throttled=0x1\n"))
    result = system_info._power_health()
    assert result["status"] == "critical"
    assert result["flags"]["under_voltage_now"] is True


def test_power_health_handles_missing_vcgencmd(monkeypatch):
    def missing(*args, **kwargs):
        raise OSError("missing")
    monkeypatch.setattr(system_info.subprocess, "run", missing)
    assert system_info._power_health() == {"available": False, "status": "unknown"}
