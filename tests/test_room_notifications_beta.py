"""Threshold, hysteresis, freshness and notification-inbox tests."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.room_notifications import ThresholdRule, NotificationPolicy, classify, update_alert_state, poll_once


def test_hysteresis_does_not_flap():
    rule = ThresholdRule(metric="humidity_percent", minimum=40, maximum=70, hysteresis=3)
    assert classify(rule, 39, "normal") == "low"
    assert classify(rule, 41, "low") == "low"
    assert classify(rule, 43, "low") == "normal"
    assert classify(rule, 71, "normal") == "high"
    assert classify(rule, 68, "high") == "high"
    assert classify(rule, 67, "high") == "normal"


def test_minimum_duration_and_recovery():
    rule = ThresholdRule(metric="soil_moisture_percent", minimum=30, min_duration_seconds=120)
    state, event = update_alert_state(rule, 20, {}, now=1000)
    assert event is None
    state, event = update_alert_state(rule, 20, state, now=1119)
    assert event is None
    state, event = update_alert_state(rule, 20, state, now=1120)
    assert event["kind"] == "threshold_low"
    state, event = update_alert_state(rule, 20, state, now=1300)
    assert event is None
    state, event = update_alert_state(rule, 40, state, now=1301)
    assert event is None
    state, event = update_alert_state(rule, 40, state, now=1421)
    assert event["kind"] == "recovered"


def test_missing_data_cannot_trigger_threshold_alert():
    rule = ThresholdRule(metric="temperature_c", maximum=30)
    state, event = update_alert_state(rule, None, {}, now=1000)
    assert event is None
    assert state["candidate"] is None


def test_invalid_rule_settings_are_rejected():
    with pytest.raises(ValidationError):
        ThresholdRule(metric="humidity_percent", minimum=90, maximum=50)
    with pytest.raises(ValidationError):
        ThresholdRule(metric="soil_moisture_percent")


def test_explicit_opt_in_and_inbox_only():
    at = datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc).timestamp()
    data = {"policies": {"room_test": NotificationPolicy(rules=[
        ThresholdRule(metric="soil_moisture_percent", maximum=70, min_duration_seconds=60)
    ]).model_dump()}, "states": {}, "events": []}
    rooms = {"rooms": [{"id": "room_test"}], "sensor_history": [{
        "room_id": "room_test", "timestamp": datetime.fromtimestamp(at,timezone.utc).isoformat(),
        "soil_moisture_percent": 88.8, "soil_calibration_status": "valid",
    }]}
    assert poll_once(store=data, room_state=rooms, now=at) == []
    events = poll_once(store=data, room_state=rooms, now=at+61)
    assert len(events) == 1
    assert events[0]["delivery"] == "in_app_pending"
    assert poll_once(store=data, room_state=rooms, now=at+62) == []


def test_mars_disconnect_is_not_alarm_by_default():
    assert NotificationPolicy().notify_mars_offline is False
    assert NotificationPolicy().notify_cloud_channel_offline is False
    assert NotificationPolicy().push_enabled is False


def test_cloud_disconnect_requires_sustained_outage_and_reports_recovery():
    from app.room_notifications import connection_transition
    state = {}
    state, event = connection_transition("cloud", False, state, now=1000, minimum_down_seconds=300)
    assert event is None
    state, event = connection_transition("cloud", False, state, now=1299, minimum_down_seconds=300)
    assert event is None
    state, event = connection_transition("cloud", False, state, now=1300, minimum_down_seconds=300)
    assert event == "connection_offline"
    state, event = connection_transition("cloud", False, state, now=2000, minimum_down_seconds=300)
    assert event is None
    state, event = connection_transition("cloud", True, state, now=2001, minimum_down_seconds=300)
    assert event == "connection_recovered"
    state, event = connection_transition("cloud", None, state, now=2002, minimum_down_seconds=300)
    assert event is None


def test_cloud_offline_alarm_requires_room_policy_opt_in():
    from app.room_notifications import poll_once
    store = {"policies": {"room_test": NotificationPolicy(
        notify_cloud_channel_offline=True, connection_min_down_seconds=60
    ).model_dump()}, "states": {}, "events": []}
    rooms = {"rooms": [{"id": "room_test"}], "sensor_history": []}
    assert poll_once(now=1000, store=store, room_state=rooms, connections={"cloud": False}) == []
    events = poll_once(now=1060, store=store, room_state=rooms, connections={"cloud": False})
    assert len(events) == 1
    assert events[0]["kind"] == "connection_offline"
    assert events[0]["source"] == "cloud"


def test_mars_offline_only_for_explicitly_assigned_room_devices():
    from app.room_notifications import poll_once
    policy = NotificationPolicy(notify_mars_offline=True, connection_min_down_seconds=60)
    store = {"policies": {"room_1": policy.model_dump(), "room_2": policy.model_dump()},
             "states": {}, "events": []}
    rooms = {"rooms": [{"id": "room_1"}, {"id": "room_2"}],
             "assignments": {"mars-hydro:fc3000": "room_1"}, "sensor_history": []}
    assert poll_once(now=1000, store=store, room_state=rooms,
                     connections={"mars_lamp": False, "mars_fan": False}) == []
    events = poll_once(now=1061, store=store, room_state=rooms,
                       connections={"mars_lamp": False, "mars_fan": False})
    assert len(events) == 1
    assert events[0]["room_id"] == "room_1"
    assert events[0]["source"] == "mars_lamp"
