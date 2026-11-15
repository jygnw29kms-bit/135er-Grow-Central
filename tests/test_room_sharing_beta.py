"""Permission and invitation security regression tests."""
import hashlib

import pytest
from fastapi import HTTPException
from unittest.mock import Mock

from app.room_permissions import allowed, assignable, PERMISSIONS
from app import room_sharing


def test_owner_exclusivity_and_growth_roles():
    assert allowed("owner", "members.manage")
    assert allowed("admin", "members.invite")
    assert not allowed("admin", "members.manage")
    assert allowed("grower", "journal.write")
    assert not allowed("grower", "devices.control")
    assert not allowed("observer", "journal.write")
    assert not allowed("observer", "members.invite")
    assert not allowed("unrecognized", "room.view")
    assert assignable("admin", "grower")
    assert not assignable("admin", "admin")
    assert not assignable("grower", "observer")
    assert not assignable("owner", "owner")


def test_invites_are_cryptographic_and_one_time_visible():
    store = {"invitations": [], "members": []}
    body = room_sharing.InviteCreate(role="grower", delivery_hint="qr")
    row, token = room_sharing.make_invitation(store, "room_1", body, now=100.0)
    assert len(token) >= 40
    assert row["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(store)
    assert row["expires_at"] == 100.0 + 48 * 3600
    assert "token_hash" not in room_sharing.public_invite(row)
    assert row["status"] == "pending"


def test_invites_cannot_grant_owner_or_overflow():
    with pytest.raises(ValueError):
        room_sharing.InviteCreate(role="owner")
    data = {"invitations": [
        {"room_id": "room_1", "status": "pending", "expires_at": 10000}
        for _ in range(room_sharing.MAX_ACTIVE_INVITES_PER_ROOM)
    ], "members": []}
    with pytest.raises(ValueError, match="too many"):
        room_sharing.make_invitation(data, "room_1", room_sharing.InviteCreate(), now=100)


def test_api_machine_token_is_not_owner_role(monkeypatch):
    monkeypatch.setattr(room_sharing, "authenticated", lambda request: False)
    with pytest.raises(HTTPException) as info:
        room_sharing._require_owner(Mock())
    assert info.value.status_code == 403


def test_invite_store_never_exposes_raw_token(tmp_path, monkeypatch):
    monkeypatch.setattr(room_sharing, "DATA_FILE", tmp_path / "invites.json")
    data = {"invitations": [], "members": []}
    row, token = room_sharing.make_invitation(data, "room_1", room_sharing.InviteCreate(), now=100)
    room_sharing._save(data)
    raw = room_sharing.DATA_FILE.read_text()
    assert token not in raw
    assert row["token_hash"] in raw
    assert (room_sharing.DATA_FILE.stat().st_mode & 0o077) == 0
