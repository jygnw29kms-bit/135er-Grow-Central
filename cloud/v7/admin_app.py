"""135er Grow Central Cloud V7 admin and entitlement sidecar.

Runs next to the proven V6 cloud core and uses the SAME DATABASE_URL.
This makes V6 -> V7 upgrades non-destructive: accounts, devices, pairings,
sessions and device identities stay in place while administration evolves.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_TOKEN = os.environ.get("CLOUD_ADMIN_TOKEN", "").strip()
ADMIN_MODE = os.environ.get("CLOUD_ADMIN_MODE", "standalone").strip()
MAX_DEVICES = int(os.environ.get("CLOUD_MAX_DEVICES", "1000"))
OFFLINE_AFTER = int(os.environ.get("CLOUD_OFFLINE_AFTER_SECONDS", "120"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)

app = FastAPI(title="135er Grow Central Cloud Admin", version="7.0", docs_url=None, redoc_url=None)

FEATURES = (
    "remote_control", "camera", "history_extended", "alerts",
    "automation_pro", "api_access", "beta_features",
)
PLANS = {"BASIC", "PLUS", "PRO", "INTERNAL"}
STATES = {"pending", "active", "blocked", "expired"}


def now() -> int:
    return int(time.time())


def admin_auth(x_growcentral_admin: str | None) -> None:
    if len(ADMIN_TOKEN) < 32:
        raise HTTPException(503, "admin token not configured")
    candidate = (x_growcentral_admin or "").strip()
    if not candidate or not secrets.compare_digest(candidate, ADMIN_TOKEN):
        raise HTTPException(401, "invalid admin token")


def init_schema() -> None:
    schema = [
        """CREATE TABLE IF NOT EXISTS device_entitlements(
             device_id VARCHAR(36) PRIMARY KEY,
             customer VARCHAR(200),
             device_group VARCHAR(120),
             state VARCHAR(20) NOT NULL DEFAULT 'pending',
             plan VARCHAR(20) NOT NULL DEFAULT 'BASIC',
             valid_until BIGINT,
             notes TEXT,
             remote_control INTEGER NOT NULL DEFAULT 0,
             camera INTEGER NOT NULL DEFAULT 0,
             history_extended INTEGER NOT NULL DEFAULT 0,
             alerts INTEGER NOT NULL DEFAULT 0,
             automation_pro INTEGER NOT NULL DEFAULT 0,
             api_access INTEGER NOT NULL DEFAULT 0,
             beta_features INTEGER NOT NULL DEFAULT 0,
             created_at BIGINT NOT NULL,
             updated_at BIGINT NOT NULL
           )""",
        "CREATE INDEX IF NOT EXISTS idx_device_entitlements_state ON device_entitlements(state)",
        "CREATE INDEX IF NOT EXISTS idx_device_entitlements_customer ON device_entitlements(customer)",
    ]
    with engine.begin() as con:
        for stmt in schema:
            con.execute(text(stmt))
        # Import already paired V6 devices as pending without touching identity data.
        rows = con.execute(text("SELECT id FROM devices")).mappings().all()
        t = now()
        for row in rows:
            exists = con.execute(text("SELECT device_id FROM device_entitlements WHERE device_id=:d"), {"d": row["id"]}).first()
            if not exists:
                con.execute(text(
                    "INSERT INTO device_entitlements(device_id,state,plan,created_at,updated_at) "
                    "VALUES(:d,'pending','BASIC',:t,:t)"
                ), {"d": row["id"], "t": t})


init_schema()


class EntitlementUpdate(BaseModel):
    customer: str | None = Field(default=None, max_length=200)
    device_group: str | None = Field(default=None, max_length=120)
    state: str = "pending"
    plan: str = "BASIC"
    valid_until: int | None = None
    notes: str | None = Field(default=None, max_length=4000)
    features: dict[str, bool] = Field(default_factory=dict)


def effective(row: dict[str, Any]) -> dict[str, Any]:
    state = row["state"]
    valid_until = row.get("valid_until")
    if valid_until and int(valid_until) <= now():
        state = "expired"
    enabled = state == "active"
    features = {name: bool(row.get(name)) and enabled for name in FEATURES}
    return {
        "device_id": row["device_id"],
        "state": state,
        "plan": row["plan"],
        "valid_until": valid_until,
        "features": features,
    }


@app.get("/health")
def health():
    with engine.begin() as con:
        total = con.execute(text("SELECT COUNT(*) FROM devices")).scalar_one()
        licensed = con.execute(text("SELECT COUNT(*) FROM device_entitlements WHERE state='active'")).scalar_one()
    return {"ok": True, "version": 7, "admin_mode": ADMIN_MODE, "devices": total, "active": licensed, "soft_limit": MAX_DEVICES}


@app.get("/api/admin/devices")
def list_devices(
    q: str = Query(default="", max_length=120),
    x_growcentral_admin: str | None = Header(default=None),
):
    admin_auth(x_growcentral_admin)
    init_schema()
    needle = f"%{q.strip()}%"
    sql = """SELECT d.id,d.name,d.hardware_guid,d.account_id,d.created_at,d.last_seen,d.revoked_at,
                    e.customer,e.device_group,e.state,e.plan,e.valid_until,e.notes,
                    e.remote_control,e.camera,e.history_extended,e.alerts,e.automation_pro,e.api_access,e.beta_features
             FROM devices d JOIN device_entitlements e ON e.device_id=d.id
             WHERE (:q='' OR d.id LIKE :needle OR d.name LIKE :needle OR d.hardware_guid LIKE :needle
                    OR COALESCE(e.customer,'') LIKE :needle OR COALESCE(e.device_group,'') LIKE :needle)
             ORDER BY d.created_at DESC LIMIT 2000"""
    with engine.begin() as con:
        rows = [dict(r) for r in con.execute(text(sql), {"q": q.strip(), "needle": needle}).mappings().all()]
    t = now()
    for row in rows:
        row["online"] = bool(row.get("last_seen") and t - int(row["last_seen"]) <= OFFLINE_AFTER)
        row["effective"] = effective(row)
    return rows


@app.put("/api/admin/devices/{device_id}")
def update_device(device_id: str, body: EntitlementUpdate, x_growcentral_admin: str | None = Header(default=None)):
    admin_auth(x_growcentral_admin)
    state = body.state.upper() if False else body.state.lower()
    plan = body.plan.upper()
    if state not in STATES:
        raise HTTPException(422, "invalid state")
    if plan not in PLANS:
        raise HTTPException(422, "invalid plan")
    values = {name: 1 if body.features.get(name, False) else 0 for name in FEATURES}
    values.update({
        "d": device_id, "customer": body.customer, "group": body.device_group,
        "state": state, "plan": plan, "valid": body.valid_until,
        "notes": body.notes, "updated": now(),
    })
    sets = ",".join(f"{name}=:{name}" for name in FEATURES)
    with engine.begin() as con:
        if not con.execute(text("SELECT id FROM devices WHERE id=:d"), {"d": device_id}).first():
            raise HTTPException(404, "unknown device")
        con.execute(text(
            f"UPDATE device_entitlements SET customer=:customer,device_group=:group,state=:state,plan=:plan,"
            f"valid_until=:valid,notes=:notes,{sets},updated_at=:updated WHERE device_id=:d"
        ), values)
        row = dict(con.execute(text("SELECT * FROM device_entitlements WHERE device_id=:d"), {"d": device_id}).mappings().one())
    return effective(row)


@app.get("/api/admin/stats")
def stats(x_growcentral_admin: str | None = Header(default=None)):
    admin_auth(x_growcentral_admin)
    init_schema()
    with engine.begin() as con:
        total = con.execute(text("SELECT COUNT(*) FROM devices")).scalar_one()
        pending = con.execute(text("SELECT COUNT(*) FROM device_entitlements WHERE state='pending'")).scalar_one()
        active = con.execute(text("SELECT COUNT(*) FROM device_entitlements WHERE state='active'")).scalar_one()
        blocked = con.execute(text("SELECT COUNT(*) FROM device_entitlements WHERE state='blocked'")).scalar_one()
    return {"total": total, "pending": pending, "active": active, "blocked": blocked, "soft_limit": MAX_DEVICES}


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    if ADMIN_MODE not in {"standalone", "both"}:
        raise HTTPException(404)
    return """<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>135er Grow Central Cloud</title><style>
body{font-family:system-ui;background:#071018;color:#e8f2f5;margin:0}header{padding:24px;background:#0c1a24;border-bottom:1px solid #29404b}.wrap{max-width:1200px;margin:auto;padding:22px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card,table{background:#0d1b25;border:1px solid #29404b;border-radius:12px}.card{padding:16px}input,button,select{background:#122630;color:#e8f2f5;border:1px solid #395561;border-radius:8px;padding:9px}table{width:100%;border-collapse:collapse;margin-top:18px}td,th{padding:10px;border-bottom:1px solid #203640;text-align:left}.muted{color:#8fa7b2}@media(max-width:800px){.cards{grid-template-columns:1fr 1fr}}</style></head><body><header><b>135er Grow Central Cloud · Administration V7</b></header><div class='wrap'><p>Standalone-Administration ist installiert. API-Zugriffe erfordern den lokalen Admin-Token aus <code>/etc/135er-growcentral-cloud/cloud.env</code>.</p><div class='cards'><div class='card'>Geräte<br><b id='total'>–</b></div><div class='card'>Pending<br><b id='pending'>–</b></div><div class='card'>Aktiv<br><b id='active'>–</b></div><div class='card'>Gesperrt<br><b id='blocked'>–</b></div></div><p class='muted'>Die vollständige editierbare Oberfläche wird über dieselbe Admin-API bedient; Plesk nutzt exakt dieselbe Datenbasis.</p></div></body></html>"""
