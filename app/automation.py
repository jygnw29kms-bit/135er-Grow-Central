"""Persistent local automation definitions using the appliance credential store.

FRITZ! routines remain owned by the FRITZ!Box. Grow Central stores only local
rule definitions; their actions reuse the separately encrypted FRITZ! login.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])
DATA_FILE = Path(os.getenv("GC_AUTOMATIONS_FILE", "/opt/135er-grow-central/data/automations.json"))


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


@router.get("")
async def list_automations():
    return {"automations": _load(), "execution_policy": "stored_fritz_credentials"}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_automation(definition: AutomationDefinition):
    rows = _load()
    next_number = max((int(row.get("id", "gc-0").split("-")[-1]) for row in rows if re.fullmatch(r"gc-\d+", str(row.get("id", "")))), default=0) + 1
    row = {"id": f"gc-{next_number}", **definition.model_dump()}
    rows.append(row)
    _save(rows)
    append_audit("automation.created", automation_id=row["id"], trigger=row["trigger"], device_id=row["device_id"])
    return {"ok": True, "automation": row, "execution_policy": "stored_fritz_credentials"}


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
