"""Administrative API shared by standalone UI and the Plesk extension."""
from datetime import datetime, timezone
import secrets
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

FEATURES = (
    "remote_control",
    "camera",
    "history_extended",
    "alerts",
    "automation_pro",
    "api_access",
    "beta_features",
)


class DeviceUpsert(BaseModel):
    display_name: str = Field(default="", max_length=100)
    owner_name: str = Field(default="", max_length=120)
    group_name: str = Field(default="", max_length=80)
    status: Literal["pending", "active", "blocked", "expired"] = "pending"
    plan: Literal["BASIC", "PLUS", "PRO", "INTERNAL"] = "BASIC"
    valid_until: datetime | None = None
    notes: str = Field(default="", max_length=2000)
    features: dict[str, bool] = Field(default_factory=dict)


def _admin_ok(token: str | None) -> bool:
    expected = settings.cloud_admin_token.strip()
    candidate = (token or "").strip()
    return len(expected) >= 32 and bool(candidate) and secrets.compare_digest(candidate, expected)


def require_admin(x_admin_token: str | None) -> None:
    if len(settings.cloud_admin_token.strip()) < 32:
        raise HTTPException(503, "cloud admin token is not configured")
    if not _admin_ok(x_admin_token):
        raise HTTPException(401, "invalid admin token")


@router.get("/summary")
async def summary(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        counts = {}
        for state in ("pending", "active", "blocked", "expired"):
            cur = await db.execute("SELECT COUNT(*) AS c FROM managed_devices WHERE status=?", (state,))
            counts[state] = int((await cur.fetchone())["c"])
        cur = await db.execute("SELECT COUNT(*) AS c FROM managed_devices")
        counts["total"] = int((await cur.fetchone())["c"])
    return {
        "devices": counts,
        "max_devices": settings.cloud_max_devices,
        "heartbeat_seconds": settings.cloud_heartbeat_seconds,
        "offline_after_seconds": settings.cloud_offline_after_seconds,
        "admin_mode": settings.cloud_admin_mode,
        "features": list(FEATURES),
    }


@router.get("/devices")
async def list_devices(
    q: str = Query(default="", max_length=100),
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    pattern = f"%{q.strip()}%"
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM managed_devices
               WHERE ?='' OR device_id LIKE ? OR display_name LIKE ? OR owner_name LIKE ? OR group_name LIKE ?
               ORDER BY updated_at DESC LIMIT 500""",
            (q.strip(), pattern, pattern, pattern, pattern),
        )
        rows = await cur.fetchall()
        result = []
        for row in rows:
            device = dict(row)
            fcur = await db.execute("SELECT feature,enabled FROM device_features WHERE device_id=?", (row["device_id"],))
            device["features"] = {r["feature"]: bool(r["enabled"]) for r in await fcur.fetchall()}
            result.append(device)
    return result


@router.put("/devices/{device_id}")
async def upsert_device(
    device_id: str,
    payload: DeviceUpsert,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    if not device_id or len(device_id) > 128:
        raise HTTPException(422, "invalid device id")
    unknown = sorted(set(payload.features) - set(FEATURES))
    if unknown:
        raise HTTPException(422, f"unknown features: {', '.join(unknown)}")
    now = datetime.now(timezone.utc).isoformat()
    valid_until = payload.valid_until.isoformat() if payload.valid_until else None
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute(
            """INSERT INTO managed_devices
               (device_id,display_name,owner_name,group_name,status,plan,valid_until,notes,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                 display_name=excluded.display_name, owner_name=excluded.owner_name,
                 group_name=excluded.group_name, status=excluded.status, plan=excluded.plan,
                 valid_until=excluded.valid_until, notes=excluded.notes, updated_at=excluded.updated_at""",
            (device_id, payload.display_name, payload.owner_name, payload.group_name,
             payload.status, payload.plan, valid_until, payload.notes, now, now),
        )
        for feature in FEATURES:
            enabled = 1 if payload.features.get(feature, False) else 0
            await db.execute(
                """INSERT INTO device_features(device_id,feature,enabled) VALUES(?,?,?)
                   ON CONFLICT(device_id,feature) DO UPDATE SET enabled=excluded.enabled""",
                (device_id, feature, enabled),
            )
        await db.commit()
    return {"ok": True, "device_id": device_id}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        cur = await db.execute("DELETE FROM managed_devices WHERE device_id=?", (device_id,))
        await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "unknown device")
    return {"ok": True}


@router.get("/devices/{device_id}/entitlements")
async def entitlements(device_id: str, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM managed_devices WHERE device_id=?", (device_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "unknown device")
        fcur = await db.execute("SELECT feature,enabled FROM device_features WHERE device_id=?", (device_id,))
        features = {r["feature"]: bool(r["enabled"]) for r in await fcur.fetchall()}
    return {
        "device_id": device_id,
        "status": row["status"],
        "plan": row["plan"],
        "valid_until": row["valid_until"],
        "features": features,
    }
