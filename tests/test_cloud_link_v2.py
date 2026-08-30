from __future__ import annotations

import asyncio

from local.cloud_link import agent_v2


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    @property
    def is_success(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_local_status_uses_configured_local_api_token(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "LOCAL_API", "http://127.0.0.1:8080")
    monkeypatch.setattr(agent_v2.legacy, "LOCAL_TOKEN", "test-token")
    client = FakeClient(FakeResponse(200, {"ok": True}))

    payload = asyncio.run(agent_v2.local_status(client))

    assert payload == {"ok": True}
    assert client.calls[0][1]["headers"] == {"X-API-Token": "test-token"}


def test_cloud_capabilities_reports_incompatible_http_response(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(404, {}))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result == {"reachable": True, "compatible": False, "http_status": 404}


def test_cloud_capabilities_accepts_health_contract(monkeypatch):
    monkeypatch.setattr(agent_v2.legacy, "CLOUD_URL", "https://example.invalid")
    client = FakeClient(FakeResponse(200, {
        "ok": True,
        "service": "135er-Grow Central Cloud",
        "version": "0.8.0",
        "closed_test_mode": True,
    }))

    result = asyncio.run(agent_v2.cloud_capabilities(client))

    assert result["compatible"] is True
    assert result["version"] == "0.8.0"
    assert result["closed_test_mode"] is True
