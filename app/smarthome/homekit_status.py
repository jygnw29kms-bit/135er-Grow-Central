"""Local-first HomeKit publication diagnostics for Grow Central.

This module deliberately does not make the cloud a dependency of HomeKit.
It provides stable accessory identifiers, Apple-Home-compatible service mapping,
and a small persistent status registry that the local bridge/export worker can
update while the UI can inspect the exact publication state.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.security import require_write_auth

router = APIRouter(prefix="/homekit", tags=["homekit"])

STATE_PATH = Path(os.getenv("GC_HOMEKIT_STATUS_FILE", "/var/lib/grow-central/homekit-publications.json"))
ACCESSORY_NAMESPACE = uuid.UUID("71e9a7ba-7b04-4bd6-989f-0bed43ce99b8")

# Apple Home has no dedicated soil-moisture tile. We export the percentage via
# a HumiditySensor service, but retain the Grow-Central semantic type so the UI
# can label it explicitly as Bodenfeuchte instead of air humidity.
HOMEKIT_SERVICE_MAP = {
    "temperature": {"service": "TemperatureSensor", "characteristic": "CurrentTemperature", "unit": "°C"},
    "temperature_c": {"service": "TemperatureSensor", "characteristic": "CurrentTemperature", "unit": "°C"},
    "soil_temperature": {"service": "TemperatureSensor", "characteristic": "CurrentTemperature", "unit": "°C"},
    "humidity": {"service": "HumiditySensor", "characteristic": "CurrentRelativeHumidity", "unit": "%"},
    "humidity_percent": {"service": "HumiditySensor", "characteristic": "CurrentRelativeHumidity", "unit": "%"},
    "soil_moisture": {"service": "HumiditySensor", "characteristic": "CurrentRelativeHumidity", "unit": "%", "semantic": "soil_moisture"},
    "on": {"service": "Switch", "characteristic": "On", "unit": None},
}

PublicationState = Literal["disabled", "pending", "published", "error"]


class PublicationReport(BaseModel):
    device_id: str = Field(min_length=1, max_length=160)
    metric: str = Field(min_length=1, max_length=80)
    room: str | None = Field(default=None, max_length=120)
    enabled: bool = True
    state: PublicationState = "pending"
    detail: str | None = Field(default=None, max_length=500)


def stable_accessory_id(device_id: str, metric: str) -> str:
    return str(uuid.uuid5(ACCESSORY_NAMESPACE, f"{device_id}:{metric}"))


def service_mapping(metric: str) -> dict:
    mapping = HOMEKIT_SERVICE_MAP.get(metric)
    if not mapping:
        raise KeyError(metric)
    return dict(mapping)


def _read() -> dict:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": 1, "publications": {}}
    except (OSError, json.JSONDecodeError):
        return {"schema": 1, "publications": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("publications"), dict):
        return {"schema": 1, "publications": {}}
    return payload


def _write(payload: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="homekit-", suffix=".json", dir=str(STATE_PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATE_PATH)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _key(device_id: str, metric: str) -> str:
    return f"{device_id}::{metric}"


@router.get("/capabilities")
def capabilities():
    return {
        "schema": 1,
        "local_first": True,
        "cloud_required": False,
        "stable_accessory_ids": True,
        "metrics": HOMEKIT_SERVICE_MAP,
        "states": ["disabled", "pending", "published", "error"],
    }


@router.get("/status")
def status():
    payload = _read()
    rows = list(payload["publications"].values())
    return {
        "schema": 1,
        "summary": {
            "total": len(rows),
            "published": sum(1 for row in rows if row.get("state") == "published"),
            "pending": sum(1 for row in rows if row.get("state") == "pending"),
            "errors": sum(1 for row in rows if row.get("state") == "error"),
        },
        "publications": sorted(rows, key=lambda row: (row.get("device_id", ""), row.get("metric", ""))),
    }


@router.post("/status", dependencies=[Depends(require_write_auth)])
def report(body: PublicationReport):
    try:
        mapping = service_mapping(body.metric)
    except KeyError as exc:
        raise HTTPException(422, f"unsupported HomeKit metric: {body.metric}") from exc

    payload = _read()
    timestamp = datetime.now(timezone.utc).isoformat()
    row = {
        "device_id": body.device_id,
        "metric": body.metric,
        "room": body.room,
        "enabled": body.enabled,
        "state": "disabled" if not body.enabled else body.state,
        "detail": body.detail,
        "accessory_id": stable_accessory_id(body.device_id, body.metric),
        "service": mapping["service"],
        "characteristic": mapping["characteristic"],
        "unit": mapping.get("unit"),
        "semantic": mapping.get("semantic", body.metric),
        "updated_at": timestamp,
    }
    payload["publications"][_key(body.device_id, body.metric)] = row
    _write(payload)
    append_audit(
        "homekit.publication.status",
        device_id=body.device_id,
        metric=body.metric,
        state=row["state"],
        room=body.room,
    )
    return {"ok": True, "publication": row}
