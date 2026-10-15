"""Persistent local automation definitions using the appliance credential store.

FRITZ! routines remain owned by the FRITZ!Box. Grow Central stores only local
rule definitions; their actions reuse the separately encrypted FRITZ! login.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.credential_store import get_provider_config
from app.security import require_write_auth
from app.smarthome.adapters.fritz import FritzAhaClient

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])
DATA_FILE = Path(os.getenv("GC_AUTOMATIONS_FILE", "/opt/135er-grow-central/data/automations.json"))
RUNTIME_FILE = Path(os.getenv("GC_AUTOMATION_RUNTIME_FILE", "/var/lib/135er-grow-central/automation-runtime.json"))
LOCAL_TZ = ZoneInfo(os.getenv("GC_TIMEZONE", "Europe/Berlin"))
_scheduler_task: asyncio.Task | None = None


class AutomationDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    trigger: str = Field(pattern=r"^(manual|time|temperature_above|temperature_below)$")
    trigger_value: str = Field(default="", max_length=32)
    device_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    ain: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9 _.-]+$")
    on: bool
    enabled: bool = True


def _load() -> list[dict]:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Automationsdatei ist beschädigt oder nicht lesbar") from exc
    return value if isinstance(value, list) else []


def _save(rows: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".automations-", dir=DATA_FILE.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, DATA_FILE)
    finally:
        Path(temporary).unlink(missing_ok=True)



def _validate_definition(definition: AutomationDefinition) -> None:
    if definition.trigger == "time" and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", definition.trigger_value):
        raise HTTPException(422, "Uhrzeit muss HH:MM entsprechen")
    if definition.trigger in {"temperature_above", "temperature_below"}:
        try:
            value = float(definition.trigger_value)
        except ValueError as exc:
            raise HTTPException(422, "Temperatur-Trigger ben?tigt einen Zahlenwert") from exc
        if not -30 <= value <= 80:
            raise HTTPException(422, "Temperatur-Trigger au?erhalb des erlaubten Bereichs")


def _runtime_load() -> dict:
    try:
        value = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {"last_runs": {}}
    return value if isinstance(value, dict) else {"last_runs": {}}


def _runtime_save(value: dict) -> None:
    RUNTIME_FILE.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".automation-runtime-", dir=RUNTIME_FILE.parent)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o640)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        if not hasattr(os, "fchmod"):
            os.chmod(temporary, 0o640)
        os.replace(temporary, RUNTIME_FILE)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _runtime_mark(automation_id: str, *, key: str, source: str, ok: bool | None, error: str = "") -> None:
    state = _runtime_load(); runs = state.setdefault("last_runs", {})
    runs[automation_id] = {"key": key, "source": source, "ok": ok, "error": error[:240], "at": datetime.now(timezone.utc).isoformat()}
    _runtime_save(state)


async def _execute(row: dict, *, source: str) -> dict:
    config = get_provider_config("fritz") or {}
    username = str(config.get("username") or "").strip(); password = str(config.get("password") or "")
    host = str(config.get("host") or "fritz.box").strip()
    if not username or not password:
        raise RuntimeError("FRITZ!-Zugang ist nicht eingerichtet")
    ain = str(row.get("ain") or "").strip()
    if not ain:
        raise RuntimeError("Automation hat keine AIN")
    requested = bool(row.get("on"))
    client = FritzAhaClient(host, username, password)
    append_audit("automation.execution.started", automation_id=row.get("id"), source=source, device_id=row.get("device_id"), on=requested)
    result = await client.command("setswitchon" if requested else "setswitchoff", ain)
    if result not in {"0", "1"}:
        raise RuntimeError("FRITZ!Box meldet keinen g?ltigen Schaltzustand")
    observed = await client.command("getswitchstate", ain)
    expected = "1" if requested else "0"
    if observed != expected:
        raise RuntimeError("FRITZ!-Schaltzustand wurde nicht best?tigt")
    append_audit("automation.execution.succeeded", automation_id=row.get("id"), source=source, device_id=row.get("device_id"), on=requested)
    return {"ok": True, "automation_id": row.get("id"), "on": requested, "confirmed": True}


async def _scheduler_tick(now: datetime | None = None) -> int:
    now = now or datetime.now(LOCAL_TZ)
    minute = now.strftime("%H:%M"); run_key = f"{now.date().isoformat()}T{minute}"
    rows = _load(); runtime = _runtime_load().get("last_runs", {})
    attempted = 0
    for row in rows:
        if not row.get("enabled", True) or row.get("trigger") != "time" or row.get("trigger_value") != minute:
            continue
        automation_id = str(row.get("id") or "")
        if not automation_id or (runtime.get(automation_id) or {}).get("key") == run_key:
            continue
        attempted += 1
        # Mark the minute before executing. A failing rule is not retried every 15 seconds.
        _runtime_mark(automation_id, key=run_key, source="scheduler", ok=None)
        try:
            await _execute(row, source="scheduler")
        except Exception as exc:
            _runtime_mark(automation_id, key=run_key, source="scheduler", ok=False, error=f"{type(exc).__name__}: {exc}")
            append_audit("automation.execution.failed", automation_id=automation_id, source="scheduler", error=type(exc).__name__)
        else:
            _runtime_mark(automation_id, key=run_key, source="scheduler", ok=True)
    return attempted


async def _scheduler_loop() -> None:
    while True:
        try:
            await _scheduler_tick()
        except Exception as exc:
            append_audit("automation.scheduler.error", error=type(exc).__name__)
        await asyncio.sleep(15)


def install(app) -> None:
    @app.on_event("startup")
    async def _automation_startup() -> None:
        global _scheduler_task
        if _scheduler_task is None or _scheduler_task.done():
            _scheduler_task = asyncio.create_task(_scheduler_loop(), name="growcentral-automation-scheduler")

    @app.on_event("shutdown")
    async def _automation_shutdown() -> None:
        global _scheduler_task
        task = _scheduler_task; _scheduler_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@router.get("")
async def list_automations():
    return {"automations": _load(), "execution_policy": "stored_fritz_credentials",
            "execution_status": "time_and_manual", "automatic_triggers": ["time"], "stored_only_triggers": ["temperature_above", "temperature_below"]}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_automation(definition: AutomationDefinition):
    _validate_definition(definition)
    rows = _load()
    next_number = max((int(row.get("id", "gc-0").split("-")[-1]) for row in rows if re.fullmatch(r"gc-\d+", str(row.get("id", "")))), default=0) + 1
    row = {"id": f"gc-{next_number}", **definition.model_dump()}
    rows.append(row)
    _save(rows)
    append_audit("automation.created", automation_id=row["id"], trigger=row["trigger"], device_id=row["device_id"])
    return {"ok": True, "automation": row, "execution_policy": "stored_fritz_credentials"}


@router.get("/runtime")
async def automation_runtime():
    return {"scheduler": "running" if _scheduler_task is not None and not _scheduler_task.done() else "stopped", **_runtime_load()}


@router.post("/{automation_id}/run", dependencies=[Depends(require_write_auth)])
async def run_automation(automation_id: str):
    if not re.fullmatch(r"gc-\d+", automation_id):
        raise HTTPException(422, "Ung?ltige Automations-ID")
    row = next((item for item in _load() if item.get("id") == automation_id), None)
    if row is None:
        raise HTTPException(404, "Automation nicht gefunden")
    key = "manual:" + datetime.now(timezone.utc).isoformat()
    try:
        result = await _execute(row, source="manual")
    except Exception as exc:
        _runtime_mark(automation_id, key=key, source="manual", ok=False, error=f"{type(exc).__name__}: {exc}")
        append_audit("automation.execution.failed", automation_id=automation_id, source="manual", error=type(exc).__name__)
        raise HTTPException(502, f"Automation konnte nicht best?tigt ausgef?hrt werden ({type(exc).__name__})") from None
    _runtime_mark(automation_id, key=key, source="manual", ok=True)
    return result


@router.delete("/{automation_id}", dependencies=[Depends(require_write_auth)])
async def delete_automation(automation_id: str):
    if not re.fullmatch(r"gc-\d+", automation_id):
        raise HTTPException(422, "Ungültige Automations-ID")
    rows = _load()
    remaining = [row for row in rows if row.get("id") != automation_id]
    if len(remaining) == len(rows):
        raise HTTPException(404, "Automation nicht gefunden")
    _save(remaining)
    append_audit("automation.deleted", automation_id=automation_id)
    return {"ok": True}
