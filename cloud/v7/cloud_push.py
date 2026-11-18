"""Account-bound Cloud Web Push opt-in. No push events are sent by this module.

This is intentionally separate from the Pi's local subscription store. Browser
credentials stay in the Cloud origin and are never forwarded to the Final Master
iframe. A push *subscription* is not evidence of a delivered alarm.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine, text

DEVICE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_SUBSCRIPTIONS_PER_OWNER_DEVICE = 5


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=40, max_length=256, pattern=r"^[A-Za-z0-9_-]+={0,2}$")
    auth: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+={0,2}$")


class CloudSubscription(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2048)
    keys: PushKeys


def trusted_endpoint(endpoint: str) -> bool:
    """Allow official Web Push services only, never arbitrary server URLs."""
    try:
        u = urlsplit(endpoint)
        host = (u.hostname or "").lower().rstrip(".")
        return (u.scheme == "https" and u.username is None and u.password is None
                and u.port in (None, 443) and not u.fragment
                and (host in {"fcm.googleapis.com", "updates.push.services.mozilla.com",
                              "web.push.apple.com"} or host.endswith(".push.apple.com"))
                and bool(u.path and u.path != "/"))
    except ValueError:
        return False


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as db:
        db.execute(text("""CREATE TABLE IF NOT EXISTS gc_cloud_push_subscriptions (
          id VARCHAR(64) PRIMARY KEY,
          account_id VARCHAR(36) NOT NULL,
          device_id VARCHAR(100) NOT NULL,
          endpoint TEXT NOT NULL,
          p256dh VARCHAR(256) NOT NULL,
          auth VARCHAR(128) NOT NULL,
          created_at BIGINT NOT NULL DEFAULT 0
        )"""))
        db.execute(text("""CREATE INDEX IF NOT EXISTS idx_gc_cloud_push_owner_device
          ON gc_cloud_push_subscriptions(account_id, device_id)"""))



def submit_owner_alert(
    engine: Engine, device_id: str, event: dict, *,
    send: Callable[[dict, dict], object] | None = None,
) -> dict:
    """Trusted in-process dispatch adapter, NOT an exposed HTTP endpoint.

    Call only after the Cloud relay has validated event origin, its bound Pi
    identity and its room. Push acceptance is not proof of handset display.
    """
    if not DEVICE.fullmatch(device_id):
        raise ValueError("Invalid device ID")
    if not isinstance(event, dict) or event.get("room_id") is None:
        raise ValueError("Missing room-bound event")
    room_id = event.get("room_id")
    if not isinstance(room_id, str) or not re.fullmatch(r"room_[A-Za-z0-9_-]{1,110}", room_id):
        raise ValueError("Invalid room ID")
    private = os.getenv("GC_CLOUD_VAPID_PRIVATE_KEY", "")
    subject = os.getenv("GC_CLOUD_WEBPUSH_SUBJECT", "")
    if send is None:
        if not private or not subject.startswith(("mailto:", "https:")):
            return {"accepted": 0, "failed": 0, "status": "not_configured"}
        try:
            from pywebpush import webpush
        except ImportError:
            return {"accepted": 0, "failed": 0, "status": "sender_not_installed"}
        def send(subscription: dict, data: dict) -> object:
            import json
            return webpush(subscription_info=subscription,
                           data=json.dumps(data, separators=(",", ":")),
                           vapid_private_key=private,
                           vapid_claims={"sub": subject}, timeout=8)
    with engine.connect() as db:
        rows = db.execute(text("""SELECT s.endpoint, s.p256dh, s.auth
              FROM gc_cloud_push_subscriptions s
              JOIN accounts a ON a.id=s.account_id
              JOIN devices d ON d.id=s.device_id AND d.account_id=s.account_id
              WHERE s.device_id=:d AND a.status='active' AND d.revoked_at IS NULL"""),
              {"d": device_id}).all()
    payload = {"title": "Grow Central · Alarm",
               "body": str(event.get("message") or event.get("kind") or "Statusänderung")[:180],
               "room_id": room_id, "kind": str(event.get("kind") or "")[:80],
               "url": "/"}
    accepted = failed = 0
    for endpoint, p256dh, auth in rows:
        if not trusted_endpoint(endpoint):
            continue
        try:
            send({"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}, payload)
            accepted += 1
        except Exception:
            failed += 1
    return {"accepted": accepted, "failed": failed,
            "status": "submitted" if accepted else "not_submitted"}

def build_router(
    engine: Engine, *, account_from_access: Callable[[str], str],
    get_device_for_account: Callable[[str, str], object],
    clock: Callable[[], int] | None = None,
) -> APIRouter:
    import time
    current_time = clock or (lambda: int(time.time()))
    router = APIRouter(prefix="/api/v2/push", tags=["cloud-push"])

    def owner(device_id: str, authorization: str | None) -> str:
        if not DEVICE.fullmatch(device_id):
            raise HTTPException(422, "Invalid device ID")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Cloud login required")
        account_id = account_from_access(authorization[7:].strip())
        get_device_for_account(device_id, account_id)
        return account_id

    @router.get("/devices/{device_id}/status")
    def status(device_id: str, authorization: str | None = Header(default=None)):
        account_id = owner(device_id, authorization)
        with engine.connect() as db:
            count = db.execute(text("""SELECT COUNT(*) FROM gc_cloud_push_subscriptions
                 WHERE account_id=:a AND device_id=:d"""),
                 {"a": account_id, "d": device_id}).scalar_one()
        public = os.getenv("GC_CLOUD_VAPID_PUBLIC_KEY", "")
        sender_ready = bool(public and os.getenv("GC_CLOUD_VAPID_PRIVATE_KEY")
                            and os.getenv("GC_CLOUD_WEBPUSH_SUBJECT", "").startswith(("mailto:", "https:")))
        return {"device_id": device_id, "registered_devices": count,
                "vapid_public_key": public if sender_ready else "",
                "can_subscribe": sender_ready,
                "delivery": "not_armed_until_server_event_dispatch_and_ios_verification"}

    @router.post("/devices/{device_id}/subscriptions", status_code=201)
    def subscribe(device_id: str, body: CloudSubscription,
                  authorization: str | None = Header(default=None)):
        account_id = owner(device_id, authorization)
        if not trusted_endpoint(body.endpoint):
            raise HTTPException(422, "Unsupported Web Push endpoint")
        if not (os.getenv("GC_CLOUD_VAPID_PUBLIC_KEY") and os.getenv("GC_CLOUD_VAPID_PRIVATE_KEY")
                and os.getenv("GC_CLOUD_WEBPUSH_SUBJECT", "").startswith(("mailto:", "https:"))):
            raise HTTPException(503, "Cloud Push not configured")
        digest = hashlib.sha256(body.endpoint.encode("utf-8")).hexdigest()
        with engine.begin() as db:
            existing = db.execute(text("""SELECT account_id, device_id
                FROM gc_cloud_push_subscriptions WHERE id=:i"""), {"i": digest}).first()
            if existing and (existing[0] != account_id or existing[1] != device_id):
                raise HTTPException(409, "Subscription belongs to a different account or device")
            count = db.execute(text("""SELECT COUNT(*) FROM gc_cloud_push_subscriptions
              WHERE account_id=:a AND device_id=:d"""),
              {"a": account_id, "d": device_id}).scalar_one()
            if not existing and count >= MAX_SUBSCRIPTIONS_PER_OWNER_DEVICE:
                raise HTTPException(409, "Maximum devices reached")
            db.execute(text("""DELETE FROM gc_cloud_push_subscriptions
                          WHERE id=:i AND account_id=:a AND device_id=:d"""),
                       {"i": digest, "a": account_id, "d": device_id})
            db.execute(text("""INSERT INTO gc_cloud_push_subscriptions
                 (id,account_id,device_id,endpoint,p256dh,auth,created_at)
                 VALUES (:i,:a,:d,:e,:p,:k,:t)"""),
                 {"i": digest, "a": account_id, "d": device_id, "e": body.endpoint,
                  "p": body.keys.p256dh, "k": body.keys.auth, "t": current_time()})
        return {"registered": True, "subscription_id": digest,
                "delivery": "registration_only_not_proof_of_notification"}

    @router.delete("/devices/{device_id}/subscriptions/{subscription_id}")
    def revoke(device_id: str, subscription_id: str,
               authorization: str | None = Header(default=None)):
        account_id = owner(device_id, authorization)
        if not DIGEST.fullmatch(subscription_id):
            raise HTTPException(422, "Invalid subscription ID")
        with engine.begin() as db:
            db.execute(text("""DELETE FROM gc_cloud_push_subscriptions
                WHERE id=:i AND account_id=:a AND device_id=:d"""),
                {"i": subscription_id, "a": account_id, "d": device_id})
        return {"revoked": True}

    return router
