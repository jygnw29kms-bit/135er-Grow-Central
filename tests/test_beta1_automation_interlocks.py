"""Automation Beta 1.0: pure fail-safe guards, never energize live equipment."""
from datetime import datetime, timedelta, timezone

from app.room_control_plans import (
    RoomControlPlan, LightPlan, FanPlan, evaluate_actuation_safety,
)


NOW = datetime(2026, 11, 16, 18, 0, tzinfo=timezone.utc)


def configured_plan():
    return RoomControlPlan(
        enabled=True,
        light=LightPlan(mode="schedule", on_at="06:00", off_at="23:00", brightness_percent=50),
        fan=FanPlan(mode="humidity_above", humidity_above_percent=65,
                    base_speed_percent=25, boost_speed_percent=75),
    )


def telemetry():
    return {"timestamp": (NOW - timedelta(seconds=10)).isoformat(),
            "temperature_c": 25, "humidity_percent": 75}


def devices():
    return {"light": {"fresh": True, "power_on": True},
            "fan": {"fresh": True, "power_on": True}}


def previous():
    return {"light": NOW - timedelta(minutes=10),
            "fan": NOW - timedelta(minutes=10)}


def test_no_actuation_even_when_all_interlocks_are_green():
    result = evaluate_actuation_safety(configured_plan(), telemetry(),
                                       device_status=devices(), last_switch_at=previous(), now=NOW)
    assert result["sensor_fresh"]
    for dev in result["devices"].values():
        assert dev["safe_to_simulate"] is True
        assert dev["actuation_allowed"] is False
        assert dev["action"] == "dry_run_only"


def test_manual_override_blocks_both_paths():
    result = evaluate_actuation_safety(configured_plan(), telemetry(), device_status=devices(),
                                       last_switch_at=previous(), manual_override=True, now=NOW)
    assert all("manual_override" in d["blocked_by"] for d in result["devices"].values())


def test_unknown_ble_or_untrusted_sensor_cannot_energize_actuators():
    old = {"timestamp": (NOW - timedelta(minutes=25)).isoformat(), "humidity_percent": 80}
    result = evaluate_actuation_safety(configured_plan(), old, device_status={"fan": {"fresh": False}},
                                       last_switch_at=previous(), now=NOW)
    assert "room_sample_stale_or_unavailable" in result["devices"]["light"]["blocked_by"]
    assert "actuator_state_unconfirmed" in result["devices"]["fan"]["blocked_by"]
    assert "sensor_policy_manual_hold" in result["devices"]["fan"]["blocked_by"]
    assert all(x["actuation_allowed"] is False for x in result["devices"].values())


def test_minimum_gap_and_clock_regression_block_in_utc():
    recent = {"light": NOW - timedelta(seconds=5), "fan": NOW + timedelta(minutes=2)}
    result = evaluate_actuation_safety(configured_plan(), telemetry(), device_status=devices(),
                                       last_switch_at=recent, now=NOW)
    assert all("minimum_switch_gap_or_clock_regression" in d["blocked_by"]
               for d in result["devices"].values())


def test_unknown_last_switch_history_is_not_invented():
    result = evaluate_actuation_safety(configured_plan(), telemetry(),
                                       device_status=devices(), now=NOW)
    assert all("switch_history_unknown" in d["blocked_by"] for d in result["devices"].values())


def test_plan_disabled_requires_explicit_authorization():
    plan = configured_plan().model_copy(update={"enabled": False})
    result = evaluate_actuation_safety(plan, telemetry(), device_status=devices(),
                                       last_switch_at=previous(), now=NOW)
    assert all("plan_not_enabled" in d["blocked_by"] for d in result["devices"].values())
