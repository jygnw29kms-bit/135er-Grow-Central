"""Safe, persistent grow recipe definitions.

Recipes are declarative only: they do not write to devices. Applying recipes to
actuators remains a separate, validated automation concern.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])
DATA_FILE = Path(os.getenv("GC_RECIPES_FILE", "/var/lib/135er-grow-central/recipes.json"))


class RecipeDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phase: str = Field(pattern=r"^(germination|vegetative|flowering|flush|harvest|other)$")
    target_temperature_c: float | None = Field(default=None, ge=0, le=60)
    target_humidity_percent: float | None = Field(default=None, ge=0, le=100)
    target_vpd_kpa: float | None = Field(default=None, ge=0, le=5)
    light_cycle: str = Field(default="", max_length=32)
    watering_note: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=3000)


def _load() -> list[dict]:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Rezeptdatei ist beschädigt oder nicht lesbar") from exc
    if not isinstance(data, list):
        raise HTTPException(500, "Rezeptdatei ist ungültig")
    return [row for row in data if isinstance(row, dict)]


def _save(rows: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".recipes-", dir=DATA_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.chmod(temp, 0o640)
        os.replace(temp, DATA_FILE)
    finally:
        Path(temp).unlink(missing_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_recipes():
    return {"recipes": _load(), "execution_status": "declarative_only"}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_recipe(body: RecipeDefinition):
    rows = _load(); now = _now()
    row = {"id": "recipe_" + uuid.uuid4().hex[:12], **body.model_dump(), "created_at": now, "updated_at": now}
    rows.append(row); _save(rows)
    append_audit("recipe.created", recipe_id=row["id"], phase=row["phase"])
    return {"ok": True, "recipe": row}


@router.put("/{recipe_id}", dependencies=[Depends(require_write_auth)])
async def update_recipe(recipe_id: str, body: RecipeDefinition):
    rows = _load(); row = next((r for r in rows if r.get("id") == recipe_id), None)
    if not row: raise HTTPException(404, "Rezept nicht gefunden")
    row.update(body.model_dump()); row["updated_at"] = _now(); _save(rows)
    append_audit("recipe.updated", recipe_id=recipe_id, phase=row["phase"])
    return {"ok": True, "recipe": row}


@router.delete("/{recipe_id}", dependencies=[Depends(require_write_auth)])
async def delete_recipe(recipe_id: str):
    rows = _load(); remaining = [r for r in rows if r.get("id") != recipe_id]
    if len(remaining) == len(rows): raise HTTPException(404, "Rezept nicht gefunden")
    _save(remaining); append_audit("recipe.deleted", recipe_id=recipe_id)
    return {"ok": True}
