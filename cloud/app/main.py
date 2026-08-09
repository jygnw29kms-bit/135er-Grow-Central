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
import json
import uuid

import aiosqlite
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db

BASE = Path(__file__).resolve().parents[1]
WEB = BASE / "web"

app = FastAPI(title="135er-Grow Central Cloud", version="0.7.1")
app.mount("/static", StaticFiles(directory=WEB), name="static")


def check_token(x_api_token: str | None):
    """DE: Einfacher Alpha-Tokencheck. EN: Simple alpha-stage token check."""
    if not x_api_token or x_api_token != settings.cloud_api_token:
        raise HTTPException(401, "invalid api token")


@app.on_event("startup")
async def startup():
    """DE: Datenbank initialisieren. EN: Initialize the database."""
    await init_db()


@app.get("/")
async def index():
    """DE: Cloud-UI ausliefern. EN: Serve the cloud UI."""
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
async def health():
    """DE: Öffentlicher Healthcheck. EN: Public health check."""
    return {"ok": True, "service": "135er-Grow Central Cloud", "version": "0.7.1"}


@app.post("/api/v1/telemetry")
async def telemetry(payload: dict, x_api_token: str | None = Header(default=None)):
    """DE: Telemetrie vom Pi speichern. EN: Store telemetry received from a Pi."""
    check_token(x_api_token)
    required = ("site_id", "device_id", "ts")
    if not all(key in payload for key in required):
        raise HTTPException(422, f"required: {required}")
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            """INSERT INTO telemetry
            (ts,site_id,device_id,temperature_c,humidity_pct,vpd_kpa,fan_speed_pct,device_online,extra_json)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                payload["ts"], payload["site_id"], payload["device_id"],
                payload.get("temperature_c"), payload.get("humidity_pct"),
                payload.get("vpd_kpa"), payload.get("fan_speed_pct"),
                1 if payload.get("device_online", True) else 0,
                json.dumps(payload.get("extra", {})),
            ),
        )
        await db.commit()
    return {"ok": True}


@app.get("/api/v1/sites/{site_id}/latest")
async def latest(site_id: str, x_api_token: str | None = Header(default=None)):
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
async def history(site_id: str, limit: int = 200, x_api_token: str | None = Header(default=None)):
    """DE: Begrenzte Historie liefern. EN: Return bounded telemetry history."""
    check_token(x_api_token)
    limit = max(1, min(limit, 2000))
    async with aiosqlite.connect(settings.cloud_db) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM telemetry WHERE site_id=? ORDER BY id DESC LIMIT ?",
            (site_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/commands")
async def create_command(payload: dict, x_api_token: str | None = Header(default=None)):
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
                command_id, payload["site_id"], payload["target"], payload["action"],
                json.dumps(payload.get("value")), created, "pending",
            ),
        )
        await db.commit()
    return {"id": command_id, "status": "pending"}


@app.get("/api/v1/sites/{site_id}/commands/pending")
async def pending(site_id: str, x_api_token: str | None = Header(default=None)):
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
async def command_result(command_id: str, payload: dict, x_api_token: str | None = Header(default=None)):
    """DE: Ergebnis der lokalen Prüfung speichern. EN: Store local command result."""
    check_token(x_api_token)
    async with aiosqlite.connect(settings.cloud_db) as db:
        await db.execute(
            "UPDATE commands SET status=?, result_json=? WHERE id=?",
            ("done" if payload.get("ok") else "failed", json.dumps(payload), command_id),
        )
        await db.commit()
    return {"ok": True}
