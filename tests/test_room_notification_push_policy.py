"""Room alert quiet-hours and no-alert-flap checks."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.room_notifications import NotificationPolicy, ThresholdRule, in_quiet_hours, update_alert_state

BERLIN = ZoneInfo("Europe/Berlin")


def test_quiet_hours_cross_midnight():
    p = NotificationPolicy(quiet_hours_start="22:00", quiet_hours_end="07:00")
    assert in_quiet_hours(p, now=datetime(2026, 11, 15, 23, 10, tzinfo=BERLIN))
    assert in_quiet_hours(p, now=datetime(2026, 11, 16, 6, 59, tzinfo=BERLIN))
    assert not in_quiet_hours(p, now=datetime(2026, 11, 16, 7, 1, tzinfo=BERLIN))


def test_quiet_hours_disabled_and_bad_configuration():
    from pydantic import ValidationError
    assert not in_quiet_hours(NotificationPolicy())
    for start, end in (("25:00", "06:00"), ("22:00", None)):
        try:
            NotificationPolicy(quiet_hours_start=start, quiet_hours_end=end)
        except ValidationError:
            pass
        else:
            raise AssertionError("Invalid quiet-hours policy accepted")


def test_sustained_threshold_and_recovery_emit_once():
    rule = ThresholdRule(metric="humidity_percent", maximum=70, hysteresis=4,
                         min_duration_seconds=60)
    state, event = update_alert_state(rule, 72, {}, now=100)
    assert event is None
    state, event = update_alert_state(rule, 72, state, now=161)
    assert event and event["kind"] == "threshold_high"
    state, event = update_alert_state(rule, 69, state, now=200)
    assert event is None
    state, event = update_alert_state(rule, 65, state, now=210)
    assert event is None
    state, event = update_alert_state(rule, 65, state, now=271)
    assert event and event["kind"] == "recovered"
