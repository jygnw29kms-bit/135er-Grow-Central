"""Invalid telemetry must never generate a misleading all-clear alert."""
from datetime import datetime, timezone

from app.room_notifications import (
    NotificationPolicy, ThresholdRule, classify, poll_once,
)


def test_nonfinite_alarm_values_are_unknown_not_recovery():
    rule = ThresholdRule(metric="humidity_percent", maximum=70, min_duration_seconds=30)
    for invalid in (float("nan"), float("inf"), -float("inf")):
        assert classify(rule, invalid, previous="high") == "unknown"


def test_nan_does_not_clear_active_alarm_in_poll():
    timestamp = datetime.fromtimestamp(1800000000, timezone.utc).isoformat()
    room_id = "room_test"
    policy = NotificationPolicy(rules=[ThresholdRule(
        metric="humidity_percent", maximum=70, min_duration_seconds=30)])
    state = {"policies": {room_id: policy.model_dump()},
             "states": {f"{room_id}:0:humidity_percent": {
                 "state": "high", "candidate": "high", "candidate_since": 1799999900}},
             "events": []}
    room_state = {"rooms": [{"id": room_id}], "assignments": {},
                  "sensor_history": [{"room_id": room_id, "timestamp": timestamp,
                                      "humidity_percent": float("nan")}]}
    events = poll_once(now=1800000000, store=state, room_state=room_state)
    assert events == []
    assert state["states"][f"{room_id}:0:humidity_percent"]["state"] == "high"


def test_quiet_hours_are_independent_of_bad_sensor_samples():
    from app.room_notifications import in_quiet_hours
    from zoneinfo import ZoneInfo
    policy = NotificationPolicy(quiet_hours_start="22:00", quiet_hours_end="07:00")
    berlin = datetime(2026, 11, 17, 23, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    assert in_quiet_hours(policy, now=berlin)
