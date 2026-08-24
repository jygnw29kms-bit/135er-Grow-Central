"""135er-Grow Central Cloud API."""
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
import json
import secrets
import uuid
from typing import Any, Literal

import aiosqlite
from fastapi import FastAPI, Header, HTTPException, Path as ApiPath, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .db import init_db
from .diagnostics import router as diagnostics_router

BASE = Path(__file__).resolve().parents[1]
WEB = BASE / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="135er-Grow Central Cloud", version="0.7.1", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB), name="static")
app.include_router(diagnostics_router)


class TelemetryPayload(BaseModel):
    site_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    device_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")
    ts: datetime
    temperature_c: float | None = Field(default=None, ge=-50, le=100)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    vpd_kpa: float | None = Field(default=None, ge=0, le=20)
    fan_speed_pct: int | None = Field(default=None, ge=0, le=100)
    device_online: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


class CommandPayload(BaseModel):
    site_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    target: Literal["df100m"]
    action: Literal["set_speed"]
    value: int = Field(ge=0, le=100)


class CommandResultPayload(BaseModel):
    ok: bool
    message: str = Field(default="", max_length=500)
    ts: datetime


def _normal_token_ok(token: str | None) -> bool:
    expected = settings.cloud_api_token.strip()
    candidate = (token or "").strip()
    return len(expected) >= 32 and not expected.startswith("CHANGE_ME") and bool(candidate) and secrets.compare_digest(candidate, expected)


def check_token(x_api_token: str | None) -> None:
    if _normal_token_ok(x_api_token):
        return
    if len(settings.cloud_api_token.strip()) < 32:
        raise HTTPException(503, "cloud authentication is not configured")
    raise HTTPException(401, "invalid api token", headers={"WWW-Authenticate": "Bearer"})


def allow_closed_test_data(x_api_token: str | None, site_id: str, device_id: str | None = None) -> None:
    if _normal_token_ok(x_api_token):
        return
    if settings.cloud_closed_test_mode and site_id == settings.cloud_closed_test_site:
        if device_id is None or device_id.startswith("raspberry-pi-"):
            return
    raise HTTPException(403, "credential-free access is limited to the configured closed-test site")


@app.get("/")
async def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "135er-Grow Central Cloud",
        "version": "0.7.1",
        "closed_test_mode": settings.cloud_closed_test_mode,
        "remote_commands": settings.cloud_allow_commands,
    }


@app.post("/api/v1/telemetry")
async def telemetry(payload: TelemetryPayload, x_api_token: str | None = Header(default=None)):
    allow_closed_test_data(x_api_token, payload.site_id, payload.device_id)
    extra_json = json.dumps(payload.extra, separators=(",", ":"))
    if len(extra_json.encode("utf-8")) > 16_384:
        raise HTTPException(413, "telemetry extra payload too large")
    retention = max(1000, int(settings.cloud_telemetry_retention_rows))
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO telemetry
            (ts,site_id,device_id,temperature_c,humidity_pct,vpd_kpa,fan_speed_pct,device_online,extra_json)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                payload.ts.isoformat(), payload.site_id, payload.device_id,
                payload.temperature_c, payload.humidity_pct, payload.vpd_kpa,
                payload.fan_speed_pct, 1 if payload.device_online else 0, extra_json,
            ),
        )
        # Keep public test traffic bounded even if the endpoint is discovered.
        await db.execute(
            "DELETE FROM telemetry WHERE id NOT IN (SELECT id FROM telemetry ORDER BY id DESC LIMIT ?)",
            (retention,),
        )
        await db.commit()
    return {"ok": True, "closed_test_mode": settings.cloud_closed_test_mode}


@app.get("/api/v1/sites/{site_id}/latest")
async def latest(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    x_api_token: str | None = Header(default=None),
):
    allow_closed_test_data(x_api_token, site_id)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM telemetry WHERE site_id=? ORDER BY id DESC LIMIT 1", (site_id,))
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "no telemetry")
    return dict(row)


@app.get("/api/v1/sites/{site_id}/history")
async def history(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    limit: int = Query(default=200, ge=1, le=2000),
    x_api_token: str | None = Header(default=None),
):
    allow_closed_test_data(x_api_token, site_id)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM telemetry WHERE site_id=? ORDER BY id DESC LIMIT ?", (site_id, limit))
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/commands")
async def create_command(payload: CommandPayload, x_api_token: str | None = Header(default=None)):
    check_token(x_api_token)
    if not settings.cloud_allow_commands:
        raise HTTPException(403, "remote commands are disabled")
    command_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            "INSERT INTO commands(id,site_id,target,action,value_json,created_at,status) VALUES(?,?,?,?,?,?,?)",
            (command_id, payload.site_id, payload.target, payload.action, json.dumps(payload.value), created, "pending"),
        )
        await db.commit()
    return {"id": command_id, "status": "pending"}


@app.get("/api/v1/sites/{site_id}/commands/pending")
async def pending(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    x_api_token: str | None = Header(default=None),
):
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM commands WHERE site_id=? AND status='pending' ORDER BY created_at LIMIT 20", (site_id,)
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/commands/{command_id}/result")
async def command_result(
    command_id: uuid.UUID,
    payload: CommandResultPayload,
    x_api_token: str | None = Header(default=None),
):
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        cursor = await db.execute(
            "UPDATE commands SET status=?, result_json=? WHERE id=?",
            ("done" if payload.ok else "failed", payload.model_dump_json(), str(command_id)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "unknown command")
        await db.commit()
    return {"ok": True}
