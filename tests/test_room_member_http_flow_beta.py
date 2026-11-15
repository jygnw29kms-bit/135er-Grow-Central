"""Actual HTTP invite -> claim -> scoped member login without owner API access."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth_middleware, room_members, room_sharing, rooms


def test_local_owner_invites_member_with_room_only_access(monkeypatch, tmp_path):
    monkeypatch.setattr(room_sharing, "DATA_FILE", tmp_path / "sharing.json")
    monkeypatch.setattr(auth_middleware, "configured", lambda: True)
    monkeypatch.setattr(auth_middleware, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(auth_middleware, "api_token_authenticated", lambda request: False)
    monkeypatch.setattr(room_sharing, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(room_members, "authenticated",
                        lambda request: request.cookies.get("test_owner") == "yes")
    monkeypatch.setattr(room_sharing, "_room_exists", lambda room_id: room_id == "room_test")
    monkeypatch.setattr(room_members, "_room_exists", lambda room_id: room_id == "room_test")
    monkeypatch.setattr(rooms, "load_state", lambda: {
        "rooms": [{"id": "room_test", "name": "Grow Zelt"}],
        "plants": [{"id": "plant_1", "room_id": "room_test", "name": "Basilikum", "phase": "vegetative"}],
        "room_journal": [],
    })

    app = FastAPI()
    app.add_middleware(auth_middleware.GuiAuthMiddleware)
    app.include_router(room_sharing.router)
    app.include_router(room_members.router)
    app.include_router(room_members.join_router)

    @app.get("/api/v1/rooms")
    async def unscoped_owner():
        return {"unscoped": True}

    owner = TestClient(app)
    owner.cookies.set("test_owner", "yes")
    invite_response = owner.post("/api/v1/room-sharing/room_test/invitations",
                                 json={"role": "grower", "delivery_hint": "sms"})
    assert invite_response.status_code == 200, invite_response.text
    invitation = invite_response.json()
    assert "qr_svg_once" in invitation and "<svg" in invitation["qr_svg_once"]
    assert "/join#invite=" in invitation["share_url_once"]

    guest = TestClient(app, follow_redirects=False)
    assert guest.get("/join").status_code == 200
    token = invitation["token_once"]
    response = guest.post("/api/v1/room-members/accept", json={
        "invite_token": token, "username": "grower1",
        "password": "long secure passphrase 123",
    })
    assert response.status_code == 200, response.text
    assert guest.get("/api/v1/room-members/status").json()["role"] == "grower"
    room = guest.get("/api/v1/room-members/room/room_test")
    assert room.status_code == 200
    assert room.json()["plants"][0]["name"] == "Basilikum"
    assert guest.get("/api/v1/rooms").status_code == 401
    assert guest.get("/api/v1/room-sharing/policy").status_code in (401, 403)

    # Owner can instantly revoke: the member cookie becomes unusable.
    members = owner.get("/api/v1/room-members/owner/room_test/members").json()["members"]
    assert len(members) == 1
    revoked = owner.delete("/api/v1/room-members/owner/room_test/members/" + members[0]["id"])
    assert revoked.status_code == 200
    assert guest.get("/api/v1/room-members/status").json()["authenticated"] is False
    assert guest.get("/api/v1/room-members/room/room_test").status_code in (401, 403)
