"""Room alarm rules, deduplication and an on-device event inbox.

Web Push is a separate delivery adapter: creating an event is NOT claiming an
iPhone received a notification. No default Mars-Hydro offline alarm when the
user has intentionally disconnected that hardware.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.room_sharing import _require_owner, _room_exists
from app.rooms import load_state

router = APIRouter(prefix="/api/v1/room-notifications", tags=["room-notifications"])
DATA_FILE = Path(os.getenv("GC_ROOM_NOTIFICATION_FILE", "/var/lib/135er-grow-central/room-notifications.json"))
MAX_EVENTS = 500
METRICS = {
    "temperature_c": (0.0, 60.0),
    "humidity_percent": (0.0, 100.0),
    "soil_moisture_percent": (0.0, 100.0),
}


class ThresholdRule(BaseModel):
    metric: Literal["temperature_c", "humidity_percent", "soil_moisture_percent"]
    minimum: float | None = None
    maximum: float | None = None
    hysteresis: float = Field(default=2, ge=0.1, le=20)
    min_duration_seconds: int = Field(default=120, ge=30, le=3600)
    cooldown_seconds: int = Field(default=1800, ge=300, le=86400)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_bounds(self):
        lo, hi = METRICS[self.metric]
        if self.minimum is None and self.maximum is None:
            raise ValueError("at least one bound required")
        for val in (self.minimum, self.maximum):
            if val is not None and not lo <= val <= hi:
                raise ValueError("bound outside measurement range")
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("minimum must be below maximum")
        return self


class NotificationPolicy(BaseModel):
    rules: list[ThresholdRule] = Field(default_factory=list, max_length=16)
    sensor_offline_after_seconds: int = Field(default=900, ge=300, le=86400)
    notify_sensor_offline: bool = False
    notify_cloud_channel_offline: bool = False
    notify_mars_offline: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    push_enabled: bool = False  # Never set as delivered without a registered subscription.


def classify(rule: ThresholdRule, value: float | None, previous: str = "normal") -> str:
    """Hysteresis prevents one-reading alarm flapping."""
    if value is None:
        return "unknown"
    if rule.minimum is not None:
        clear_at = rule.minimum + rule.hysteresis
        if value < (clear_at if previous == "low" else rule.minimum):
            return "low"
    if rule.maximum is not None:
        clear_at = rule.maximum - rule.hysteresis
        if value > (clear_at if previous == "high" else rule.maximum):
            return "high"
    return "normal"


def update_alert_state(rule: ThresholdRule, value: float | None, row: dict, *, now: float) -> tuple[dict, dict | None]:
    """Produce one alert on sustained excursion, then an eventual recovery."""
    old = row.get("state", "normal")
    detected = classify(rule, value, old)
    state = dict(row)
    if detected == "unknown":
        state["candidate"] = None
        return state, None
    if detected != state.get("candidate"):
        state["candidate"] = detected
        state["candidate_since"] = now
    if detected == old or now - state.get("candidate_since", now) < rule.min_duration_seconds:
        return state, None
    state["state"] = detected
    event = {"kind": "recovered" if detected == "normal" else "threshold_" + detected,
             "metric": rule.metric, "value": value, "at": datetime.fromtimestamp(now, timezone.utc).isoformat()}
    # Do not suppress the first transition or a recovery. Repeated values in
    # the same state do not create repeated events.
    state["last_event_at"] = now
    return state, event


def _load() -> dict:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"policies": {}, "states": {}, "events": []}
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "Notification store invalid") from exc
    if not isinstance(value, dict):
        raise HTTPException(500, "Notification store invalid")
    return {"policies": value.get("policies", {}), "states": value.get("states", {}), "events": value.get("events", [])}


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    fd, filename = tempfile.mkstemp(dir=DATA_FILE.parent, prefix=".room-notification-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        os.chmod(filename, 0o600)
        os.replace(filename, DATA_FILE)
    finally:
        Path(filename).unlink(missing_ok=True)


def _latest_sample(state: dict, room_id: str) -> dict:
    return next((row for row in reversed(state.get("sensor_history", [])) if row.get("room_id") == room_id), {})


def poll_once(*, now: float | None = None, store: dict | None = None, room_state: dict | None = None) -> list[dict]:
    """Evaluate configured room thresholds and queue inbox events, never send Push."""
    now = time.time() if now is None else now
    data = _load() if store is None else store
    rooms = load_state() if room_state is None else room_state
    emitted: list[dict] = []
    for room_id, raw in data.get("policies", {}).items():
        if not any(r["id"] == room_id for r in rooms.get("rooms", [])):
            continue
        policy = NotificationPolicy.model_validate(raw)
        sample = _latest_sample(rooms, room_id)
        age = None
        try:
            stamp = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
            age = now - stamp.timestamp()
        except (KeyError, TypeError, ValueError):
            pass
        fresh = age is not None and 0 <= age <= policy.sensor_offline_after_seconds
        for index, rule in enumerate(policy.rules):
            if not rule.enabled:
                continue
            key = f"{room_id}:{index}:{rule.metric}"
            state = data.setdefault("states", {}).get(key, {})
            metric = sample.get(rule.metric)
            if rule.metric == "soil_moisture_percent" and sample.get("soil_calibration_status") != "valid":
                metric = None
            value = float(metric) if fresh and type(metric) in (float, int) else None
            state, event = update_alert_state(rule, value, state, now=now)
            data["states"][key] = state
            if event:
                event = {**event, "room_id": room_id, "rule_index": index, "delivery": "in_app_pending"}
                emitted.append(event)
        # Stale readings are handled as a dedicated, explicit opt-in alert.
        if policy.notify_sensor_offline:
            key = f"{room_id}:sensor_offline"
            previous = data.setdefault("states", {}).get(key, {}).get("offline", False)
            offline = not fresh
            if offline != previous:
                data["states"][key] = {"offline": offline}
                if not previous and offline:
                    emitted.append({"room_id": room_id, "kind": "sensor_offline",
                                    "at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                                    "delivery": "in_app_pending"})
    data.setdefault("events", []).extend(emitted)
    data["events"] = data["events"][-MAX_EVENTS:]
    if store is None:
        _save(data)
    return emitted


@router.get("/{room_id}")
async def notification_state(room_id: str, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    data = _load()
    return {"room_id": room_id, "policy": data["policies"].get(room_id, NotificationPolicy().model_dump()),
            "events": [event for event in data["events"] if event.get("room_id") == room_id][-100:],
            "push_delivery": "not_configured_subscriptions_required"}


@router.put("/{room_id}")
async def save_policy(room_id: str, policy: NotificationPolicy, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    data = _load()
    data["policies"][room_id] = policy.model_dump()
    _save(data)
    return {"room_id": room_id, "policy": policy.model_dump(), "delivery": "in_app_only_until_webpush_subscribed"}


# Evaluate configured alert rules locally, independently of optional cloud access.
# No push send is attempted without a specific device subscription and consent.
_notification_task = None


async def _notification_loop() -> None:
    import asyncio
    import logging
    log = logging.getLogger(__name__)
    while True:
        try:
            # Avoid creating empty database files for installations with no policy.
            if DATA_FILE.exists():
                poll_once()
        except Exception:
            log.exception("room notification evaluation failed")
        await asyncio.sleep(60)


def install(app) -> None:
    import asyncio

    async def start():
        global _notification_task
        if _notification_task is None or _notification_task.done():
            _notification_task = asyncio.create_task(_notification_loop(), name="room-notification-evaluator")

    async def stop():
        global _notification_task
        task, _notification_task = _notification_task, None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app.router.add_event_handler("startup", start)
    app.router.add_event_handler("shutdown", stop)
