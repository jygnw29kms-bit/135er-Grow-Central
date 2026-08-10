"""135er-Grow Central Cloud API.

DE:
    Optionaler VServer-Dienst für Telemetrie, Historie und eine vorbereitete
    Remote-Command-Queue. Er ersetzt niemals die lokale Raspberry-Pi-Steuerung.

EN:
    Optional VPS service for telemetry, history and a prepared remote-command
    queue. It never replaces the local Raspberry Pi control node.
"""
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

BASE = Path(__file__).resolve().parents[1]
WEB = BASE / "web"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="135er-Grow Central Cloud", version="0.7.1", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB), name="static")


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


def check_token(x_api_token: str | None):
    """Fail closed until a sufficiently strong cloud token is configured."""
    expected = settings.cloud_api_token.strip()
    if len(expected) < 32 or expected.startswith("CHANGE_ME"):
        raise HTTPException(503, "cloud authentication is not configured")
    candidate = (x_api_token or "").strip()
    if not candidate or not secrets.compare_digest(candidate, expected):
        raise HTTPException(401, "invalid api token", headers={"WWW-Authenticate": "Bearer"})


@app.get("/")
async def index():
    """DE: Cloud-UI ausliefern. EN: Serve the cloud UI."""
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
async def health():
    """DE: Öffentlicher Healthcheck. EN: Public health check."""
    return {"ok": True, "service": "135er-Grow Central Cloud", "version": "0.7.1"}


@app.post("/api/v1/telemetry")
async def telemetry(payload: TelemetryPayload, x_api_token: str | None = Header(default=None)):
    """DE: Telemetrie vom Pi speichern. EN: Store telemetry received from a Pi."""
    check_token(x_api_token)
    extra_json = json.dumps(payload.extra, separators=(",", ":"))
    if len(extra_json.encode("utf-8")) > 16_384:
        raise HTTPException(413, "telemetry extra payload too large")
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO telemetry
            (ts,site_id,device_id,temperature_c,humidity_pct,vpd_kpa,fan_speed_pct,device_online,extra_json)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                payload.ts.isoformat(), payload.site_id, payload.device_id,
                payload.temperature_c, payload.humidity_pct,
                payload.vpd_kpa, payload.fan_speed_pct,
                1 if payload.device_online else 0,
                extra_json,
            ),
        )
        await db.commit()
    return {"ok": True}


@app.get("/api/v1/sites/{site_id}/latest")
async def latest(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    x_api_token: str | None = Header(default=None),
):
    """DE: Letzten Standortwert liefern. EN: Return latest telemetry for a site."""
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM telemetry WHERE site_id=? ORDER BY id DESC LIMIT 1",
            (site_id,),
        )
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
    """DE: Begrenzte Historie liefern. EN: Return bounded telemetry history."""
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM telemetry WHERE site_id=? ORDER BY id DESC LIMIT ?",
            (site_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/commands")
async def create_command(payload: CommandPayload, x_api_token: str | None = Header(default=None)):
    """DE: Remote-Befehl nur bei Server-Freigabe anlegen.
    EN: Queue a remote command only when server-side commands are enabled.
    """
    check_token(x_api_token)
    if not settings.cloud_allow_commands:
        raise HTTPException(403, "remote commands are disabled")
    command_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO commands(id,site_id,target,action,value_json,created_at,status)
               VALUES(?,?,?,?,?,?,?)""",
            (
                command_id, payload.site_id, payload.target, payload.action,
                json.dumps(payload.value), created, "pending",
            ),
        )
        await db.commit()
    return {"id": command_id, "status": "pending"}


@app.get("/api/v1/sites/{site_id}/commands/pending")
async def pending(
    site_id: str = ApiPath(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
    x_api_token: str | None = Header(default=None),
):
    """DE: Offene Befehle für einen Standort liefern.
    EN: Return pending commands for a site.
    """
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM commands WHERE site_id=? AND status='pending' ORDER BY created_at LIMIT 20",
            (site_id,),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/commands/{command_id}/result")
async def command_result(command_id: uuid.UUID, payload: CommandResultPayload, x_api_token: str | None = Header(default=None)):
    """DE: Ergebnis der lokalen Prüfung speichern. EN: Store local command result."""
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        cursor = await db.execute(
            "UPDATE commands SET status=?, result_json=? WHERE id=?",
            (
                "done" if payload.ok else "failed",
                payload.model_dump_json(),
                str(command_id),
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "unknown command")
        await db.commit()
    return {"ok": True}
