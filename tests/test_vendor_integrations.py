from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.vendor_integrations import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_vendor_profiles_include_spider_farmer_codes_and_esp32():
    data = _client().get("/api/vendors/profiles").json()
    profiles = data["profiles"]
    codes = {row["code"] for row in profiles if row["vendor"] == "Spider Farmer"}
    assert {"1001", "1002", "1005", "1007"}.issubset(codes)
    assert any(row["family"] == "ESP32" for row in profiles)


def test_vendor_writes_are_safe_by_default(monkeypatch):
    monkeypatch.delenv("GC_SPIDER_WRITES", raising=False)
    data = _client().get("/api/vendors/status").json()
    assert data["spider_farmer"]["writes_enabled"] is False
    assert data["esp32"]["enabled"] is True
