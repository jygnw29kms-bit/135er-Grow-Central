"""Local-first grow photo journal for Grow Central.

Photos are stored as files next to the existing local Grow-Central data while all
metadata continues to live in the canonical rooms.json state. No second database
or cloud service is introduced.
"""
from __future__ import annotations

import base64
import binascii
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.security import require_write_auth
from app import rooms

router = APIRouter(prefix="/api/v1/grow-photos", tags=["grow-photos"])
PHOTO_DIR = Path(os.getenv("GC_GROW_PHOTO_DIR", "/var/lib/135er-grow-central/grow-photos"))
MAX_PHOTO_BYTES = max(512 * 1024, int(os.getenv("GC_GROW_PHOTO_MAX_BYTES", str(8 * 1024 * 1024))))

_IMAGE_TYPES = {
    "jpeg": ("jpg", "image/jpeg"),
    "jpg": ("jpg", "image/jpeg"),
    "png": ("png", "image/png"),
    "webp": ("webp", "image/webp"),
}


class GrowPhotoCreate(BaseModel):
    room_id: str = Field(min_length=1, max_length=128)
    plant_id: str | None = Field(default=None, max_length=128)
    title: str = Field(default="Foto", min_length=1, max_length=120)
    note: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    image_data_url: str = Field(min_length=32, max_length=12_000_000)


def _decode_image(data_url: str) -> tuple[bytes, str, str]:
    if not data_url.startswith("data:image/") or ";base64," not in data_url:
        raise HTTPException(415, "Nur JPEG, PNG oder WebP als Bilddatei erlaubt")
    header, encoded = data_url.split(",", 1)
    subtype = header[11:].split(";", 1)[0].lower()
    mapping = _IMAGE_TYPES.get(subtype)
    if not mapping:
        raise HTTPException(415, "Nur JPEG, PNG oder WebP als Bilddatei erlaubt")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(400, "Ungültige Bilddaten") from exc
    if not raw:
        raise HTTPException(400, "Leere Bilddatei")
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(413, f"Bild ist größer als {MAX_PHOTO_BYTES // (1024 * 1024)} MiB")

    ext, media_type = mapping
    valid = False
    if ext == "jpg":
        valid = raw.startswith(b"\xff\xd8\xff")
    elif ext == "png":
        valid = raw.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == "webp":
        valid = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    if not valid:
        raise HTTPException(415, "Bildinhalt passt nicht zum Dateityp")
    return raw, ext, media_type


def _cycle_day(plant: dict[str, Any] | None) -> int | None:
    if not plant:
        return None
    raw = str(plant.get("start_date") or "").strip()
    if not raw:
        return None
    try:
        started = date.fromisoformat(raw[:10])
    except ValueError:
        return None
    return max(1, (date.today() - started).days + 1)


def _find_photo_row(state: dict[str, Any], photo_id: str) -> dict[str, Any] | None:
    for key in ("room_journal", "plant_journal"):
        row = next((entry for entry in state[key] if entry.get("photo_id") == photo_id), None)
        if row:
            return row
    return None


def _photo_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [entry for entry in state["room_journal"] if entry.get("photo_id")]
    rows.extend(entry for entry in state["plant_journal"] if entry.get("photo_id"))
    rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
    return rows


def _store_photo(raw: bytes, photo_id: str, ext: str) -> Path:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(PHOTO_DIR, 0o700)
    target = PHOTO_DIR / f"{photo_id}.{ext}"
    fd, temp_name = tempfile.mkstemp(prefix=f".{photo_id}-", dir=PHOTO_DIR)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
        return target
    finally:
        Path(temp_name).unlink(missing_ok=True)


@router.get("")
async def list_grow_photos(
    room_id: str | None = Query(default=None, max_length=128),
    plant_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=1000),
):
    state = rooms.load_state()
    result = _photo_rows(state)
    if room_id:
        result = [row for row in result if row.get("room_id") == room_id]
    if plant_id:
        result = [row for row in result if row.get("plant_id") == plant_id]
    return {"photos": result[:limit]}


@router.post("", dependencies=[Depends(require_write_auth)])
async def create_grow_photo(body: GrowPhotoCreate):
    raw, ext, media_type = _decode_image(body.image_data_url)
    state = rooms.load_state()
    rooms.room_or_404(state, body.room_id)
    plant = None
    if body.plant_id:
        plant = rooms.plant_or_404(state, body.plant_id)
        if plant.get("room_id") != body.room_id:
            raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")

    photo_id = rooms.new_id("photo")
    target = _store_photo(raw, photo_id, ext)
    try:
        with rooms.edit_state() as current:
            rooms.room_or_404(current, body.room_id)
            plant = None
            if body.plant_id:
                plant = rooms.plant_or_404(current, body.plant_id)
                if plant.get("room_id") != body.room_id:
                    raise HTTPException(409, "Pflanze gehört zu einem anderen Raum")
            snapshot = rooms._latest_sensor_snapshot(current, body.room_id)
            clean_tags = list(dict.fromkeys(tag.strip()[:40] for tag in body.tags if tag.strip()))[:20]
            created_at = rooms.now_iso()
            row = {
                "id": rooms.new_id("entry"),
                "room_id": body.room_id,
                "plant_id": body.plant_id,
                "category": "photo",
                "title": body.title,
                "text": body.note,
                "tags": clean_tags,
                "photo_id": photo_id,
                "photo_url": f"/api/v1/grow-photos/{photo_id}",
                "photo_media_type": media_type,
                "photo_bytes": len(raw),
                "phase": plant.get("phase") if plant else None,
                "cycle_day": _cycle_day(plant),
                "sensor_snapshot": snapshot,
                "created_at": created_at,
            }
            if body.plant_id:
                current["plant_journal"].append(row)
            else:
                current["room_journal"].append(row)
            rooms._append_grow_event(
                current,
                body.room_id,
                plant_id=body.plant_id,
                event_type="photo",
                note=body.note or body.title,
                payload={
                    "journal_entry_id": row["id"],
                    "photo_id": photo_id,
                    "photo_url": row["photo_url"],
                    "tags": clean_tags,
                    "phase": row["phase"],
                    "cycle_day": row["cycle_day"],
                },
                source="photo-journal",
            )
            return row
    except Exception:
        target.unlink(missing_ok=True)
        raise


@router.get("/{photo_id}", include_in_schema=False)
async def get_grow_photo(photo_id: str):
    state = rooms.load_state()
    row = _find_photo_row(state, photo_id)
    if not row:
        raise HTTPException(404, "Foto nicht gefunden")
    media_type = str(row.get("photo_media_type") or "image/jpeg")
    suffix = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(media_type)
    if not suffix:
        raise HTTPException(404, "Foto nicht gefunden")
    path = PHOTO_DIR / f"{photo_id}.{suffix}"
    if not path.is_file():
        raise HTTPException(404, "Fotodatei fehlt")
    return FileResponse(path, media_type=media_type, headers={
        "Cache-Control": "private, max-age=3600",
        "X-Content-Type-Options": "nosniff",
    })


@router.delete("/{photo_id}", dependencies=[Depends(require_write_auth)])
async def delete_grow_photo(photo_id: str):
    with rooms.edit_state() as state:
        row = _find_photo_row(state, photo_id)
        if not row:
            raise HTTPException(404, "Foto nicht gefunden")
        state["room_journal"] = [entry for entry in state["room_journal"] if entry.get("photo_id") != photo_id]
        state["plant_journal"] = [entry for entry in state["plant_journal"] if entry.get("photo_id") != photo_id]
        state["grow_events"] = [
            event for event in state["grow_events"]
            if (event.get("payload") or {}).get("photo_id") != photo_id
        ]
        media_type = str(row.get("photo_media_type") or "image/jpeg")
    suffix = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(media_type)
    if suffix:
        (PHOTO_DIR / f"{photo_id}.{suffix}").unlink(missing_ok=True)
    return {"ok": True, "photo_id": photo_id}
