"""Delegated invitations: admin may invite Grower/Observer in own room only."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth_middleware, room_members, room_sharing


def test_delegated_room_admin_invites_without_privilege_escalation(monkeypatch, tmp_path):
    monkeypatch.setattr(room_sharing, "DATA_FILE", tmp_path / "room-sharing.json")
    monkeypatch.setattr(room_sharing, "_room_exists", lambda room: room in {"room_a", "room_b"})
    monkeypatch.setattr(room_members, "_room_exists", lambda room: room in {"room_a", "room_b"})
    monkeypatch.setattr(auth_middleware, "configured", lambda: True)
    monkeypatch.setattr(auth_middleware, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(room_members, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(room_sharing, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(auth_middleware, "api_token_authenticated", lambda _: False)
    app = FastAPI()
    app.add_middleware(auth_middleware.GuiAuthMiddleware)
    app.include_router(room_members.router)
    app.include_router(room_sharing.router)

    owner = TestClient(app)
    owner.cookies.set("test_owner", "yes")
    invitation = owner.post("/api/v1/room-sharing/room_a/invitations",
                            json={"role": "admin"}).json()
    assert "token_once" in invitation

    admin = TestClient(app)
    acceptance = admin.post("/api/v1/room-members/accept", json={
        "invite_token": invitation["token_once"],
        "username": "delegated_admin",
        "password": "a very long admin test password",
    })
    assert acceptance.status_code == 200, acceptance.text
    url = "/api/v1/room-members/room/room_a/invitations"
    allowed = admin.post(url, json={"role": "grower", "delivery_hint": "qr"})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["invitation"]["role"] == "grower"
    assert "token_once" in allowed.json()
    assert admin.post(url, json={"role": "observer"}).status_code == 200
    assert admin.post(url, json={"role": "admin"}).status_code == 403
    assert admin.post("/api/v1/room-members/room/room_b/invitations",
                      json={"role": "grower"}).status_code == 403
    assert admin.post("/api/v1/room-sharing/room_a/invitations",
                      json={"role": "grower"}).status_code in (401, 403)
    members = owner.get("/api/v1/room-members/owner/room_a/members").json()["members"]
    assert len(members) == 1
    assert owner.delete("/api/v1/room-members/owner/room_a/members/"
                        + members[0]["id"]).status_code == 200
    assert admin.post(url, json={"role": "grower"}).status_code in (401, 403)


def test_grower_and_observer_cannot_delegate(monkeypatch, tmp_path):
    from app.room_permissions import assignable
    assert not assignable("grower", "observer")
    assert not assignable("observer", "grower")
    assert not assignable("admin", "admin")
    assert not assignable("admin", "owner")
