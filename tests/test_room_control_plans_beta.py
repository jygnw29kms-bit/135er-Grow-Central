"""Beta room automation plan dry-run tests, no physical device writes."""
import pytest
from pydantic import ValidationError

from app.room_control_plans import LightPlan, FanPlan, RoomControlPlan, light_desired, fan_desired


def test_light_cycle_handles_midnight():
    plan = LightPlan(mode="schedule", on_at="18:00", off_at="06:00", brightness_percent=60)
    assert light_desired(plan, minute="23:45") == {"on": True, "brightness_percent": 60}
    assert light_desired(plan, minute="05:59")["on"] is True
    assert light_desired(plan, minute="06:00")["on"] is False
    assert light_desired(plan, minute="12:00")["on"] is False


def test_light_rejects_bad_times_and_no_dark_period():
    for values in ({"on_at": "24:10"}, {"on_at": "06:00", "off_at": "06:00"}):
        with pytest.raises(ValidationError):
            LightPlan(mode="schedule", **values)


def test_fan_hysteresis_and_missing_sensor():
    plan = FanPlan(mode="humidity_above", humidity_above_percent=65, hysteresis_humidity_percent=5,
                   base_speed_percent=25, boost_speed_percent=75)
    assert fan_desired(plan, temperature=None, humidity=66, was_boosted=False)["speed_percent"] == 75
    assert fan_desired(plan, temperature=None, humidity=62, was_boosted=True)["speed_percent"] == 75
    assert fan_desired(plan, temperature=None, humidity=59, was_boosted=True)["speed_percent"] == 25
    assert fan_desired(plan, temperature=None, humidity=None, was_boosted=True)["speed_percent"] is None


def test_plans_are_never_armed_by_default():
    plan = RoomControlPlan()
    assert plan.enabled is False
    assert plan.light.mode == "off"
    assert plan.fan.mode == "off"


def test_fan_disallows_invalid_boost_speed():
    with pytest.raises(ValidationError):
        FanPlan(base_speed_percent=80, boost_speed_percent=30)
