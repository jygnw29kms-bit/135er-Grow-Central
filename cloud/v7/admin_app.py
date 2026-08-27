"""135er Grow Central Cloud V7 admin and entitlement sidecar.

Runs next to the proven V6 cloud core and uses the SAME DATABASE_URL.
This makes V6 -> V7 upgrades non-destructive: accounts, devices, pairings,
sessions and Ed25519 device identities stay in place while administration evolves.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
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


def sha256s(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


class DeviceIdentity(BaseModel):
    device_id: str = Field(min_length=36, max_length=36)


class DeviceEntitlementProof(BaseModel):
    device_id: str = Field(min_length=36, max_length=36)
    nonce: str = Field(min_length=16, max_length=256)
    timestamp: int
    signature: str = Field(min_length=40, max_length=256)


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


def entitlement_row(device_id: str) -> dict[str, Any]:
    init_schema()
    with engine.begin() as con:
        row = con.execute(text("SELECT * FROM device_entitlements WHERE device_id=:d"), {"d": device_id}).mappings().first()
    if not row:
        raise HTTPException(404, "unknown device")
    return dict(row)


@app.get("/health")
def health():
    init_schema()
    with engine.begin() as con:
        total = con.execute(text("SELECT COUNT(*) FROM devices")).scalar_one()
        licensed = con.execute(text("SELECT COUNT(*) FROM device_entitlements WHERE state='active'")).scalar_one()
    return {"ok": True, "version": 7, "admin_mode": ADMIN_MODE, "devices": total, "active": licensed, "soft_limit": MAX_DEVICES}


@app.get("/api/admin/devices")
def list_devices(q: str = Query(default="", max_length=120), x_growcentral_admin: str | None = Header(default=None)):
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
    state = body.state.lower()
    plan = body.plan.upper()
    if state not in STATES:
        raise HTTPException(422, "invalid state")
    if plan not in PLANS:
        raise HTTPException(422, "invalid plan")
    values = {
        "d": device_id,
        "customer": body.customer,
        "group": body.device_group,
        "state": state,
        "plan": plan,
        "valid": body.valid_until,
        "notes": body.notes,
        "updated": now(),
        "remote_control": 1 if body.features.get("remote_control", False) else 0,
        "camera": 1 if body.features.get("camera", False) else 0,
        "history_extended": 1 if body.features.get("history_extended", False) else 0,
        "alerts": 1 if body.features.get("alerts", False) else 0,
        "automation_pro": 1 if body.features.get("automation_pro", False) else 0,
        "api_access": 1 if body.features.get("api_access", False) else 0,
        "beta_features": 1 if body.features.get("beta_features", False) else 0,
    }
    update_sql = text("""
        UPDATE device_entitlements
           SET customer=:customer,
               device_group=:group,
               state=:state,
               plan=:plan,
               valid_until=:valid,
               notes=:notes,
               remote_control=:remote_control,
               camera=:camera,
               history_extended=:history_extended,
               alerts=:alerts,
               automation_pro=:automation_pro,
               api_access=:api_access,
               beta_features=:beta_features,
               updated_at=:updated
         WHERE device_id=:d
    """)
    with engine.begin() as con:
        if not con.execute(text("SELECT id FROM devices WHERE id=:d"), {"d": device_id}).first():
            raise HTTPException(404, "unknown device")
        con.execute(update_sql, values)
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


@app.post("/api/v7/device/entitlements/challenge")
def entitlement_challenge(body: DeviceIdentity):
    t = now()
    nonce = secrets.token_urlsafe(32)
    with engine.begin() as con:
        row = con.execute(text(
            "SELECT id FROM devices WHERE id=:d AND account_id IS NOT NULL AND revoked_at IS NULL"
        ), {"d": body.device_id}).first()
        if not row:
            raise HTTPException(404, "device not found")
        con.execute(text(
            "INSERT INTO device_nonces(nonce_hash,device_id,created_at,expires_at,used_at) VALUES(:h,:d,:c,:e,NULL)"
        ), {"h": sha256s(nonce), "d": body.device_id, "c": t, "e": t + 60})
    return {"nonce": nonce, "expires_in": 60, "signature_format": "GCLOUD2"}


@app.post("/api/v7/device/entitlements")
def device_entitlements(body: DeviceEntitlementProof):
    t = now()
    if abs(t - body.timestamp) > 60:
        raise HTTPException(401, "stale device proof")
    nh = sha256s(body.nonce)
    with engine.begin() as con:
        nonce_row = con.execute(text(
            "SELECT device_id FROM device_nonces WHERE nonce_hash=:h AND device_id=:d AND expires_at>:t AND used_at IS NULL"
        ), {"h": nh, "d": body.device_id, "t": t}).mappings().first()
        if not nonce_row:
            raise HTTPException(401, "invalid or consumed nonce")
        device = con.execute(text(
            "SELECT public_key,revoked_at FROM devices WHERE id=:d AND account_id IS NOT NULL"
        ), {"d": body.device_id}).mappings().first()
        if not device or device["revoked_at"] is not None:
            raise HTTPException(403, "device revoked")
        signed = f"GCLOUD2\n{body.device_id}\n{body.nonce}\n{body.timestamp}".encode("utf-8")
        try:
            pub = str(device["public_key"])
            pub_raw = base64.urlsafe_b64decode(pub + "=" * (-len(pub) % 4))
            sig_raw = base64.urlsafe_b64decode(body.signature + "=" * (-len(body.signature) % 4))
            Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig_raw, signed)
        except Exception as exc:
            raise HTTPException(401, "invalid device signature") from exc
        result = con.execute(text(
            "UPDATE device_nonces SET used_at=:t WHERE nonce_hash=:h AND used_at IS NULL"
        ), {"t": t, "h": nh})
        if result.rowcount != 1:
            raise HTTPException(409, "nonce already consumed")
        con.execute(text("UPDATE devices SET last_seen=:t WHERE id=:d"), {"t": t, "d": body.device_id})
    payload = effective(entitlement_row(body.device_id))
    payload["server_time"] = t
    payload["entitlement_version"] = 1
    return payload


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    if ADMIN_MODE not in {"standalone", "both"}:
        raise HTTPException(404)
    return """<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>135er Grow Central Cloud</title><style>body{font-family:system-ui;background:#071018;color:#e8f2f5;margin:0}header{padding:24px;background:#0c1a24;border-bottom:1px solid #29404b}.wrap{max-width:1200px;margin:auto;padding:22px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{background:#0d1b25;border:1px solid #29404b;border-radius:12px;padding:16px}.muted{color:#8fa7b2}@media(max-width:800px){.cards{grid-template-columns:1fr 1fr}}</style></head><body><header><b>135er Grow Central Cloud · Administration V7</b></header><div class='wrap'><p>Standalone-Administration aktiv. Geräte, Pakete und Feature-Freischaltungen werden zentral in derselben Datenbank wie der Cloud-Core verwaltet.</p><div class='cards'><div class='card'>Geräte<br><b>Cloud-Core</b></div><div class='card'>Pakete<br><b>BASIC · PLUS · PRO</b></div><div class='card'>Status<br><b>Pending · Aktiv · Gesperrt</b></div><div class='card'>Identität<br><b>Ed25519</b></div></div><p class='muted'>Administrationszugriffe sind mit CLOUD_ADMIN_TOKEN geschützt. Pis lesen ihre Freigaben über Challenge + vorhandene Ed25519-Geräteidentität.</p></div></body></html>"""
