"""Opt-in, per-room Web Push subscriptions and delivery adapter.

Subscriptions belong to a room AND authenticated individual. Never send to a
revoked member, never expose endpoint/keys to API clients, and never claim
delivery merely because an event was queued.

On iOS, subscribe through the installed HTTPS Home Screen PWA; HTTP .local is
not a usable iOS Web Push origin. Cloud delivery requires a separate HTTPS
Cloud subscription gateway and is not implicitly enabled by this Pi router.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gui_auth import authenticated
from app.room_members import _member_from_request, _require_room_access
from app.room_permissions import allowed
from app.room_sharing import _load as member_store, _room_exists

router = APIRouter(prefix="/api/v1/room-push", tags=["room-push"])
DATA_FILE = Path(os.getenv("GC_ROOM_PUSH_FILE", "/var/lib/135er-grow-central/room-push.json"))
ALLOWED_PUSH_HOSTS = {"fcm.googleapis.com", "updates.push.services.mozilla.com"}
MAX_SUBSCRIPTIONS_PER_USER = 5


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=40, max_length=256, pattern=r"^[A-Za-z0-9_-]+={0,2}$")
    auth: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+={0,2}$")


class PushSubscription(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2048)
    keys: PushKeys


def trusted_endpoint(endpoint: str) -> bool:
    try:
        u = urlsplit(endpoint)
        host = (u.hostname or "").lower()
        return (
            u.scheme == "https" and u.username is None and u.password is None
            and u.port in (None, 443) and u.fragment == ""
            and (host in ALLOWED_PUSH_HOSTS or host == "web.push.apple.com"
                 or host.endswith(".push.apple.com"))
            and bool(u.path and u.path != "/")
        )
    except ValueError:
        return False


def _load() -> list[dict]:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "Push subscription store unavailable") from exc
    if not isinstance(data, list):
        raise HTTPException(500, "Invalid push subscription store")
    return data


def _save(rows: list[dict]) -> None:
    DATA_FILE.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".room-push-", dir=DATA_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, DATA_FILE)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _actor(request: Request, room_id: str) -> str:
    _require_room_access(request, room_id, "alerts.view")
    if authenticated(request):
        return "owner"
    member = _member_from_request(request, member_store())
    if not member or member.get("room_id") != room_id or not allowed(member.get("role", ""), "alerts.view"):
        raise HTTPException(403, "No permission to subscribe")
    return member["id"]


def _digest(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def valid_recipient(row: dict, sharing: dict) -> bool:
    if row.get("actor") == "owner":
        return True
    return any(
        m.get("id") == row.get("actor") and m.get("status") == "active"
        and m.get("room_id") == row.get("room_id")
        and allowed(m.get("role", ""), "alerts.view")
        for m in sharing.get("members", [])
    )


def dispatch_event(event: dict, subscriptions: list[dict], *,
                   sharing: dict, send=None) -> dict:
    """Deliver one event with a real Web Push sender; never expose subscription secrets.

    The optional 'send' dependency permits deterministic tests. Real sending
    requires configured VAPID keys and the optional pywebpush package.
    """
    private = os.getenv("GC_WEBPUSH_VAPID_PRIVATE_KEY", "")
    subject = os.getenv("GC_WEBPUSH_SUBJECT", "")
    if send is None:
        if not private or not subject.startswith(("mailto:", "https://")):
            return {"accepted": 0, "failed": 0, "status": "not_configured"}
        try:
            from pywebpush import webpush
        except ImportError:
            return {"accepted": 0, "failed": 0, "status": "sender_not_installed"}
        send = lambda row, payload: webpush(
            subscription_info={"endpoint": row["endpoint"], "keys": row["keys"]},
            data=json.dumps(payload, separators=(",", ":")),
            vapid_private_key=private,
            vapid_claims={"sub": subject},
            timeout=8,
        )
    payload = {
        "title": "Grow Central · Alarm",
        "body": str(event.get("message") or event.get("kind") or "Statusänderung")[:180],
        "room_id": str(event.get("room_id") or "")[:120],
        "kind": str(event.get("kind") or "")[:80],
        "url": "/",
    }
    accepted = failed = 0
    for row in subscriptions:
        if (row.get("room_id") != payload["room_id"]
                or not valid_recipient(row, sharing)
                or not trusted_endpoint(str(row.get("endpoint") or ""))):
            continue
        try:
            send(row, payload)
            accepted += 1
        except Exception:
            failed += 1
    return {"accepted": accepted, "failed": failed, "status": "submitted" if accepted else "not_submitted"}


@router.get("/{room_id}/status")
async def push_status(room_id: str, request: Request):
    actor = _actor(request, room_id)
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    subs = [r for r in _load() if r["room_id"] == room_id and r["actor"] == actor]
    return {
        "room_id": room_id, "registered_devices": len(subs),
        "available": bool(os.getenv("GC_WEBPUSH_VAPID_PUBLIC_KEY")
                          and os.getenv("GC_WEBPUSH_VAPID_PRIVATE_KEY")
                          and os.getenv("GC_WEBPUSH_SUBJECT", "").startswith(("mailto:", "https:"))
                          and importlib.util.find_spec("pywebpush")),
        "vapid_public_key": os.getenv("GC_WEBPUSH_VAPID_PUBLIC_KEY", ""),
        "delivery": "requires_https_installed_pwa_and_permission",
    }


@router.post("/{room_id}/subscriptions")
async def subscribe(room_id: str, body: PushSubscription, request: Request):
    actor = _actor(request, room_id)
    if not _room_exists(room_id):
        raise HTTPException(404, "Room not found")
    if not trusted_endpoint(body.endpoint):
        raise HTTPException(422, "Unsupported push service endpoint")
    rows = _load()
    digest = _digest(body.endpoint)
    rows = [r for r in rows if not (r["room_id"] == room_id and r["actor"] == actor and r["id"] == digest)]
    if sum(r["room_id"] == room_id and r["actor"] == actor for r in rows) >= MAX_SUBSCRIPTIONS_PER_USER:
        raise HTTPException(409, "Maximum registered push devices reached")
    rows.append({"room_id": room_id, "actor": actor, "id": digest,
                 "endpoint": body.endpoint, "keys": body.keys.model_dump()})
    _save(rows)
    return {"ok": True, "registered_devices": sum(r["room_id"] == room_id and r["actor"] == actor for r in rows)}


@router.delete("/{room_id}/subscriptions/{subscription_id}")
async def unsubscribe(room_id: str, subscription_id: str, request: Request):
    actor = _actor(request, room_id)
    rows = _load()
    kept = [r for r in rows if not (r["room_id"] == room_id and r["actor"] == actor
                                     and r["id"] == subscription_id)]
    _save(kept)
    return {"ok": True}
