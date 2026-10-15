"""Grow Central platform compatibility/status sidecar.

The service mirrors operational metadata only. It is never in the control path
for local automation or Apple Home. Reports are authenticated with the same
Ed25519 device identity used by the Grow Central cloud.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_TOKEN = os.environ.get("CLOUD_ADMIN_TOKEN", "").strip()
REPORT_TTL = int(os.environ.get("PLATFORM_REPORT_TTL_SECONDS", "300"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
app = FastAPI(title="Grow Central Platform Status", version="1.0", docs_url=None, redoc_url=None)


def now() -> int:
    return int(time.time())


def sha256s(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def admin_auth(token: str | None) -> None:
    if len(ADMIN_TOKEN) < 32:
        raise HTTPException(503, "admin token not configured")
    candidate = (token or "").strip()
    if not candidate or not secrets.compare_digest(candidate, ADMIN_TOKEN):
        raise HTTPException(401, "invalid admin token")


def init_schema() -> None:
    schema = [
        """CREATE TABLE IF NOT EXISTS platform_reports(
             device_id VARCHAR(36) PRIMARY KEY,
             local_version VARCHAR(40),
             device_api VARCHAR(80),
             device_protocol VARCHAR(80),
             homekit_schema INTEGER,
             homekit_total INTEGER NOT NULL DEFAULT 0,
             homekit_published INTEGER NOT NULL DEFAULT 0,
             homekit_pending INTEGER NOT NULL DEFAULT 0,
             homekit_errors INTEGER NOT NULL DEFAULT 0,
             capabilities_json TEXT NOT NULL DEFAULT '{}',
             reported_at BIGINT NOT NULL
           )""",
        "CREATE INDEX IF NOT EXISTS idx_platform_reports_reported_at ON platform_reports(reported_at)",
    ]
    with engine.begin() as con:
        for stmt in schema:
            con.execute(text(stmt))


init_schema()


class DeviceIdentity(BaseModel):
    device_id: str = Field(min_length=36, max_length=36)


class PlatformReport(BaseModel):
    local_version: str = Field(min_length=1, max_length=40)
    device_api: str = Field(min_length=1, max_length=80)
    device_protocol: str = Field(default="gc-device-v1", min_length=1, max_length=80)
    homekit_schema: int = Field(default=1, ge=1, le=100)
    homekit_total: int = Field(default=0, ge=0, le=10000)
    homekit_published: int = Field(default=0, ge=0, le=10000)
    homekit_pending: int = Field(default=0, ge=0, le=10000)
    homekit_errors: int = Field(default=0, ge=0, le=10000)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class SignedPlatformReport(BaseModel):
    device_id: str = Field(min_length=36, max_length=36)
    nonce: str = Field(min_length=16, max_length=256)
    timestamp: int
    signature: str = Field(min_length=40, max_length=256)
    report: PlatformReport


def canonical_report(report: PlatformReport) -> str:
    return json.dumps(report.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verify_device(device_id: str, nonce: str, timestamp: int, signature: str, report: PlatformReport) -> None:
    t = now()
    if abs(t - timestamp) > 60:
        raise HTTPException(401, "stale device proof")
    nonce_hash = sha256s(nonce)
    with engine.begin() as con:
        nonce_row = con.execute(text(
            "SELECT device_id FROM device_nonces WHERE nonce_hash=:h AND device_id=:d AND expires_at>:t AND used_at IS NULL"
        ), {"h": nonce_hash, "d": device_id, "t": t}).mappings().first()
        if not nonce_row:
            raise HTTPException(401, "invalid or consumed nonce")
        device = con.execute(text(
            "SELECT public_key,revoked_at FROM devices WHERE id=:d AND account_id IS NOT NULL"
        ), {"d": device_id}).mappings().first()
        if not device or device["revoked_at"] is not None:
            raise HTTPException(403, "device revoked")
        digest = hashlib.sha256(canonical_report(report).encode("utf-8")).hexdigest()
        signed = f"GCPLATFORM1\n{device_id}\n{nonce}\n{timestamp}\n{digest}".encode("utf-8")
        try:
            pub = str(device["public_key"])
            pub_raw = base64.urlsafe_b64decode(pub + "=" * (-len(pub) % 4))
            sig_raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
            Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig_raw, signed)
        except Exception as exc:
            raise HTTPException(401, "invalid device signature") from exc
        result = con.execute(text(
            "UPDATE device_nonces SET used_at=:t WHERE nonce_hash=:h AND used_at IS NULL"
        ), {"t": t, "h": nonce_hash})
        if result.rowcount != 1:
            raise HTTPException(409, "nonce already consumed")


@app.get("/health")
def health():
    init_schema()
    with engine.begin() as con:
        reports = con.execute(text("SELECT COUNT(*) FROM platform_reports")).scalar_one()
        fresh = con.execute(text(
            "SELECT COUNT(*) FROM platform_reports WHERE reported_at>=:cutoff"
        ), {"cutoff": now() - REPORT_TTL}).scalar_one()
    return {
        "ok": True,
        "service": "grow-central-platform-status",
        "version": 1,
        "report_ttl_seconds": REPORT_TTL,
        "reports": reports,
        "fresh_reports": fresh,
        "local_first": True,
        "cloud_required_for_homekit": False,
    }


@app.post("/api/v7/platform/challenge")
def challenge(body: DeviceIdentity):
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
    return {"nonce": nonce, "expires_in": 60, "signature_format": "GCPLATFORM1"}


@app.post("/api/v7/platform/report")
def report(body: SignedPlatformReport):
    if body.report.homekit_published + body.report.homekit_pending + body.report.homekit_errors > body.report.homekit_total:
        raise HTTPException(422, "HomeKit counters exceed total")
    verify_device(body.device_id, body.nonce, body.timestamp, body.signature, body.report)
    values = body.report.model_dump()
    values.update({
        "device_id": body.device_id,
        "capabilities_json": json.dumps(body.report.capabilities, ensure_ascii=False, sort_keys=True),
        "reported_at": now(),
    })
    with engine.begin() as con:
        con.execute(text("DELETE FROM platform_reports WHERE device_id=:device_id"), {"device_id": body.device_id})
        con.execute(text("""
            INSERT INTO platform_reports(
                device_id,local_version,device_api,device_protocol,homekit_schema,
                homekit_total,homekit_published,homekit_pending,homekit_errors,
                capabilities_json,reported_at
            ) VALUES(
                :device_id,:local_version,:device_api,:device_protocol,:homekit_schema,
                :homekit_total,:homekit_published,:homekit_pending,:homekit_errors,
                :capabilities_json,:reported_at
            )
        """), values)
        con.execute(text("UPDATE devices SET last_seen=:t WHERE id=:d"), {"t": now(), "d": body.device_id})
    return {"ok": True, "reported_at": values["reported_at"]}


@app.get("/api/admin/platform")
def admin_platform(x_growcentral_admin: str | None = Header(default=None)):
    admin_auth(x_growcentral_admin)
    init_schema()
    with engine.begin() as con:
        rows = [dict(row) for row in con.execute(text(
            """SELECT p.*,d.name,d.last_seen,d.revoked_at
                 FROM platform_reports p LEFT JOIN devices d ON d.id=p.device_id
                 ORDER BY p.reported_at DESC"""
        )).mappings().all()]
    cutoff = now() - REPORT_TTL
    for row in rows:
        row["fresh"] = int(row["reported_at"]) >= cutoff
        try:
            row["capabilities"] = json.loads(row.pop("capabilities_json"))
        except (TypeError, json.JSONDecodeError):
            row["capabilities"] = {}
    return {
        "schema": 1,
        "local_first": True,
        "cloud_required_for_homekit": False,
        "reports": rows,
    }
