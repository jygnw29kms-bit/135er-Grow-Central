"""Cloud account-bound Grow Central room invitations and memberships.

Staged Beta component. Production owner-only WebSocket MUST remain unchanged
until a separate guest socket uses get_membership_role() on EVERY message and
the private GuestRequestBroker (never broadcast_to_clients). Local Pi member
cookies are not trusted as Cloud account credentials.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import time
from typing import Callable

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine, text

ROOM = re.compile(r"^room_[A-Za-z0-9_-]{1,110}$")
ROLES = {"admin", "grower", "observer"}
MAX_PENDING_INVITES = 25


def ensure_schema(engine: Engine) -> None:
    statements = [
        """CREATE TABLE IF NOT EXISTS cloud_room_invitations (
             token_hash VARCHAR(64) PRIMARY KEY,
             device_id VARCHAR(36) NOT NULL,
             room_id VARCHAR(120) NOT NULL,
             creator_account_id VARCHAR(36) NOT NULL,
             role VARCHAR(12) NOT NULL,
             created_at BIGINT NOT NULL,
             expires_at BIGINT NOT NULL,
             redeemed_by VARCHAR(36),
             redeemed_at BIGINT,
             revoked_at BIGINT
           )""",
        """CREATE TABLE IF NOT EXISTS cloud_room_memberships (
             device_id VARCHAR(36) NOT NULL,
             room_id VARCHAR(120) NOT NULL,
             account_id VARCHAR(36) NOT NULL,
             owner_account_id VARCHAR(36) NOT NULL,
             role VARCHAR(12) NOT NULL,
             joined_at BIGINT NOT NULL,
             revoked_at BIGINT,
             PRIMARY KEY (device_id,room_id,account_id)
           )""",
        """CREATE INDEX IF NOT EXISTS idx_cloud_invites_room
           ON cloud_room_invitations(device_id,room_id,expires_at)""",
        """CREATE INDEX IF NOT EXISTS idx_cloud_members_account
           ON cloud_room_memberships(account_id,revoked_at)""",
    ]
    with engine.begin() as db:
        for statement in statements:
            db.execute(text(statement))


def get_membership_role(engine: Engine, device_id: str, room_id: str,
                        account_id: str) -> str | None:
    """Lookup for every guest WebSocket request and for revocation checks."""
    with engine.connect() as db:
        role = db.execute(text("""
          SELECT m.role FROM cloud_room_memberships m
          JOIN devices d ON d.id=m.device_id
          JOIN accounts a ON a.id=m.account_id
          JOIN accounts o ON o.id=m.owner_account_id
          WHERE m.device_id=:d AND m.room_id=:r AND m.account_id=:a
          AND m.revoked_at IS NULL AND d.revoked_at IS NULL
          AND d.account_id=m.owner_account_id AND a.status='active'
          AND o.status='active'
        """), {"d": device_id, "r": room_id, "a": account_id}).scalar()
    return role if role in ROLES else None


class InviteInput(BaseModel):
    role: str = Field(default="grower", pattern=r"^(admin|grower|observer)$")
    ttl_hours: int = Field(default=48, ge=1, le=168)


class RedeemInput(BaseModel):
    invite_token: str = Field(min_length=30, max_length=200)


class RoleInput(BaseModel):
    role: str = Field(pattern=r"^(admin|grower|observer)$")


def build_router(
    engine: Engine,
    *,
    account_from_access: Callable[[str], str],
    get_device_for_account: Callable[[str, str], object],
    public_url: str,
    clock: Callable[[], int] = lambda: int(time.time()),
) -> APIRouter:
    router = APIRouter(prefix="/api/v2/collaboration", tags=["cloud-collaboration"])

    def account(authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer ") or not authorization[7:].strip():
            raise HTTPException(401, "Bearer access token required")
        return account_from_access(authorization[7:].strip())

    def owner(device_id: str, account_id: str) -> None:
        get_device_for_account(device_id, account_id)

    def valid_room(room_id: str) -> None:
        if not ROOM.fullmatch(room_id):
            raise HTTPException(422, "Invalid room identifier")

    @router.post("/devices/{device_id}/rooms/{room_id}/invitations")
    def invite(device_id: str, room_id: str, body: InviteInput,
               authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        owner(device_id, account_id)
        valid_room(room_id)
        current = clock()
        raw_token = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with engine.begin() as db:
            n = db.execute(text("""
              SELECT COUNT(*) FROM cloud_room_invitations
              WHERE device_id=:d AND room_id=:r AND expires_at>:now
                AND redeemed_by IS NULL AND revoked_at IS NULL
            """), {"d": device_id, "r": room_id, "now": current}).scalar()
            if n >= MAX_PENDING_INVITES:
                raise HTTPException(409, "Too many outstanding invitations")
            db.execute(text("""
              INSERT INTO cloud_room_invitations
                (token_hash,device_id,room_id,creator_account_id,role,created_at,expires_at)
              VALUES (:h,:d,:r,:owner,:role,:created,:expires)
            """), {"h": hashed, "d": device_id, "r": room_id, "owner": account_id,
                   "role": body.role, "created": current,
                   "expires": current + body.ttl_hours * 3600})
        # Fragment keeps the secret out of web server access logs. The
        # Cloud PWA must implement its own join form before this is usable.
        return {"share_url_once": public_url.rstrip("/") + "/#room-invite=" + raw_token,
                "token_once": raw_token, "room_id": room_id,
                "role": body.role, "expires_at": current + body.ttl_hours * 3600,
                "delivery": "manual_share_only", "acceptance_ui": "cloud_join_page"}

    @router.post("/accept")
    def accept(body: RedeemInput, authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        digest = hashlib.sha256(body.invite_token.encode("utf-8")).hexdigest()
        current = clock()
        with engine.begin() as db:
            row = db.execute(text("""
              SELECT device_id,room_id,creator_account_id,role
              FROM cloud_room_invitations WHERE token_hash=:h
                AND expires_at>:now AND redeemed_by IS NULL AND revoked_at IS NULL
            """), {"h": digest, "now": current}).mappings().first()
            if not row:
                raise HTTPException(400, "Invalid or expired invitation")
            if row["creator_account_id"] == account_id:
                raise HTTPException(403, "Owner cannot redeem own invitation")
            # Ensure the original inviter still owns the device. Revoking
            # its Cloud pairing invalidates outstanding room invitations.
            owner(row["device_id"], row["creator_account_id"])
            update = db.execute(text("""
              UPDATE cloud_room_invitations
              SET redeemed_by=:account,redeemed_at=:now
              WHERE token_hash=:h AND redeemed_by IS NULL AND revoked_at IS NULL
                AND expires_at>:now
            """), {"account": account_id, "now": current, "h": digest})
            if update.rowcount != 1:
                raise HTTPException(409, "Invitation already claimed")
            matched = db.execute(text("""
              SELECT 1 FROM cloud_room_memberships
              WHERE device_id=:d AND room_id=:r AND account_id=:a
            """), {"d": row["device_id"], "r": row["room_id"], "a": account_id}).first()
            values = {"d": row["device_id"], "r": row["room_id"],
                      "a": account_id, "owner": row["creator_account_id"],
                      "role": row["role"], "now": current}
            if matched:
                db.execute(text("""
                  UPDATE cloud_room_memberships SET role=:role,owner_account_id=:owner,revoked_at=NULL
                  WHERE device_id=:d AND room_id=:r AND account_id=:a
                """), values)
            else:
                db.execute(text("""
                  INSERT INTO cloud_room_memberships
                  (device_id,room_id,account_id,owner_account_id,role,joined_at)
                  VALUES (:d,:r,:a,:owner,:role,:now)
                """), values)
        return {"ok": True, "device_id": row["device_id"],
                "room_id": row["room_id"], "role": row["role"],
                "remote_access": "guest_scoped"}

    @router.get("/my-rooms")
    def my_rooms(authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        with engine.connect() as db:
            rows = db.execute(text("""
              SELECT m.device_id,m.room_id,m.role
              FROM cloud_room_memberships m
              JOIN devices d ON d.id=m.device_id
              JOIN accounts o ON o.id=m.owner_account_id
              JOIN accounts guest ON guest.id=m.account_id
              WHERE m.account_id=:a AND m.revoked_at IS NULL
                AND guest.status='active'
                AND d.revoked_at IS NULL AND d.account_id=m.owner_account_id
                AND o.status='active'
            """), {"a": account_id}).mappings().all()
        return {"memberships": [dict(row) for row in rows],
                "remote_access": "guest_scoped"}

    @router.get("/devices/{device_id}/rooms/{room_id}/members")
    def members(device_id: str, room_id: str,
                authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        owner(device_id, account_id)
        valid_room(room_id)
        with engine.connect() as db:
            rows = db.execute(text("""
              SELECT m.account_id,m.role,m.joined_at FROM cloud_room_memberships m
              JOIN accounts a ON a.id=m.account_id
              WHERE m.device_id=:d AND m.room_id=:r AND m.revoked_at IS NULL
                AND a.status='active'
            """), {"d": device_id, "r": room_id}).mappings().all()
        return {"members": [dict(row) for row in rows]}

    @router.patch("/devices/{device_id}/rooms/{room_id}/members/{member_id}")
    def change_role(device_id: str, room_id: str, member_id: str, body: RoleInput,
                    authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        owner(device_id, account_id)
        valid_room(room_id)
        with engine.begin() as db:
            result = db.execute(text("""
              UPDATE cloud_room_memberships SET role=:role
              WHERE device_id=:d AND room_id=:r AND account_id=:m
                AND revoked_at IS NULL
            """), {"role": body.role, "d": device_id, "r": room_id, "m": member_id})
            if result.rowcount != 1:
                raise HTTPException(404, "Member not found")
        return {"ok": True, "role": body.role}

    @router.delete("/devices/{device_id}/rooms/{room_id}/members/{member_id}")
    def revoke(device_id: str, room_id: str, member_id: str,
               authorization: str | None = Header(default=None)):
        account_id = account(authorization)
        owner(device_id, account_id)
        valid_room(room_id)
        with engine.begin() as db:
            result = db.execute(text("""
              UPDATE cloud_room_memberships SET revoked_at=:now
              WHERE device_id=:d AND room_id=:r AND account_id=:m
                AND revoked_at IS NULL
            """), {"now": clock(), "d": device_id, "r": room_id, "m": member_id})
            if result.rowcount != 1:
                raise HTTPException(404, "Member not found")
        return {"ok": True}

    return router
