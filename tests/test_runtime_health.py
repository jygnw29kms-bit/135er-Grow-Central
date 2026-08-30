from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.runtime_health import router


def test_runtime_health_declares_headless_local_first(monkeypatch, tmp_path):
    import app.runtime_health as runtime_health

    monkeypatch.setattr(runtime_health, "STATE_DIR", tmp_path)
    monkeypatch.setattr(runtime_health, "APP_DIR", tmp_path)
    monkeypatch.setattr(runtime_health, "CLOUD_STATE", tmp_path / "cloud-link-status.json")

    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/runtime/health")
    assert response.status_code == 200
    data = response.json()
    assert data["architecture"] == "headless-local-first"
    assert data["ui"]["local_kiosk"] is False
    assert data["ui"]["desktop_web"] is True
    assert data["ui"]["mobile"] is True
    assert data["device_api"] == "gc-device-v1"
    assert data["device_runtime"]["provider_count"] >= 1
