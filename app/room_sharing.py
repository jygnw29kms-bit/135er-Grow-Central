"""Owner-managed, single-use room invitations.

This is the secure *invitation registry*, not a second bypass around the
single-owner login. Invitations become useful to guests only once the separate
member authentication + Cloud identity layer is activated. No public redeem
endpoint is exposed until then.

All entries are stored as SHA-256 token digests, never raw bearer links.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.gui_auth import authenticated
from app.room_permissions import PERMISSIONS, assignable, permission_matrix

router = APIRouter(prefix="/api/v1/room-sharing", tags=["room-sharing"])
DATA_FILE = Path(os.getenv("GC_ROOM_SHARING_FILE", "/var/lib/135er-grow-central/room-sharing.json"))
MAX_ACTIVE_INVITES_PER_ROOM = 25
INVITATION_TTL_SECONDS = 48 * 3600


def _require_owner(request: Request) -> None:
    # The machine API token is for trusted internal services and MUST NOT
    # allow account administration or creation of bearer invitation links.
    if not authenticated(request):
        raise HTTPException(403, "Only the signed-in room owner may manage invitations")


def _load() -> dict:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"invitations": [], "members": [], "sessions": {}}
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "Room membership store unavailable") from exc
    if not isinstance(value, dict) or not isinstance(value.get("invitations"), list) or not isinstance(value.get("members"), list):
        raise HTTPException(500, "Invalid room membership store")
    value.setdefault("sessions", {})
    if not isinstance(value["sessions"], dict):
        raise HTTPException(500, "Invalid membership session store")
    return value


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    fd, filename = tempfile.mkstemp(dir=DATA_FILE.parent, prefix=".room-sharing-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(filename, 0o600)
        os.replace(filename, DATA_FILE)
    finally:
        Path(filename).unlink(missing_ok=True)


def _room_exists(room_id: str) -> bool:
    from app.rooms import load_state
    return any(room["id"] == room_id for room in load_state()["rooms"])


class InviteCreate(BaseModel):
    role: Literal["admin", "grower", "observer"] = "grower"
    delivery_hint: Literal["qr", "link", "email", "sms"] = "link"
    recipient_label: str = Field(default="", max_length=120)
    ttl_hours: int = Field(default=48, ge=1, le=168)


def make_invitation(data: dict, room_id: str, request: InviteCreate, *, now: float | None = None) -> tuple[dict, str]:
    now = time.time() if now is None else now
    if not assignable("owner", request.role):
        raise ValueError("role cannot be granted")
    active = sum(
        1 for row in data["invitations"]
        if row.get("room_id") == room_id and row.get("status") == "pending"
        and row.get("expires_at", 0) > now
    )
    if active >= MAX_ACTIVE_INVITES_PER_ROOM:
        raise ValueError("too many active invites")
    token = secrets.token_urlsafe(32)
    row = {
        "id": "invite_" + secrets.token_hex(12),
        "room_id": room_id,
        "role": request.role,
        "delivery_hint": request.delivery_hint,
        "recipient_label": request.recipient_label,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "status": "pending",
        "created_at": now,
        "expires_at": now + request.ttl_hours * 3600,
        "used_at": None,
    }
    data["invitations"].append(row)
    return row, token


def invitation_qr_svg(link: str) -> str:
    """Generate QR locally; never send invitation tokens to a third-party QR API."""
    import io
    import qrcode
    from qrcode.image.svg import SvgPathImage

    image = qrcode.make(link, image_factory=SvgPathImage, box_size=5, border=3)
    out = io.BytesIO()
    image.save(out)
    return out.getvalue().decode("utf-8")


def public_invite(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in {"token_hash"}}


@router.get("/policy")
async def sharing_policy(request: Request, _=Depends(_require_owner)):
    return {"roles": permission_matrix(), "invitation_methods": ["qr", "link", "email", "sms"],
            "delivery": "share_link_only_no_automatic_sms_email", "redemption": "pending_member_identity_integration"}


@router.get("/{room_id}/invitations")
async def list_invitations(room_id: str, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    data = _load()
    return {"invitations": [public_invite(row) for row in data["invitations"] if row["room_id"] == room_id]}


@router.post("/{room_id}/invitations")
async def create_invitation(room_id: str, body: InviteCreate, request: Request, _=Depends(_require_owner)):
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    # Validate the controlled origin *before* persisting a one-time invitation.
    # Reject embedded credentials, query/fragment and non-root URL paths.
    from urllib.parse import urlsplit
    origin = os.getenv("GC_ROOM_JOIN_ORIGIN", "http://135er-grow-central.local").rstrip("/")
    try:
        parsed = urlsplit(origin)
        valid_origin = (
            ((parsed.scheme == "https" and parsed.port in (None, 443))
             or origin == "http://135er-grow-central.local")
            and bool(parsed.hostname) and parsed.username is None and parsed.password is None
            and not parsed.path and not parsed.query and not parsed.fragment
        )
    except ValueError:
        valid_origin = False
    if not valid_origin:
        raise HTTPException(503, "Invalid join origin")
    data = _load()
    try:
        row, token = make_invitation(data, room_id, body)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    # Shareable token is revealed ONCE. The owner is responsible for sharing
    # the controlled link through QR, SMS, email or a messaging app.
    link = origin + "/join#invite=" + token
    svg = invitation_qr_svg(link)
    _save(data)
    return {"invitation": public_invite(row), "token_once": token,
            "join_path": "/join#invite=" + token,
            "share_url_once": link, "qr_svg_once": svg,
            "delivery": "manual_share_via_link_sms_email_or_qr", "redeem_enabled": True}


@router.delete("/{room_id}/invitations/{invitation_id}")
async def revoke_invitation(room_id: str, invitation_id: str, request: Request, _=Depends(_require_owner)):
    data = _load()
    row = next((r for r in data["invitations"] if r["room_id"] == room_id and r["id"] == invitation_id), None)
    if row is None:
        raise HTTPException(404, "Invitation not found")
    row["status"] = "revoked"
    _save(data)
    return {"ok": True, "id": invitation_id}
