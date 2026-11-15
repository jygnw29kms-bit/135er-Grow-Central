"""A room-member cookie is not an owner cookie or a machine API token."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth_middleware, room_members


def test_room_member_middleware_never_unlocks_unscoped_routes(monkeypatch):
    monkeypatch.setattr(auth_middleware, "configured", lambda: True)
    monkeypatch.setattr(auth_middleware, "authenticated", lambda req: False)
    monkeypatch.setattr(auth_middleware, "api_token_authenticated", lambda req: False)
    monkeypatch.setattr(room_members, "member_authenticated", lambda req: True)

    app = FastAPI()
    app.add_middleware(auth_middleware.GuiAuthMiddleware)

    @app.get("/api/v1/room-members/room/room_1")
    async def scoped():
        return {"scoped": True}

    @app.get("/api/v1/rooms")
    async def unscoped():
        return {"unscoped": True}

    @app.get("/ui")
    async def owner_ui():
        return {"owner": True}

    client = TestClient(app, follow_redirects=False)
    assert client.get("/api/v1/room-members/room/room_1").status_code == 200
    assert client.get("/api/v1/rooms").status_code == 401
    assert client.get("/ui").status_code == 303
    assert client.get("/join").status_code != 401
