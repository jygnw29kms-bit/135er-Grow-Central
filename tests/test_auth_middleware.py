from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth_middleware


def _app(monkeypatch, *, gui=False, api=False):
    monkeypatch.setattr(auth_middleware, "configured", lambda: True)
    monkeypatch.setattr(auth_middleware, "authenticated", lambda _request: gui)
    monkeypatch.setattr(auth_middleware, "api_token_authenticated", lambda _request: api)
    app = FastAPI()
    app.add_middleware(auth_middleware.GuiAuthMiddleware)

    @app.get("/api/private")
    async def api_private():
        return {"ok": True}

    @app.get("/ui")
    async def ui():
        return {"ui": True}

    return app


def test_service_token_can_pass_api_boundary(monkeypatch):
    response = TestClient(_app(monkeypatch, api=True)).get("/api/private")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_service_token_cannot_open_browser_ui(monkeypatch):
    client = TestClient(_app(monkeypatch, api=True), follow_redirects=False)
    response = client.get("/ui")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_missing_session_and_token_blocks_private_api(monkeypatch):
    response = TestClient(_app(monkeypatch)).get("/api/private")
    assert response.status_code == 401


def test_gui_session_can_open_ui(monkeypatch):
    response = TestClient(_app(monkeypatch, gui=True)).get("/ui")
    assert response.status_code == 200
