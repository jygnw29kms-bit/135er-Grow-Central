"""Fail-closed room-scoped Cloud guest relay policy.

This module is deliberately NOT activated in the owner-only production
WebSocket until Cloud account membership persistence and private response
routing are in place. Every guest request must be authorized here before
forwarding to the Pi; responses must be routed only to the requesting socket,
never through device-wide broadcast_to_clients().
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from typing import Any

READ_PATH = re.compile(
    r"^/api/v1/rooms/([a-zA-Z0-9_-]{1,120})/"
    r"(journal|plants|events|devices|live-snapshot)(?:\?limit=([0-9]{1,3}))?$"
)
ROOM_ID = re.compile(r"^room_[a-zA-Z0-9_-]{1,110}$")
READ_PERMISSIONS = {
    "journal": "journal.view",
    "plants": "room.view",
    "events": "room.view",
    "devices": "devices.view",
    "live-snapshot": "room.view",
}
ROLE_PERMISSIONS = {
    "admin": frozenset({"room.view", "journal.view", "journal.write", "devices.view"}),
    "grower": frozenset({"room.view", "journal.view", "journal.write", "devices.view"}),
    "observer": frozenset({"room.view", "journal.view", "devices.view"}),
}
EXPECTED_RESULT = {"read": "read_result", "journal_create": "journal_result"}
MAX_PENDING_PER_SESSION = 24
PENDING_TTL_SECONDS = 30


class GuestRequestDenied(ValueError):
    """Guest action is outside the explicitly delegated capabilities."""


def authorize_guest_message(message: dict, *, room_id: str, role: str) -> tuple[dict, str]:
    """Return a normalized request and expected result envelope, or fail closed."""
    if not ROOM_ID.fullmatch(room_id) or role not in ROLE_PERMISSIONS:
        raise GuestRequestDenied("No authorized room role")
    if not isinstance(message, dict):
        raise GuestRequestDenied("Invalid envelope")
    kind = message.get("type")
    capabilities = ROLE_PERMISSIONS[role]
    if kind == "read":
        path = message.get("path")
        match = READ_PATH.fullmatch(path) if isinstance(path, str) else None
        if not match or match.group(1) != room_id:
            raise GuestRequestDenied("Read not scoped to assigned room")
        if READ_PERMISSIONS[match.group(2)] not in capabilities:
            raise GuestRequestDenied("Missing room read permission")
        # No arbitrary keys or query parameters may reach the Pi as guest.
        if set(message) - {"type", "request_id", "path"}:
            raise GuestRequestDenied("Unexpected read arguments")
        if match.group(3) is not None and int(match.group(3)) > 100:
            raise GuestRequestDenied("Invalid query limit")
        normalized = {"type": "read", "path": path}
        return normalized, EXPECTED_RESULT["read"]

    if kind == "journal_create" and "journal.write" in capabilities:
        if message.get("room_id") != room_id or message.get("confirm_write") is not True:
            raise GuestRequestDenied("Journal write not confirmed for assigned room")
        permitted = {"type", "request_id", "room_id", "title", "text", "category",
                     "plant_id", "confirm_write"}
        if set(message) - permitted:
            raise GuestRequestDenied("Unexpected journal fields")
        title = message.get("title")
        note = message.get("text", "")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise GuestRequestDenied("Invalid journal title")
        if not isinstance(note, str) or len(note) > 5000:
            raise GuestRequestDenied("Invalid journal note")
        if message.get("category", "note") not in {
            "note", "observation", "watering", "feeding", "training", "other"
        }:
            raise GuestRequestDenied("Unsupported journal category")
        plant_id = message.get("plant_id")
        if plant_id is not None and (
            not isinstance(plant_id, str)
            or not re.fullmatch(r"plant_[a-zA-Z0-9_-]{1,110}", plant_id)
        ):
            raise GuestRequestDenied("Invalid plant identifier")
        normalized = {k: v for k, v in message.items() if k != "request_id"}
        return normalized, EXPECTED_RESULT["journal_create"]

    raise GuestRequestDenied("Guest action not permitted")


@dataclass(frozen=True)
class Pending:
    session_id: str
    original_id: str
    expected_type: str
    expires_at: float


class GuestRequestBroker:
    """A strict per-request response broker for a *future* guest WebSocket.

    Device-origin responses cannot be published to all device subscribers.
    The authenticated Cloud client gets only its own correlated response.
    This broker does not itself authenticate Cloud accounts or forward sockets.
    """
    def __init__(self):
        self._pending: dict[str, Pending] = {}

    def prepare(self, message: dict, *, session_id: str, room_id: str,
                role: str, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        self.expire(now=now)
        if not isinstance(session_id, str) or not session_id:
            raise GuestRequestDenied("Invalid guest session")
        active = sum(p.session_id == session_id for p in self._pending.values())
        if active >= MAX_PENDING_PER_SESSION:
            raise GuestRequestDenied("Too many pending requests")
        normalized, expected_type = authorize_guest_message(
            message, room_id=room_id, role=role
        )
        original_id = message.get("request_id")
        if (not isinstance(original_id, str) or not 1 <= len(original_id) <= 64
                or not re.fullmatch(r"[a-zA-Z0-9_-]+", original_id)):
            raise GuestRequestDenied("Invalid request identifier")
        internal_id = secrets.token_urlsafe(24)
        self._pending[internal_id] = Pending(
            session_id, original_id, expected_type, now + PENDING_TTL_SECONDS
        )
        return {**normalized, "request_id": internal_id}

    def route_reply(self, message: dict, *, now: float | None = None) -> tuple[str, dict] | None:
        now = time.monotonic() if now is None else now
        if not isinstance(message, dict):
            return None
        internal_id = message.get("request_id")
        if not isinstance(internal_id, str):
            return None
        pending = self._pending.pop(internal_id, None)
        if pending is None or pending.expires_at <= now:
            return None
        if message.get("type") != pending.expected_type:
            return None
        response = dict(message)
        response["request_id"] = pending.original_id
        return pending.session_id, response

    def revoke_session(self, session_id: str) -> None:
        self._pending = {
            key: pending for key, pending in self._pending.items()
            if pending.session_id != session_id
        }

    def expire(self, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._pending = {
            key: pending for key, pending in self._pending.items()
            if pending.expires_at > now
        }

    @property
    def pending_count(self) -> int:
        return len(self._pending)
