"""Room-specific light/fan automation plans, validated but NOT armed.

Separate this from app.automation (FRITZ! outlet scheduler). This module
stores a device-independent desired state only; no BLE, MQTT or relay commands
are issued before the actuator adapter/safety interlocks are implemented.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.room_sharing import _require_owner, _room_exists

router = APIRouter(prefix="/api/v1/room-control-plans", tags=["room-controls"])
DATA_FILE = Path(os.getenv("GC_ROOM_CONTROL_PLANS_FILE", "/var/lib/135er-grow-central/room-control-plans.json"))


class LightPlan(BaseModel):
    mode: Literal["off", "schedule"] = "off"
    on_at: str = "06:00"
    off_at: str = "00:00"
    brightness_percent: int = Field(default=50, ge=10, le=100)
    # A minimum off-time avoids rapid switching due to clock or network faults.
    min_switch_gap_seconds: int = Field(default=120, ge=60, le=3600)

    @model_validator(mode="after")
    def validate_schedule(self):
        for item in (self.on_at, self.off_at):
            try:
                parsed = datetime.strptime(item, "%H:%M")
            except ValueError as exc:
                raise ValueError("time must be HH:MM") from exc
            if parsed.strftime("%H:%M") != item:
                raise ValueError("time must be HH:MM")
        if self.on_at == self.off_at and self.mode == "schedule":
            raise ValueError("a scheduled light must have an off period")
        return self


class FanPlan(BaseModel):
    mode: Literal["off", "constant", "humidity_above", "temperature_above"] = "off"
    base_speed_percent: int = Field(default=25, ge=25, le=100)
    boost_speed_percent: int = Field(default=70, ge=25, le=100)
    temperature_above_c: float = Field(default=28, ge=0, le=55)
    humidity_above_percent: float = Field(default=70, ge=0, le=100)
    hysteresis_temperature_c: float = Field(default=1.0, ge=0.5, le=10)
    hysteresis_humidity_percent: float = Field(default=5, ge=2, le=20)
    min_switch_gap_seconds: int = Field(default=180, ge=60, le=3600)
    stale_sensor_policy: Literal["manual_hold", "base_speed"] = "manual_hold"

    @model_validator(mode="after")
    def validate_speeds(self):
        if self.boost_speed_percent < self.base_speed_percent:
            raise ValueError("boost speed must be at least base speed")
        return self


class RoomControlPlan(BaseModel):
    light: LightPlan = Field(default_factory=LightPlan)
    fan: FanPlan = Field(default_factory=FanPlan)
    enabled: bool = False


def light_desired(plan: LightPlan, *, minute: str) -> dict:
    """Pure dry-run schedule, including intervals that cross midnight."""
    if plan.mode == "off":
        return {"on": False, "brightness_percent": 0}
    a, b = plan.on_at, plan.off_at
    active = (a <= minute < b) if a < b else (minute >= a or minute < b)
    return {"on": active, "brightness_percent": plan.brightness_percent if active else 0}


def fan_desired(plan: FanPlan, *, temperature: float | None, humidity: float | None, was_boosted: bool) -> dict:
    """Pure hysteresis evaluation. An absent sensor does not trigger a boost."""
    if plan.mode == "off":
        return {"on": False, "speed_percent": 0, "reason": "disabled"}
    if plan.mode == "constant":
        return {"on": True, "speed_percent": plan.base_speed_percent, "reason": "constant"}
    if plan.mode == "temperature_above":
        value, threshold, gap = temperature, plan.temperature_above_c, plan.hysteresis_temperature_c
    else:
        value, threshold, gap = humidity, plan.humidity_above_percent, plan.hysteresis_humidity_percent
    if value is None:
        return {"on": True, "speed_percent": plan.base_speed_percent if plan.stale_sensor_policy == "base_speed" else None,
                "reason": "sensor_unavailable_manual_hold" if plan.stale_sensor_policy == "manual_hold" else "sensor_unavailable_base"}
    boost = value >= (threshold-gap if was_boosted else threshold)
    return {"on": True, "speed_percent": plan.boost_speed_percent if boost else plan.base_speed_percent,
            "reason": "threshold_boost" if boost else "base"}


def preview_from_sample(
    plan: RoomControlPlan,
    sample: dict,
    *,
    now: datetime | None = None,
    max_sensor_age_seconds: float = 120,
) -> dict:
    """Simulate a plan with *fresh* room telemetry. Never issue a device command."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include timezone")
    sample_time = None
    try:
        sample_time = datetime.fromisoformat(str(sample.get("timestamp", "")).replace("Z", "+00:00"))
        if sample_time.tzinfo is None:
            sample_time = None
    except ValueError:
        pass
    age = (now - sample_time).total_seconds() if sample_time else None
    fresh = age is not None and 0 <= age <= max_sensor_age_seconds

    def sensor(name: str) -> float | None:
        value = sample.get(name) if fresh else None
        if type(value) not in (int, float):
            return None
        import math
        return float(value) if math.isfinite(value) else None

    minute = now.astimezone(ZoneInfo("Europe/Berlin")).strftime("%H:%M")
    return {
        "light": light_desired(plan.light, minute=minute),
        "fan": fan_desired(plan.fan, temperature=sensor("temperature_c"),
                           humidity=sensor("humidity_percent"), was_boosted=False),
        "sensor_fresh": bool(fresh),
        "sensor_age_seconds": round(age, 1) if fresh else None,
        "sample_timestamp": sample.get("timestamp") if fresh else None,
        "control_enabled_in_config": plan.enabled,
        "execution": "simulation_only_no_device_command",
        "notice": "Hysteresis preview assumes fan was not previously boosted; live actuation disabled",
    }



def evaluate_actuation_safety(
    plan: RoomControlPlan,
    sample: dict,
    *,
    device_status: dict | None = None,
    last_switch_at: dict[str, datetime] | None = None,
    manual_override: bool = False,
    now: datetime | None = None,
) -> dict:
    """Pure safety evaluation. It never sends commands or grants actuation.

    Unknown actuator feedback, stale sensor samples and an operator override
    must be visible blockers, not guessed states. Time is handled as aware UTC
    instants, so repeated/skipped local DST hours do not defeat min-switch gaps.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    preview = preview_from_sample(plan, sample, now=now)
    devices = device_status or {}
    changed = last_switch_at or {}
    items = {}
    for kind, desired in (("light", preview["light"]), ("fan", preview["fan"])):
        blockers = []
        if not plan.enabled:
            blockers.append("plan_not_enabled")
        if manual_override:
            blockers.append("manual_override")
        if not preview["sensor_fresh"]:
            # Light schedules can be previewed without sensors; never command
            # equipment until the full local-health gate is verified.
            blockers.append("room_sample_stale_or_unavailable")
        status = devices.get(kind)
        if not isinstance(status, dict) or not status.get("fresh") or type(status.get("power_on")) is not bool:
            blockers.append("actuator_state_unconfirmed")
        if kind == "fan" and desired.get("speed_percent") is None:
            blockers.append("sensor_policy_manual_hold")
        last = changed.get(kind)
        if last is not None:
            if not isinstance(last, datetime) or last.tzinfo is None:
                blockers.append("last_switch_time_invalid")
            else:
                elapsed = (now - last).total_seconds()
                minimum = plan.light.min_switch_gap_seconds if kind == "light" else plan.fan.min_switch_gap_seconds
                if elapsed < 0 or elapsed < minimum:
                    blockers.append("minimum_switch_gap_or_clock_regression")
        else:
            blockers.append("switch_history_unknown")
        items[kind] = {
            "desired": desired,
            "safe_to_simulate": not blockers,
            "blocked_by": blockers,
            "actuation_allowed": False,
            "action": "dry_run_only",
        }
    return {"execution": "simulation_only_no_device_command", "devices": items,
            "manual_override": manual_override, "sensor_fresh": preview["sensor_fresh"]}


def _load() -> dict:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "Invalid room automation store") from exc
    if not isinstance(value, dict):
        raise HTTPException(500, "Invalid room automation store")
    return value


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    fd, filename = tempfile.mkstemp(dir=DATA_FILE.parent, prefix=".control-plans-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True)
            stream.flush(); os.fsync(stream.fileno())
        os.chmod(filename, 0o600)
        os.replace(filename, DATA_FILE)
    finally:
        Path(filename).unlink(missing_ok=True)


@router.get("/{room_id}")
async def get_plan(room_id: str, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    return {"room_id": room_id, "plan": _load().get(room_id, RoomControlPlan().model_dump()),
            "execution": "simulation_only_not_armed"}


@router.put("/{room_id}")
async def save_plan(room_id: str, plan: RoomControlPlan, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    # Even if user requests enabled, no physical automation is armed by this API.
    data = _load()
    data[room_id] = plan.model_dump()
    _save(data)
    return {"room_id": room_id, "plan": data[room_id], "execution": "simulation_only_not_armed"}


@router.post("/{room_id}/preview")
async def preview_plan(room_id: str, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    plan = RoomControlPlan.model_validate(_load().get(room_id, {}))
    from app.rooms import load_state, _latest_sensor_snapshot
    sample = _latest_sensor_snapshot(load_state(), room_id)
    return {"room_id": room_id, **preview_from_sample(plan, sample),
            "safety_interlocks": evaluate_actuation_safety(plan, sample)}
