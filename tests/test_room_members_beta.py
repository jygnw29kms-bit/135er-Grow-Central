"""Member redemption, revocation, and authorization isolation regression tests."""
import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import room_members, room_sharing
from app.room_permissions import allowed


def _store():
    return {"invitations": [], "members": [], "sessions": {}}


def _invite(data, role="grower"):
    body = room_sharing.InviteCreate(role=role)
    return room_sharing.make_invitation(data, "room_one", body, now=1000)


def test_redeem_is_one_use_and_password_not_stored_plaintext(monkeypatch):
    monkeypatch.setattr(room_members, "_room_exists", lambda room: room == "room_one")
    data = _store()
    row, token = _invite(data)
    request = room_members.AcceptBody(invite_token=token, username="grow_friend",
                                       password="a strong secret passphrase 123")
    member = room_members.redeem(data, request, now=1001)
    assert member["role"] == "grower"
    assert member["room_id"] == "room_one"
    assert member["password_hash"] != "a strong secret passphrase 123"
    assert row["status"] == "used"
    assert row["used_at"] == 1001
    with pytest.raises(HTTPException) as reused:
        room_members.redeem(data, request, now=1002)
    assert reused.value.status_code == 400


def test_expired_or_revoked_links_never_redeem(monkeypatch):
    monkeypatch.setattr(room_members, "_room_exists", lambda room: True)
    data = _store()
    row, token = _invite(data)
    request = room_members.AcceptBody(invite_token=token, username="friend",
                                       password="a good password phrase 123")
    with pytest.raises(HTTPException):
        room_members.redeem(data, request, now=row["expires_at"] + 1)
    row["status"] = "revoked"
    with pytest.raises(HTTPException):
        room_members.redeem(data, request, now=1002)


def test_no_room_cross_access_and_no_write_for_observer(monkeypatch):
    data = _store()
    data["members"].append({
        "id": "member_one", "username": "someone", "room_id": "room_one",
        "role": "observer", "status": "active",
    })
    token = "member-session-token" * 3
    data["sessions"][hashlib.sha256(token.encode()).hexdigest()] = {
        "member_id": "member_one", "expires_at": 9999999999,
    }
    monkeypatch.setattr(room_members, "_load", lambda: data)
    monkeypatch.setattr(room_members, "authenticated", lambda request: False)
    request = SimpleNamespace(cookies={room_members.MEMBER_COOKIE: token})
    assert room_members._require_room_access(request, "room_one", "room.view")["role"] == "observer"
    for room, capability in [
        ("room_two", "room.view"), ("room_one", "journal.write"),
        ("room_one", "devices.control"), ("room_one", "members.manage")
    ]:
        with pytest.raises(HTTPException) as denied:
            room_members._require_room_access(request, room, capability)
        assert denied.value.status_code == 403


def test_revocation_invalidates_sessions(monkeypatch, tmp_path):
    monkeypatch.setattr(room_sharing, "DATA_FILE", tmp_path / "share.json")
    monkeypatch.setattr(room_members, "_room_exists", lambda room: True)
    data = _store()
    row, token = _invite(data)
    member = room_members.redeem(data, room_members.AcceptBody(
        invite_token=token, username="friend",
        password="a good password phrase 123"), now=1001)
    data["sessions"]["session_token_digest"] = {"member_id": member["id"], "expires_at": 9999999999}
    room_sharing._save(data)
    monkeypatch.setattr(room_members, "_require_owner", lambda request: None)
    # owner endpoint can be called directly; dependency check mocked for test.
    import asyncio
    result = asyncio.run(room_members.owner_revoke_member(
        "room_one", member["id"], SimpleNamespace(), None))
    assert result["ok"] is True
    updated = room_sharing._load()
    assert updated["members"][0]["status"] == "revoked"
    assert updated["sessions"] == {}


def test_owner_can_change_member_role_but_not_create_another_owner(tmp_path, monkeypatch):
    import asyncio
    monkeypatch.setattr(room_sharing, "DATA_FILE", tmp_path / "sharing.json")
    data = _store()
    data["members"] = [{"id": "member_one", "username": "friend",
                        "room_id": "room_one", "role": "observer", "status": "active"}]
    room_sharing._save(data)
    result = asyncio.run(room_members.owner_change_role(
        "room_one", "member_one", room_members.MemberRoleChange(role="grower"),
        SimpleNamespace(), None))
    assert result["role"] == "grower"
    assert room_sharing._load()["members"][0]["role"] == "grower"
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        room_members.MemberRoleChange(role="owner")


def test_guest_alerts_respect_room_authorization(monkeypatch):
    import asyncio
    data = _store()
    data["members"] = [{"id": "member_one", "room_id": "room_one",
                        "role": "observer", "status": "active"}]
    token = "member-session-token" * 3
    data["sessions"][hashlib.sha256(token.encode()).hexdigest()] = {
        "member_id": "member_one", "expires_at": 9999999999}
    monkeypatch.setattr(room_members, "_load", lambda: data)
    monkeypatch.setattr(room_members, "authenticated", lambda request: False)
    from app import room_notifications
    monkeypatch.setattr(room_notifications, "_load", lambda: {
        "events": [{"room_id": "room_one", "kind": "threshold_low"},
                   {"room_id": "room_other", "kind": "sensor_offline"}]})
    request = SimpleNamespace(cookies={room_members.MEMBER_COOKIE: token})
    result = asyncio.run(room_members.member_alerts("room_one", request))
    assert len(result["events"]) == 1
    with pytest.raises(HTTPException):
        asyncio.run(room_members.member_alerts("room_other", request))
