from fastapi import FastAPI
from fastapi.testclient import TestClient
import json
from datetime import datetime, timedelta, timezone

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


def test_stale_cloud_warns_without_blocking_local_operation(monkeypatch, tmp_path):
    import app.runtime_health as health
    monkeypatch.setattr(health, "STATE_DIR", tmp_path)
    monkeypatch.setattr(health, "APP_DIR", tmp_path)
    monkeypatch.setattr(health, "CLOUD_STATE", tmp_path / "cloud-link-status.json")
    monkeypatch.setattr(health, "_read_env", lambda: {"GC_CLOUD_ENABLED": "true", "GC_CLOUD_URL": "https://cloud.example"})
    (tmp_path / ".provisioned").touch()
    health.CLOUD_STATE.write_text(json.dumps({
        "state": "connected", "cloud_origin": "https://cloud.example",
        "updated_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    }))
    app = FastAPI()
    app.include_router(router)
    data = TestClient(app).get("/api/runtime/health").json()
    assert data["ok"] is True
    assert data["state"] == "warning"
    assert data["cloud"]["state"] == "stale"
    assert data["cloud"]["optional_ok"] is True
    assert "cloud_not_connected" in data["warnings"]
